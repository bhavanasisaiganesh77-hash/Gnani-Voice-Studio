"""Gnani speech-to-text client (REST).

Unchanged from your working integration:
  - URL:        https://api.vachana.ai/stt/v3
  - Header:     X-API-Key-ID  (value read from GNANI_API_KEY in .env)
  - Form data:  language_code
  - File field: audio_file
  - Timeout:    120 seconds
  - Parsing:    result.get("transcript", "")

Additions, both taken from Gnani's official REST docs and both optional:
  - language_code is now a parameter (default te-IN, as in your original script)
  - apply_itn=True adds format=transcribe (numbers, dates and currency written
    in their usual form). The default sends exactly what your original script sent.

Text-to-Speech (added) uses the same host and the same X-API-Key-ID header, per Gnani's official
API reference (https://docs.gnani.ai/api/TTS/tts-inference):
  POST https://api.vachana.ai/api/v1/tts/inference   -> returns raw audio bytes

The API key stays on the server and is never logged, printed or returned.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.vachana.ai/stt/v3"
LANGUAGE_CODE = "te-IN"
TIMEOUT_SECONDS = 120
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
TTS_TIMEOUT_SECONDS = 120
TTS_SPEED_RANGE = (0.85, 1.15)  # documented range


class GnaniError(Exception):
    """An error with a short title and a plain-language explanation for the UI."""

    def __init__(self, title: str, detail: str):
        super().__init__(title)
        self.title = title
        self.detail = detail


def get_api_key():
    return os.getenv("GNANI_API_KEY")


def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "sample.wav",
    mime_type: str = "audio/wav",
    language_code: str = LANGUAGE_CODE,
    apply_itn: bool = False,
) -> dict:
    """Send audio to the Gnani API and return the parsed JSON response."""
    api_key = get_api_key()
    if not api_key:
        raise GnaniError(
            "API key not found",
            "Add GNANI_API_KEY to the .env file next to streamlit_app.py, then restart the app.",
        )

    form = {"language_code": language_code}
    if apply_itn:
        form["format"] = "transcribe"

    response = None
    try:
        response = requests.post(
            API_URL,
            headers={"X-API-Key-ID": api_key},
            data=form,
            files={"audio_file": (filename, audio_bytes, mime_type)},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()

    except requests.Timeout:
        raise GnaniError(
            "The request timed out",
            f"The service did not respond within {TIMEOUT_SECONDS} seconds. "
            "Try a shorter clip or try again in a moment.",
        )
    except requests.ConnectionError:
        raise GnaniError("Could not reach the service", "Check your internet connection and try again.")
    except requests.HTTPError:
        status = response.status_code if response is not None else "unknown"
        raise GnaniError(*_http_message(status, response))
    except ValueError:
        raise GnaniError(
            "Unexpected response",
            "The service replied, but not in a format this app understands. Try again.",
        )
    except requests.RequestException:
        raise GnaniError("Request failed", "The request could not be completed. Try again.")


def extract_transcript(result: dict) -> str:
    """Same parsing as the original script."""
    return result.get("transcript", "")


def _api_message(response) -> str:
    """Gnani error bodies look like {"success": false, "error": {"type": ..., "message": ...}}."""
    try:
        return str(response.json()["error"]["message"])[:300]
    except Exception:
        return ""


def _http_message(status, response, service="speech-to-text"):
    api_msg = _api_message(response) if response is not None else ""
    if status == 403 and service == "text-to-speech":
        return (
            "Text-to-Speech access was denied",
            "Gnani returned 403. Your key works for speech-to-text, but text-to-speech may not be enabled on "
            "your Gnani account or plan. Check that the key belongs to an active organization with credits, "
            "and ask Gnani support to enable Text-to-Speech if it does.",
        )
    if status == 403:
        return (
            "The API key was not accepted",
            "Gnani returned 403. Check that GNANI_API_KEY is correct, your organization is active, "
            "and your account has credits left.",
        )
    if status == 401:
        return ("The API key was not accepted", "Gnani returned 401. Check GNANI_API_KEY in your .env file.")
    if status == 400:
        return (
            "Gnani could not process this request" if service == "text-to-speech" else "Gnani could not process this audio",
            api_msg or (
                "Check the text, voice and language." if service == "text-to-speech"
                else "Use WAV, MP3, OGG, FLAC, AAC or M4A audio of 60 seconds or less."
            ),
        )
    if status == 429:
        return ("Too many requests", "Wait a moment, then try again.")
    if status in (500, 503):
        return (
            "The speech service had a problem",
            f"Gnani returned {status}. This is usually temporary, so try again shortly.",
        )
    return ("Request failed", f"Gnani returned HTTP {status}. {api_msg}".strip())


# ----------------------------------------------------------------------------- Text-to-Speech
_AUDIO_MAGIC = (b"RIFF", b"ID3", b"OggS", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")


def synthesize_speech(
    text: str,
    voice: str,
    model: str = "timbre-v2.5",
    language: str = "en-IN",
    speed: float = 1.0,
    container: str = "wav",
    sample_rate: int = 24000,
):
    """Generate speech. Returns (audio_bytes, content_type). Raises GnaniError on any problem.

    Body follows Gnani's documented schema. `container` is "wav" or "mp3".
    """
    api_key = get_api_key()
    if not api_key:
        raise GnaniError(
            "API key not found",
            "Add GNANI_API_KEY to the .env file next to streamlit_app.py, then restart the app.",
        )
    if container not in ("wav", "mp3"):
        raise GnaniError("Unsupported audio format", "Choose WAV or MP3.")

    speed = max(TTS_SPEED_RANGE[0], min(TTS_SPEED_RANGE[1], float(speed)))
    audio_config = {"sample_rate": int(sample_rate), "num_channels": 1, "sample_width": 2, "container": container}
    if container == "wav":
        audio_config["encoding"] = "linear_pcm"
    else:
        audio_config["bitrate"] = "128k"

    body = {
        "text": text,
        "voice": voice,
        "model": model,
        "language": language,
        "speed": speed,
        "audio_config": audio_config,
    }

    response = None
    try:
        response = requests.post(
            TTS_URL,
            headers={"X-API-Key-ID": api_key, "Content-Type": "application/json"},
            json=body,
            timeout=TTS_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.Timeout:
        raise GnaniError("The request timed out", "Gnani did not respond in time. Try shorter text or try again.")
    except requests.ConnectionError:
        raise GnaniError("Could not reach the service", "Check your internet connection and try again.")
    except requests.HTTPError:
        status = response.status_code if response is not None else "unknown"
        raise GnaniError(*_http_message(status, response, service="text-to-speech"))
    except requests.RequestException:
        raise GnaniError("Request failed", "The request could not be completed. Try again.")

    audio = response.content or b""
    content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    if not audio or content_type.startswith("application/json") or not (
        content_type.startswith("audio/") or audio[:4] in _AUDIO_MAGIC or audio[:2] == b"\xff\xfb"
    ):
        raise GnaniError(
            "No audio was returned",
            "Gnani replied, but the response was not an audio file. "
            + (_api_message(response) or "Try again, or try a different voice or language."),
        )
    if not content_type.startswith("audio/"):
        content_type = "audio/mpeg" if container == "mp3" else "audio/wav"
    return audio, content_type
