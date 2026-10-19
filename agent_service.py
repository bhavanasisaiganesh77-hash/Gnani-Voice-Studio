"""Voice Agent turn logic. Three separate pieces, wired together here and nowhere else:

    1. Speech-to-text  -> gnani_client.transcribe_audio   (only for spoken questions)
    2. Language model  -> llm_client.chat
    3. Text-to-speech  -> gnani_client.synthesize_speech  (optional; text reply is kept if it fails)

This is a simple turn-by-turn assistant. It is NOT autonomous and NOT real-time streaming.
"""

import re

import gnani_client as gnani
import llm_client as llm
from gnani_client import GnaniError
from llm_client import LlmError

MAX_CONTEXT_MESSAGES = 12   # how many earlier messages are sent to the model
MAX_SPOKEN_CHARS = 1000     # this app's own cap on text sent to Text-to-Speech

SYSTEM_TEMPLATE = (
    "You are the voice assistant inside Gnani Voice Studio. "
    "Always reply in {language}, written in the normal script for {language}. "
    "Your answer will be read aloud, so use short, natural sentences (at most four), plain text only, "
    "with no markdown, bullet points, emoji or links. "
    "Write numbers, dates and currency amounts as spoken words. "
    "If you are not sure of something, say so instead of guessing."
)


def build_messages(language_name: str, history: list) -> list:
    msgs = [{"role": "system", "content": SYSTEM_TEMPLATE.format(language=language_name)}]
    msgs += [{"role": m["role"], "content": m["content"]} for m in history[-MAX_CONTEXT_MESSAGES:]]
    return msgs


def clean_for_speech(text: str) -> str:
    text = re.sub(r"[*_`#>]+", "", text)
    return re.sub(r"\s+", " ", text).strip()[:MAX_SPOKEN_CHARS]


def transcribe(audio_bytes: bytes, lang) -> str:
    """Step 1. Reuses the existing, working Gnani STT request."""
    result = gnani.transcribe_audio(audio_bytes, "question.wav", "audio/wav", language_code=lang.stt_code)
    text = gnani.extract_transcript(result)
    if not text:
        raise GnaniError("No speech was recognized",
                         f"Nothing was heard. Speak clearly in {lang.name} and try again.")
    return text


def think(lang, history: list) -> str:
    """Step 2. `history` must already end with the user's new message."""
    return llm.chat(build_messages(lang.name, history))


def speak(text: str, lang, voice: str, model: str):
    """Step 3. Returns (audio_bytes, content_type)."""
    return gnani.synthesize_speech(
        clean_for_speech(text), voice=voice, model=model, language=lang.tts_code, container="mp3"
    )


def readiness(need_speech_input: bool = True) -> dict:
    """What is configured, as simple booleans (never the secret values)."""
    return {
        "gnani": bool(gnani.get_api_key()),
        "llm": llm.is_configured(),
        "llm_missing": llm.missing_settings(),
    }
