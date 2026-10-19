"""Speech-to-Text: 'Live Speech-to-Text' (record a clip, transcribed as soon as you stop)
and 'Audio Upload & Transcription' (upload a file or record, then transcribe).

The Gnani request itself is unchanged and lives in gnani_client.transcribe_audio.
"""

import hashlib
from datetime import datetime

import streamlit as st

import database as db
import ui
from audio_utils import ALLOWED_EXTENSIONS, IDEAL_SECONDS, MAX_SECONDS, fmt_duration, fmt_size, validate_audio
from gnani_client import GnaniError, extract_transcript, get_api_key, transcribe_audio
from ui import card_head, notice, pill

API_KEY_HELP = "Add GNANI_API_KEY to the .env file next to streamlit_app.py, then restart the app."


def transcribe_clip(slot, data, filename, mime, lang, itn):
    """One call to the existing Gnani client. Returns (raw result, text, error tuple or None)."""
    ui.show_loading(slot, "Transcribing your audio", "Longer clips can take up to two minutes.")
    try:
        result = transcribe_audio(data, filename, mime, language_code=lang.stt_code, apply_itn=itn)
    except GnaniError as err:
        return None, "", (err.title, err.detail)
    finally:
        slot.empty()
    text = extract_transcript(result)
    if not text:
        return result, "", ("No speech was recognized",
                            f"The service returned an empty transcript. Check that the audio is clear, spoken in "
                            f"{lang.name}, and not silent, then try again.")
    return result, text, None


def transcript_header(key, title="Transcript"):
    text = st.session_state.get(key, "")
    meta = f"{len(text.split())} words, {len(text)} characters" if text else "Nothing here yet"
    st.markdown(f'<div class="t-head"><h2>{ui.esc(title)}</h2><span class="t-meta">{meta}</span></div>', unsafe_allow_html=True)


def transcript_download(text, key):
    st.download_button("Download Transcript", data=text.encode("utf-8"),
                       file_name=f"transcript-{datetime.now():%Y%m%d-%H%M%S}.txt", mime="text/plain",
                       disabled=not text.strip(), key=key)


# ------------------------------------------------------------------------------ Live Speech-to-Text
def _reset_live():
    for k, v in {"live_text": "", "live_latest": None, "live_clips": 0, "live_error": None, "live_last_hash": None}.items():
        st.session_state[k] = v
    st.session_state["live_gen"] = st.session_state.get("live_gen", 0) + 1


