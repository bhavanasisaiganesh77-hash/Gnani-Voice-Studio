"""Optional AI model for the in-app assistant (any OpenAI-compatible chat API).

    POST {LLM_BASE_URL}/chat/completions      Authorization: Bearer {LLM_API_KEY}

Settings come from .env or Streamlit secrets and are never shown in the interface:
    LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

If they are missing, the assistant uses its built-in help answers instead.
"""

import logging
import os
import threading

import requests
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("voicestudio.llm")

TIMEOUT_SECONDS = 20  # the assistant should answer quickly or fall back
_local = threading.local()


def _session() -> requests.Session:
    if not hasattr(_local, "session"):
        _local.session = requests.Session()
    return _local.session


class LlmError(Exception):
    pass


def _secret(name: str) -> str:
    """Read a setting from the environment, then from Streamlit secrets (used on Streamlit Community Cloud)."""
    value = os.getenv(name)
    if not value:
        try:
            import streamlit as st
            value = st.secrets.get(name)
        except Exception:
            value = None
    return (value or "").strip()


def _settings():
    return _secret("LLM_API_KEY"), _secret("LLM_BASE_URL").rstrip("/"), _secret("LLM_MODEL")


def is_configured() -> bool:
    return all(_settings())


def chat(messages: list, temperature: float = 0.3, max_tokens: int = 600) -> str:
    """Send a conversation and return the reply text. Raises LlmError (never shown to people) on any problem."""
    key, base, model = _settings()
    if not (key and base and model):
        raise LlmError("not configured")
    if not base.startswith(("https://", "http://")):
        raise LlmError("LLM_BASE_URL must start with https://")

    response = None
    try:
        response = _session().post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        text = (response.json()["choices"][0]["message"]["content"] or "").strip()
    except requests.HTTPError:
        status = response.status_code if response is not None else "unknown"
        log.warning("assistant model returned HTTP %s", status)
        raise LlmError(f"http {status}")
    except requests.RequestException:
        log.warning("assistant model request failed")
        raise LlmError("request failed")
    except (ValueError, KeyError, IndexError, TypeError):
        log.warning("assistant model reply was not in the expected format")
        raise LlmError("bad reply")
    if not text:
        raise LlmError("empty reply")
    return text
