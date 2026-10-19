"""Text-to-Speech workspace (Gnani Timbre voices through gnani_client.synthesize_speech)."""

from datetime import datetime

import streamlit as st

import database as db
import ui
import voices
from gnani_client import GnaniError, get_api_key, synthesize_speech
from ui import card_head, notice, pill

MAX_TTS_CHARS = 1000  # this app's own limit; Gnani's REST docs do not state a maximum
QUALITY = {"Standard (24 kHz)": 24000, "High (48 kHz)": 48000}
FORMATS = {"WAV (best compatibility)": "wav", "MP3 (smaller file)": "mp3"}


def tts_page():
    user = ui.require_login()
    ui.page_header("Text-to-Speech", "Type or paste text and Gnani's Timbre voices will read it aloud. Play it here or download the audio.", "volume")

    api_ready = bool(get_api_key())
    if not api_ready:
        notice("error", "API key not found", "Add GNANI_API_KEY to the .env file next to streamlit_app.py, then restart the app.")

    with st.container(key="card_tts_options"):
        card_head("languages", "Language and voice", "Only languages and voices listed in Gnani's official documentation appear here.")
        lang, usable = ui.language_picker("tts", "tts")
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            model = st.selectbox("Voice model", list(voices.MODELS), format_func=voices.MODELS.get, key="tts_model",
                                 help="Each model has its own voices. Timbre v3.0 is newer; if your account does not have it yet, use v2.5.")
        with c2:
            options = voices.voices_for(model, lang.id)
            voice = st.selectbox("Voice", [v for v, _ in options], key=f"tts_voice_{model}_{lang.id}",
                                 format_func=lambda v: f"{v} ({dict(options)[v]})")
        c3, c4, c5 = st.columns(3, gap="medium")
        with c3:
            speed = st.slider("Speed", 0.85, 1.15, 1.0, 0.05, key="tts_speed", help="Gnani accepts 0.85 (slowest) to 1.15 (fastest).")
        with c4:
            fmt_label = st.selectbox("Audio format", list(FORMATS), key="tts_format")
        with c5:
            quality_label = st.selectbox("Quality", list(QUALITY), key="tts_quality")

    with st.container(key="card_tts_text"):
        card_head("volume", "Your text", f"Up to {MAX_TTS_CHARS} characters per generation.")
        text = st.text_area("Text to speak", key="tts_text", height=190, max_chars=MAX_TTS_CHARS, label_visibility="collapsed",
                            placeholder=f"Type or paste text in {lang.name}...")
        st.markdown(f'<p class="hint">{len(text)} / {MAX_TTS_CHARS} characters. '
                    'Write numbers, dates and currency as spoken words for the best pronunciation. '
                    + ("Timbre v3.0 also understands tags such as &lt;pauses&gt; or &lt;laugh&gt;. " if model == "timbre-v3.0" else "")
                    + '</p>', unsafe_allow_html=True)
        problem = None
        if not usable:
            problem = "Choose a language that is supported for text-to-speech."
        elif not text.strip():
            problem = "Enter some text to speak."
        generate = st.button("Generate Speech", key="gp_tts_generate", disabled=bool(problem) or not api_ready)
        if problem and text.strip() == "" and usable:
            st.caption(problem)

    slot = st.empty()
    if generate:
        st.session_state.pop("tts_error", None)
        container = FORMATS[fmt_label]
        ui.show_loading(slot, "Generating speech", "This usually takes a few seconds.")
        try:
            audio, mime = synthesize_speech(text.strip(), voice=voice, model=model, language=lang.tts_code,
                                            speed=speed, container=container, sample_rate=QUALITY[quality_label])
        except GnaniError as err:
            st.session_state["tts_error"] = (err.title, err.detail)
            st.session_state.pop("tts_result", None)
        else:
            st.session_state["tts_result"] = {
                "audio": audio, "mime": mime, "container": container, "voice": voice, "model": model,
                "language": lang.name, "chars": len(text.strip()),
            }
            if user["save_history"]:
                db.add_tts(user["id"], text.strip(), lang.name, lang.tts_code, voice, model, container, speed, audio)
        finally:
            slot.empty()

    if st.session_state.get("tts_error"):
        notice("error", *st.session_state["tts_error"])

    result = st.session_state.get("tts_result")
    with st.container(key="card_tts_result"):
        card_head("volume", "Generated audio", "Play it here, then download it.")
        if not result:
            ui.empty_state("No audio yet. Enter text above and press Generate Speech.")
        else:
            pill(f"{result['language']}, voice {result['voice']}, {result['model']}, {len(result['audio']) / 1024:.0f} KB", "done")
            st.audio(result["audio"], format=result["mime"])
            st.download_button("Download Audio", data=result["audio"],
                               file_name=f"speech-{datetime.now():%Y%m%d-%H%M%S}.{result['container']}",
                               mime=result["mime"], key="gp_tts_download")
            if user["save_history"]:
                st.caption("Saved to your History.")
