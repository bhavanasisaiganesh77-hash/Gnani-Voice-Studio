"""Language-model client for the AI Voice Agent.

Gnani's speech APIs do not include a chat model, so the agent uses a separate, independently
configured provider through the widely supported "OpenAI-compatible" chat API:

    POST {LLM_BASE_URL}/chat/completions
    Authorization: Bearer {LLM_API_KEY}

Settings (all read from .env, never hardcoded, never shown in the UI):
    LLM_API_KEY   your provider key
    LLM_BASE_URL  e.g. https://generativelanguage.googleapis.com/v1beta/openai   (Google Gemini)
    LLM_MODEL     a model id from your provider's model list

Any provider that offers this API works (Google Gemini, OpenRouter, Groq, OpenAI, a local Ollama server...).
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

TIMEOUT_SECONDS = 60


class LlmError(Exception):
    def __init__(self, title: str, detail: str):
        super().__init__(title)
        self.title = title
        self.detail = detail


def _settings():
    return (
        (os.getenv("LLM_API_KEY") or "").strip(),
        (os.getenv("LLM_BASE_URL") or "").strip().rstrip("/"),
        (os.getenv("LLM_MODEL") or "").strip(),
    )


def missing_settings() -> list:
    """Names of the .env variables that are not set yet (never their values)."""
    key, base, model = _settings()
    return [n for n, v in (("LLM_API_KEY", key), ("LLM_BASE_URL", base), ("LLM_MODEL", model)) if not v]


def is_configured() -> bool:
    return not missing_settings()


def model_name() -> str:
    return _settings()[2]


def chat(messages: list, temperature: float = 0.4, max_tokens: int = 1024) -> str:
    """Send a conversation and return the assistant's reply text."""
    missing = missing_settings()
    if missing:
        raise LlmError("AI model not configured", "Add " + ", ".join(missing) + " to your .env file, then restart the app.")
    key, base, model = _settings()
    if not base.startswith(("https://", "http://")):
        raise LlmError("AI model not configured", "LLM_BASE_URL must start with https:// (or http:// for a local server).")

    response = None
    try:
        response = requests.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        text = (data["choices"][0]["message"]["content"] or "").strip()
    except requests.Timeout:
        raise LlmError("The AI model timed out", "It did not answer in time. Try again.")
    except requests.ConnectionError:
        raise LlmError("Could not reach the AI model", "Check your internet connection and LLM_BASE_URL.")
    except requests.HTTPError:
        status = response.status_code if response is not None else "unknown"
        raise LlmError(*_http_message(status))
    except (ValueError, KeyError, IndexError, TypeError):
        raise LlmError("Unexpected answer from the AI model", "The reply was not in the expected format. Check LLM_BASE_URL and LLM_MODEL.")
    except requests.RequestException:
        raise LlmError("AI request failed", "The request could not be completed. Try again.")

    if not text:
        raise LlmError("The AI model returned an empty answer", "Try rephrasing your question, or try again.")
    return text


def _http_message(status):
    if status in (401, 403):
        return ("The AI provider rejected the key", f"The provider returned {status}. Check LLM_API_KEY in your .env file.")
    if status == 404:
        return ("AI model or address not found", "The provider returned 404. Check LLM_BASE_URL and that LLM_MODEL is a valid model id.")
    if status == 400:
        return ("The AI provider rejected the request", "The provider returned 400. Check that LLM_MODEL is correct for this provider.")
    if status == 429:
        return ("AI usage limit reached", "The provider returned 429: too many requests or the free quota is used up. Wait and try again.")
    return ("The AI provider had a problem", f"The provider returned HTTP {status}. Try again shortly.")
