"""Gemini-first, Groq-backup language model client."""

import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 45

GEMINI_DEFAULT_URL = (
    "https://generativelanguage.googleapis.com/v1beta/openai"
)
GEMINI_DEFAULT_MODEL = "gemini-2.5-flash"

GROQ_DEFAULT_URL = "https://api.groq.com/openai/v1"
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"


class LlmError(Exception):
    """Safe, user-facing AI provider error."""

    def __init__(self, title: str, detail: str):
        super().__init__(title)
        self.title = title
        self.detail = detail


def _setting(name: str, default: str = "") -> str:
    """Read a setting from environment variables or Streamlit Secrets."""

    value = os.getenv(name)

    if value and value.strip():
        return value.strip()

    try:
        import streamlit as st

        value = st.secrets.get(name, default)
        if value is not None and str(value).strip():
            return str(value).strip()
    except Exception:
        # Streamlit Secrets may not be available during local development.
        pass

    return default.strip() if isinstance(default, str) else ""


def _providers() -> list:
    """Return configured providers in fallback order."""

    providers = []

    # Primary: Gemini
    gemini_key = _setting("LLM_API_KEY")
    gemini_url = _setting(
        "LLM_BASE_URL", GEMINI_DEFAULT_URL
    ).rstrip("/")
    gemini_model = _setting(
        "LLM_MODEL", GEMINI_DEFAULT_MODEL
    )

    if gemini_key and gemini_url and gemini_model:
        providers.append({
            "name": "Gemini",
            "key": gemini_key,
            "url": gemini_url,
            "model": gemini_model,
        })

    # Backup: Groq
    groq_key = _setting("GROQ_API_KEY")
    groq_url = _setting(
        "GROQ_BASE_URL", GROQ_DEFAULT_URL
    ).rstrip("/")
    groq_model = _setting(
        "GROQ_MODEL", GROQ_DEFAULT_MODEL
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
    """Return missing configuration names without exposing secret values."""

    if _providers():
        return []

    missing = []

    if not _setting("LLM_API_KEY") and not _setting("GROQ_API_KEY"):
        missing.append("LLM_API_KEY or GROQ_API_KEY")

    return missing


def is_configured() -> bool:
    """Whether at least one provider has a configured API key."""

    return bool(_providers())


def model_name() -> str:
    """Return the first configured provider's model name."""

    providers = _providers()
    return providers[0]["model"] if providers else ""


def _request(
    provider: dict,
    messages: list,
    temperature: float,
    max_tokens: int,
) -> str:
    """Make one request to a configured OpenAI-compatible API."""

    base_url = provider["url"].rstrip("/")

    # Prevent a duplicated endpoint path if the base URL already contains it.
    if base_url.endswith("/chat/completions"):
        url = base_url
    else:
        url = f"{base_url}/chat/completions"
        logger.info("LLM request URL: %s", url)
        logger.info("LLM model: %s", provider["model"])

    logger.info(
        "AI request: provider=%s, url=%s, model=%s",
        provider["name"],
        url,
        provider["model"],
    )

    response = requests.post(
        url,
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

    # Log the status only. Never log API keys or request headers.
    if response.status_code >= 400:
        logger.warning(
            "%s request failed with HTTP %s",
            provider["name"],
            response.status_code,
        )

    response.raise_for_status()

    data = response.json()
    answer = data["choices"][0]["message"]["content"]

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Empty or invalid model response")

    return answer.strip()


def chat(
    messages: list,
    temperature: float = 0.4,
    max_tokens: int = 1024,
) -> str:
    """Try Gemini first, then Groq if the first provider fails."""

    providers = _providers()

    if not providers:
        raise LlmError(
            "AI assistant is not configured",
            "Please configure a Gemini or Groq API key and try again.",
        )

    for provider in providers:
        try:
            answer = _request(
                provider,
                messages,
                temperature,
                max_tokens,
            )

            logger.info(
                "AI response completed using %s",
                provider["name"],
            )
            return answer

        except requests.HTTPError as exc:
            status = (
                exc.response.status_code
                if exc.response is not None
                else 0
            )
            logger.warning(
                "%s request failed with HTTP %s",
                provider["name"],
                status,
            )

        except requests.Timeout:
            logger.warning("%s request timed out", provider["name"])

        except requests.ConnectionError:
            logger.warning(
                "%s connection failed",
                provider["name"],
            )

        except requests.RequestException as exc:
            logger.warning(
                "%s request failed: %s",
                provider["name"],
                type(exc).__name__,
            )

        except (ValueError, KeyError, IndexError, TypeError) as exc:
            logger.warning(
                "%s returned an invalid response: %s",
                provider["name"],
                type(exc).__name__,
            )

        except Exception as exc:
            logger.warning(
                "%s failed unexpectedly: %s",
                provider["name"],
                type(exc).__name__,
            )

    raise LlmError(
        "I'm having trouble responding right now",
        "Please try again in a moment.",
    )