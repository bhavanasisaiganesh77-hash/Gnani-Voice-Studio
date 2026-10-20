"""LLM client with Gemini primary and Groq automatic fallback."""

import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
TIMEOUT_SECONDS = 45

GROQ_DEFAULT_URL = "https://api.groq.com/openai/v1"
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"


class LlmError(Exception):
    def __init__(self, title: str, detail: str):
        super().__init__(title)
        self.title = title
        self.detail = detail


def _setting(name: str, default: str = "") -> str:
    """Read from environment/.env or Streamlit Cloud Secrets."""
    value = os.getenv(name, "").strip()
    if value:
        return value

    try:
        import streamlit as st
        value = str(st.secrets.get(name, default)).strip()
        return value
    except Exception:
        return default

def _providers():
    """Return configured AI providers, with Gemini first and Groq as backup."""

    providers = []

    # Primary provider: Google Gemini
    gemini_key = _setting("LLM_API_KEY")
    gemini_url = _setting(
        "LLM_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai",
    ).rstrip("/")
    gemini_model = _setting("LLM_MODEL", "gemini-2.5-flash")

    if gemini_key and gemini_url and gemini_model:
        providers.append({
            "name": "Gemini",
            "key": gemini_key,
            "url": gemini_url,
            "model": gemini_model,
        })

    # Backup provider: Groq
    groq_key = _setting("GROQ_API_KEY")
    groq_url = _setting(
        "GROQ_BASE_URL",
        "https://api.groq.com/openai/v1",
    ).rstrip("/")
    groq_model = _setting(
        "GROQ_MODEL",
        "llama-3.3-70b-versatile",
    )

    if groq_key and groq_url and groq_model:
        providers.append({
            "name": "Groq",
            "key": groq_key,
            "url": groq_url,
            "model": groq_model,
        })

    return providers

def missing_settings() -> list:
    """Return missing settings only when no provider is ready."""
    if _providers():
        return []
    return [
        "Configure Gemini (LLM_API_KEY, LLM_BASE_URL, LLM_MODEL) "
        "or Groq (GROQ_API_KEY)"
    ]


def is_configured() -> bool:
    return bool(_providers())


def model_name() -> str:
    providers = _providers()
    return providers[0]["model"] if providers else ""

logger.info(
    "AI request: provider=%s, url=%s, model=%s",
    provider["name"],
    f'{provider["url"].rstrip("/")}/chat/completions',
    provider["model"],
)
def _request(provider, messages, temperature, max_tokens):
    response = requests.post(
        f'{provider["url"]}/chat/completions',
        headers={
            "Authorization": f'Bearer {provider["key"]}',
            "Content-Type": "application/json",
        },
        json={
            "model": provider["model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    data = response.json()
    answer = data["choices"][0]["message"]["content"]

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Empty or invalid model response")

    return answer.strip()


def chat(messages: list, temperature: float = 0.4,
         max_tokens: int = 1024) -> str:
    """Try Gemini first, then Groq. Keep technical errors out of user replies."""
    providers = _providers()

    if not providers:
        raise LlmError(
            "AI assistant temporarily unavailable",
            "Please try again in a moment.",
        )

    for provider in providers:
        try:
            answer = _request(
                provider, messages, temperature, max_tokens
            )
            logger.info("AI response completed using %s", provider["name"])
            return answer

        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            logger.warning(
                "%s request failed with HTTP %s",
                provider["name"], status,
            )

        except requests.RequestException as exc:
            # Log only the error type, never request headers or credentials.
            logger.warning(
                "%s request failed: %s",
                provider["name"], type(exc).__name__,
            )

        except (ValueError, KeyError, IndexError, TypeError) as exc:
            logger.warning(
                "%s returned an invalid response: %s",
                provider["name"], type(exc).__name__,
            )

        except Exception as exc:
            logger.warning(
                "%s failed unexpectedly: %s",
                provider["name"], type(exc).__name__,
            )

    raise LlmError(
        "I'm having trouble responding right now",
        "Please try again in a moment.",
    )