def live_page():
    user = ui.require_login()
    ui.page_header("Live Speech-to-Text",
                   "Record a phrase and it is transcribed the moment you stop. Each clip is added to your running transcript.", "mic")
    for k, v in {"live_text": "", "live_latest": None, "live_clips": 0, "live_error": None, "live_last_hash": None, "live_gen": 0}.items():
        st.session_state.setdefault(k, v)

    notice("info", "How live works here",
           f"Each recording is sent to Gnani when you press stop (up to {MAX_SECONDS} seconds, about {IDEAL_SECONDS} works best), "
           "and the text appears a moment later. It is turn-by-turn, not word-by-word streaming.")
    with st.expander("Why isn't this word-by-word streaming?"):
        st.markdown(
            "Gnani offers a real-time WebSocket endpoint, but it needs raw 16 kHz PCM audio sent in fixed frames, and it "
            "authenticates with an `X-API-Key-ID` header. A browser cannot set that header, and putting your key in the browser "
            "would expose it. True streaming therefore needs a small server-side relay plus a browser audio-capture component. "
            "That is extra backend infrastructure, so this page uses the REST integration you already have."
        )

    api_ready = bool(get_api_key())
    if not api_ready:
        notice("error", "API key not found", API_KEY_HELP)

    with st.container(key="card_live_input"):
        lang, usable = ui.language_picker("live", "stt")
        itn = st.toggle("Write numbers, dates and currency in their usual form", value=user["apply_itn"], key="live_itn",
                        help="Sends format=transcribe, Gnani's Inverse Text Normalization option.")
        if st.session_state.live_error:
            hero = ("That clip could not be transcribed", "Read the message below, then record again.")
        elif st.session_state.live_latest:
            hero = ("Clip added", "Record the next phrase whenever you are ready.")
        else:
            hero = ("Ready when you are", "Press the microphone button to start speaking, then press stop when you finish.")
        st.markdown(f'<div class="mic-hero"><div class="mic-orb">{ui.icon("mic", 40)}</div><div><h3>{ui.esc(hero[0])}</h3>'
                    f'<p>{ui.esc(hero[1])}</p></div></div>', unsafe_allow_html=True)
        audio = st.audio_input("Record a clip", key=f"live_mic_{st.session_state.live_gen}", label_visibility="collapsed")

    slot = st.empty()
    if audio is not None and usable and api_ready:
        data = audio.getvalue()
        digest = hashlib.sha256(data).hexdigest()
        if digest != st.session_state.live_last_hash:
            st.session_state.live_last_hash = digest
            st.session_state.live_error = None
            error, _dur, mime = validate_audio("live.wav", data)
            if error:
                st.session_state.live_error = error
            else:
                _raw, text, error = transcribe_clip(slot, data, "live.wav", mime, lang, itn)
                if error:
                    st.session_state.live_error = error
                else:
                    current = st.session_state.live_text.strip()
                    st.session_state.live_text = f"{current}\n{text}" if current else text
                    st.session_state.live_latest = text
                    st.session_state.live_clips += 1
                    st.session_state.live_gen += 1  # fresh microphone widget, ready for the next clip
                    st.rerun()
    elif audio is not None and not usable:
        notice("warn", "Choose a supported language first", "This recording was not sent because the selected language cannot be transcribed.")

    if st.session_state.live_error:
        notice("error", *st.session_state.live_error)
    if st.session_state.live_latest:
        st.markdown(f'<div class="latest"><small>Latest clip</small>{ui.esc(st.session_state.live_latest)}</div>', unsafe_allow_html=True)

    with st.container(key="card_live_text"):
        transcript_header("live_text", f"Running transcript ({st.session_state.live_clips} clips)")
        st.text_area("Live transcript editor", key="live_text", height=280, label_visibility="collapsed",
                     placeholder="Clips you record appear here. You can edit the text at any time.")
        st.markdown('<p class="hint">Press Ctrl+Enter or click outside the box to apply edits before downloading or saving.</p>', unsafe_allow_html=True)
        text = st.session_state.live_text
        if not text.strip():
            ui.empty_state("Nothing transcribed yet. Record your first clip above.")
        c1, c2, c3, c4 = st.columns(4, gap="small")
        with c1:
            ui.copy_button(text, not text.strip(), "Live transcript editor", "Copy Transcript")
        with c2:
            transcript_download(text, "gg_live_dl")
        with c3:
            if st.button("Save to history", key="gg_live_save", disabled=not text.strip()):
                db.add_history(user["id"], "Live Speech-to-Text", lang.name, lang.stt_code or "", None, text)
                st.toast("Saved to your history.")
        with c4:
            st.button("New session", key="gg_live_new", on_click=_reset_live)


