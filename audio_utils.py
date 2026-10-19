"""Client-side checks run before audio is sent, so users get clear errors early.

Limits come from Gnani's REST docs: WAV, MP3, OGG, FLAC, AAC, M4A; 60 seconds maximum
(30 seconds is ideal). MAX_BYTES is this app's own safety cap, not a Gnani limit.
"""

import io
import wave

ALLOWED_EXTENSIONS = ["wav", "mp3", "ogg", "flac", "aac", "m4a"]
MIME_TYPES = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "ogg": "audio/ogg",
    "flac": "audio/flac",
    "aac": "audio/aac",
    "m4a": "audio/mp4",
}
MAX_SECONDS = 60
IDEAL_SECONDS = 30
MAX_BYTES = 25 * 1024 * 1024


def get_duration(data: bytes, extension: str):
    """Duration in seconds, or None when it cannot be read (the API will still validate)."""
    try:
        if extension == "wav":
            with wave.open(io.BytesIO(data)) as w:
                return w.getnframes() / float(w.getframerate())
    except Exception:
        pass
    try:
        import mutagen

        info = mutagen.File(io.BytesIO(data))
        if info is not None and info.info is not None and info.info.length:
            return float(info.info.length)
    except Exception:
        pass
    return None


def validate_audio(filename: str, data: bytes):
    """Return (error or None, duration or None, mime type)."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return (
            ("Unsupported file type",
             f"'.{ext or '?'}' files are not supported. Use " + ", ".join(e.upper() for e in ALLOWED_EXTENSIONS) + "."),
            None,
            "",
        )
    if not data:
        return (("The file is empty", "Choose a different file or record again."), None, "")
    if len(data) > MAX_BYTES:
        return (
            ("The file is too large",
             f"This app accepts files up to {MAX_BYTES // (1024 * 1024)} MB. Gnani also limits clips to {MAX_SECONDS} seconds."),
            None,
            "",
        )
    duration = get_duration(data, ext)
    if duration is not None and duration > MAX_SECONDS:
        return (
            ("The clip is too long",
             f"This clip is {fmt_duration(duration)}. Gnani accepts up to {MAX_SECONDS} seconds per request "
             f"(about {IDEAL_SECONDS} seconds works best). Trim it or split it into shorter clips."),
            duration,
            "",
        )
    return None, duration, MIME_TYPES[ext]


def fmt_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def fmt_size(n: int) -> str:
    return f"{n / 1024:.0f} KB" if n < 1024 * 1024 else f"{n / (1024 * 1024):.1f} MB"
