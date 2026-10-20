import logging
import os

import requests

try:
    import streamlit as st
except ImportError:
    st = None

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


logger = logging.getLogger(__name__)

# Default OpenAI-compatible API endpoints
GEMINI_DEFAULT_URL = (
    "https://generativelanguage.googleapis.com/v1beta/openai"
)
GEMINI_DEFAULT_MODEL = "gemini-3.8-flash"

GROQ_DEFAULT_URL = "https://api.groq.com/openai/v1"
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"

TIMEOUT_SECONDS = 90


class LlmError(Exception):
    """Raised when all configured language-model providers fail."""


def _setting(name, default=""):
    """Read a setting from environment variables or Streamlit Secrets."""
    value = os.getenv(name)

    if value:
        return value.strip()

    if st is not None:
        try:
            value = st.secrets.get(name, default)
            if value:
                return str(value).strip()
        except Exception:
            # Streamlit Secrets may not be configured in local development.
            pass

    return default


def _providers():
    """Return configured providers in priority order: Gemini, then Groq."""
    configured = []

    gemini_key = _setting("LLM_API_KEY")
    gemini_url = _setting(
        "LLM_BASE_URL", GEMINI_DEFAULT_URL
    ).rstrip("/")
    gemini_model = _setting(
        "LLM_MODEL", GEMINI_DEFAULT_MODEL
    )

    if gemini_key:
        configured.append({
            "name": "Gemini",
            "key": gemini_key,
            "url": gemini_url,
            "model": gemini_model,
        })

    groq_key = _setting("GROQ_API_KEY")
    groq_url = _setting(
        "GROQ_BASE_URL", GROQ_DEFAULT_URL
    ).rstrip("/")
    groq_model = _setting(
        "GROQ_MODEL", GROQ_DEFAULT_MODEL
    )

    if groq_key:
        configured.append({
            "name": "Groq",
            "key": groq_key,
            "url": groq_url,
            "model": groq_model,
        })

    return configured


def _request(provider, messages, temperature=0.3, max_tokens=800):
    """Send a chat-completion request to one provider."""
    base_url = provider["url"].rstrip("/")
    url = f"{base_url}/chat/completions"

    # Safe diagnostics: never log API keys or authorization headers.
    logger.info(
        "LLM request: provider=%s model=%s url=%s",
        provider["name"],
        provider["model"],
        url,
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
        timeout=(10, TIMEOUT_SECONDS),
    )

    if not response.ok:
        # Log a short error message, but never log the API key.
        logger.error(
            "%s returned HTTP %s: %s",
            provider["name"],
            response.status_code,
            response.text[:500],
        )

    response.raise_for_status()

    data = response.json()
    choices = data.get("choices", [])

    if not choices:
        raise LlmError(
            f'{provider["name"]} returned no response choices.'
        )

    message = choices[0].get("message", {})
    content = message.get("content", "")

    if isinstance(content, str) and content.strip():
        return content.strip()

    # Some compatible APIs return content as a list of text blocks.
    if isinstance(content, list):
        parts = [
            item.get("text", "")
            for item in content
            if isinstance(item, dict)
        ]
        answer = "\n".join(part for part in parts if part.strip())
        if answer.strip():
            return answer.strip()

    raise LlmError(
        f'{provider["name"]} returned an empty response.'
    )


def chat(messages, temperature=0.3, max_tokens=800):
    """
    Generate a response using Gemini first and Groq as fallback.

    messages should be a list of dictionaries, for example:
    [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"}
    ]
    """
    providers = _providers()

    if not providers:
        raise LlmError(
            "No LLM API keys configured. Add LLM_API_KEY for Gemini "
            "or GROQ_API_KEY for Groq in your environment or Streamlit Secrets."
        )

    errors = []

    for provider in providers:
        try:
            return _request(
                provider,
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except requests.exceptions.Timeout:
            logger.warning(
                "%s request timed out.",
                provider["name"],
            )
            errors.append(f'{provider["name"]}: request timed out')
        except requests.exceptions.HTTPError as exc:
            status = (
                exc.response.status_code
                if exc.response is not None
                else "unknown"
            )
            logger.warning(
                "%s request failed with HTTP %s.",
                provider["name"],
                status,
            )
            errors.append(f'{provider["name"]}: HTTP {status}')
        except requests.exceptions.RequestException as exc:
            logger.warning(
                "%s request failed: %s",
                provider["name"],
                type(exc).__name__,
            )
            errors.append(
                f'{provider["name"]}: connection error'
            )
        except (ValueError, KeyError, LlmError) as exc:
            logger.warning(
                "%s response could not be processed: %s",
                provider["name"],
                type(exc).__name__,
            )
            errors.append(f'{provider["name"]}: invalid response')

    logger.error("All configured LLM providers failed: %s", errors)

    raise LlmError(
        "The AI assistant could not get a response from its configured "
        "providers. Check the app logs and API configuration."
    )
def is_configured():
    """Return whether at least one LLM provider has an API key configured."""
    return bool(_providers())