# ------------------------------------------------------------------------------ Audio Upload & Transcription
def upload_page():
    user = ui.require_login()
    ui.page_header("Audio Upload & Transcription",
                   "Transcribe a recording or an audio file, then edit, copy or download the result.", "upload")
    for k, v in {"ru_text": "", "ru_source": None, "ru_raw": None, "ru_error": None}.items():
        st.session_state.setdefault(k, v)

    api_ready = bool(get_api_key())
    if not api_ready:
        notice("error", "API key not found", API_KEY_HELP)

    with st.container(key="card_ru_options"):
        lang, usable = ui.language_picker("ru", "stt")
        itn = st.toggle("Write numbers, dates and currency in their usual form", value=user["apply_itn"], key="ru_itn",
                        help="Sends format=transcribe, Gnani's Inverse Text Normalization option.")
        ui.coverage_expander()

    rec_clicked = upl_clicked = False
    recording = uploaded = None
    rec_err = upl_err = None
    rec_bytes = up_bytes = b""
    rec_mime = up_mime = ""
    with st.container(key="band"):
        left, right = st.columns(2, gap="large")
        with left:
            with st.container(key="card_ru_record"):
                card_head("mic", "Record Audio", f"Record up to {MAX_SECONDS} seconds, then transcribe it.")
                recording = st.audio_input("Record audio", label_visibility="collapsed", key="ru_mic")
                if recording is not None:
                    rec_bytes = recording.getvalue()
                    rec_err, rec_dur, rec_mime = validate_audio("recording.wav", rec_bytes)
                    if rec_err:
                        notice("error", *rec_err)
                    else:
                        pill(f"Recording ready, {fmt_duration(rec_dur)}" if rec_dur else "Recording ready", "ready")
                else:
                    pill("Waiting for a recording")
                rec_clicked = st.button("Transcribe Audio", key="gp_ru_rec",
                                        disabled=recording is None or bool(rec_err) or not usable or not api_ready)
        with right:
            with st.container(key="card_ru_upload"):
                card_head("upload", "Upload Audio", "WAV, MP3, OGG, FLAC, AAC or M4A, up to 60 seconds.")
                uploaded = st.file_uploader("Upload audio", type=ALLOWED_EXTENSIONS, label_visibility="collapsed", key="ru_upload")
                if uploaded is not None:
                    up_bytes = uploaded.getvalue()
                    upl_err, up_dur, up_mime = validate_audio(uploaded.name, up_bytes)
                    if upl_err:
                        notice("error", *upl_err)
                    else:
                        st.audio(up_bytes, format=up_mime)
                        info = f"{uploaded.name}, {fmt_size(len(up_bytes))}"
                        pill(f"{info}, {fmt_duration(up_dur)}" if up_dur else info, "ready")
                else:
                    pill("No file selected")
                upl_clicked = st.button("Transcribe Audio", key="gp_ru_upl",
                                        disabled=uploaded is None or bool(upl_err) or not usable or not api_ready)

    slot = st.empty()
    job = None
    if rec_clicked and recording is not None:
        job = ("recording", rec_bytes, "recording.wav", rec_mime)
    elif upl_clicked and uploaded is not None:
        job = ("uploaded file", up_bytes, uploaded.name, up_mime)
    if job:
        source, data, filename, mime = job
        st.session_state.ru_error = None
        raw, text, error = transcribe_clip(slot, data, filename, mime, lang, itn)
        st.session_state.ru_raw = raw
        if error:
            st.session_state.ru_error = error
        else:
            st.session_state.ru_text = text
            st.session_state.ru_source = f"{source} in {lang.name}"
            if user["save_history"]:
                db.add_history(user["id"], "Audio Upload", lang.name, lang.stt_code or "", filename, text)

    if st.session_state.ru_error:
        notice("error", *st.session_state.ru_error)

    with st.container(key="card_ru_text"):
        transcript_header("ru_text")
        if st.session_state.ru_text and st.session_state.ru_source:
            pill(f"Transcribed from your {st.session_state.ru_source}", "done")
        st.text_area("Transcript editor", key="ru_text", height=320, label_visibility="collapsed",
                     placeholder="Your transcript will appear here. Once it does, you can edit it directly.")
        st.markdown('<p class="hint">Press Ctrl+Enter or click outside the box to apply edits before downloading.</p>', unsafe_allow_html=True)
        text = st.session_state.ru_text
        if not text.strip():
            ui.empty_state("No transcript yet. Record or upload audio above, then press Transcribe Audio.")
        c1, c2, c3 = st.columns(3, gap="small")
        with c1:
            ui.copy_button(text, not text.strip(), "Transcript editor", "Copy Transcript")
        with c2:
            transcript_download(text, "gg_ru_dl")
        with c3:
            st.button("Clear", key="gg_ru_clear", disabled=not text.strip(),
                      on_click=lambda: st.session_state.update(ru_text="", ru_source=None, ru_raw=None, ru_error=None))
        if st.session_state.ru_raw:
            with st.expander("View raw API response"):
                st.json(st.session_state.ru_raw)
