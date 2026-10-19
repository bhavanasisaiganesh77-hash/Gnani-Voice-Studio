"""AI Voice Agent: microphone (or typing) -> Gnani speech-to-text -> AI model -> Gnani text-to-speech -> playback.

Each part lives in its own module (gnani_client, llm_client) and agent_service.py wires them together.
It is turn-by-turn, not real-time streaming, and not autonomous.
"""

import hashlib

import streamlit as st

import agent_service as agent
import database as db
import ui
import voices
from audio_utils import validate_audio
from gnani_client import GnaniError
from llm_client import LlmError
from ui import card_head, notice, pill

LLM_SETUP = """**One-time setup for the AI model** (Gnani's speech APIs do not include a chat model, so the agent needs its own):

1. Create an API key with an AI provider. Google Gemini works well for students: sign in at Google AI Studio and create a key.
2. Add three lines to your `.env` file (see `.env.example`):
   - `LLM_API_KEY` is your provider key
   - `LLM_BASE_URL` is `https://generativelanguage.googleapis.com/v1beta/openai` for Gemini
   - `LLM_MODEL` is a model id from your provider's model list
3. Restart the app.

Any provider with an OpenAI-compatible chat API works (OpenRouter, Groq, OpenAI, a local Ollama server). Providers set their own prices and free limits, so check them first. Every question and answer is one request to the provider."""

STATE_DEFAULTS = {"agent_active": False, "agent_conv_id": None, "agent_msgs": [], "agent_audio": None,
                  "agent_error": None, "agent_warn": None, "agent_gen": 0, "agent_last_hash": None}


def _reset_conversation():
    for k, v in STATE_DEFAULTS.items():
        if k not in ("agent_active", "agent_gen"):
            st.session_state[k] = [] if isinstance(v, list) else v
    st.session_state["agent_gen"] = st.session_state.get("agent_gen", 0) + 1


def _start():
    _reset_conversation()
    st.session_state["agent_active"] = True


def _stop():
    st.session_state["agent_active"] = False


def _run_turn(user, lang, voice, speak_back, typed=None, audio_bytes=None):
    """One full turn. Returns True when it succeeded."""
    state = st.session_state
    slot = st.empty()
    state.agent_error = state.agent_warn = None
    via = "typed"
    try:
        if audio_bytes is not None:
            via = "spoken"
            error, _d, _m = validate_audio("question.wav", audio_bytes)
            if error:
                raise GnaniError(*error)
            ui.show_loading(slot, "Listening to your question", "Turning your speech into text with Gnani...")
            question = agent.transcribe(audio_bytes, lang)
        else:
            question = typed.strip()
        ui.show_loading(slot, "Thinking", "Asking the AI model...")
        history = state.agent_msgs + [{"role": "user", "content": question, "via": via}]
        reply = agent.think(lang, history)

        # Both messages are saved only after the model answered, so a failed turn leaves nothing half-saved.
        if state.agent_conv_id is None:
            state.agent_conv_id = db.create_conversation(user["id"], question, lang.name, lang.stt_code or "")
        db.add_message(user["id"], state.agent_conv_id, "user", question)
        db.add_message(user["id"], state.agent_conv_id, "assistant", reply)
        state.agent_msgs = history + [{"role": "assistant", "content": reply, "via": "ai"}]
        state.agent_audio = None

        if speak_back:
            ui.show_loading(slot, "Preparing the spoken answer", "Turning the answer into speech with Gnani...")
            try:
                data, mime = agent.speak(reply, lang, voice, voices.DEFAULT_MODEL)
                state.agent_audio = {"audio": data, "mime": mime, "fresh": True}
            except GnaniError as err:
                state.agent_warn = (f"The written answer is ready, but the voice could not be generated: {err.title}", err.detail)
        return True
    except (GnaniError, LlmError) as err:
        state.agent_error = (err.title, err.detail)
        return False
    finally:
        slot.empty()


def _render_chat(messages):
    if not messages:
        ui.empty_state("No messages yet. Speak or type a question to begin.")
        return
    rows = []
    for m in messages:
        who = "You" if m["role"] == "user" else "Assistant"
        if m["role"] == "user":
            who += " (spoken)" if m.get("via") == "spoken" else " (typed)"
        rows.append(f'<div class="bubble {m["role"]}"><small>{ui.esc(who)}</small>{ui.esc(m["content"])}</div>')
    st.markdown(f'<div class="chat" aria-live="polite">{"".join(rows)}</div>', unsafe_allow_html=True)


def agent_page():
    user = ui.require_login()
    ui.page_header("AI Voice Agent", "Ask a question by voice or by typing. The assistant answers in text and, when voice is available, out loud.", "bot")
    state = st.session_state
    for k, v in STATE_DEFAULTS.items():
        state.setdefault(k, [] if isinstance(v, list) else v)

    notice("info", "How this agent works",
           "Turn by turn: you speak or type, then wait for the answer. It does not listen continuously or stream in real time, "
           "and it only answers questions, it does not take actions.")
    status = ui.service_status()
    if not status["gnani"]:
        notice("error", "Gnani API key not found", "Add GNANI_API_KEY to the .env file, then restart. It is needed for speech-to-text and text-to-speech.")
    if not status["llm"]:
        notice("warn", "The AI model is not configured yet", "Missing in .env: " + ", ".join(status["llm_missing"]) + ".")
        with st.expander("How to set up the AI model"):
            st.markdown(LLM_SETUP)
    ready = status["gnani"] and status["llm"]

    with st.container(key="card_agent_options"):
        card_head("languages", "Conversation settings", "Only languages with verified speech-to-text and text-to-speech are available.")
        lang, usable = ui.language_picker("agent", "agent")
        options = voices.voices_for(voices.DEFAULT_MODEL, lang.id)
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            voice = st.selectbox("Assistant voice", [v for v, _ in options], key=f"agent_voice_{lang.id}",
                                 format_func=lambda v: f"{v} ({dict(options)[v]})")
        with c2:
            speak_back = st.toggle("Speak the answers", value=True, key="agent_speak",
                                   help="Uses Gnani text-to-speech. If it fails, you still get the written answer.")

    if not state.agent_active:
        with st.container(key="card_agent_start"):
            if state.agent_msgs:
                pill("Conversation ended and saved to History", "done")
                _render_chat(state.agent_msgs)
            else:
                pill("Not started")
            if st.button("Start Voice Agent", key="gp_agent_start", disabled=not (usable and ready)):
                _start()
                st.rerun()
            if not usable:
                st.caption("Choose a supported language to start.")
        return

    # ---- active conversation ----
    with st.container(key="card_agent_controls"):
        pill("Active: ask by voice or by typing", "ready")
        b1, b2 = st.columns(2, gap="small")
        with b1:
            st.button("Stop Conversation", key="gs_agent_stop", on_click=_stop)
        with b2:
            st.button("New conversation", key="gg_agent_new", on_click=_reset_conversation)

    with st.container(key="card_agent_input"):
        card_head("mic", "Ask your question", "Press the microphone to start speaking, press stop, and your question is sent automatically.")
        audio = st.audio_input("Record your question", key=f"agent_mic_{state.agent_gen}", label_visibility="collapsed")
    typed = st.chat_input("...or type your question here", disabled=not usable)

    turn_done = spoken = False
    if typed:  # a typed question always wins; a recording waiting beside it is marked as seen so it is not sent later
        if audio is not None:
            state.agent_last_hash = hashlib.sha256(audio.getvalue()).hexdigest()
        turn_done = _run_turn(user, lang, voice, speak_back, typed=typed)
    elif audio is not None and usable:
        data = audio.getvalue()
        digest = hashlib.sha256(data).hexdigest()
        if digest != state.agent_last_hash:
            state.agent_last_hash = digest
            spoken = True
            turn_done = _run_turn(user, lang, voice, speak_back, audio_bytes=data)
    if turn_done and spoken:
        state.agent_gen += 1  # fresh microphone for the next question
        st.rerun()

    if state.agent_error:
        notice("error", *state.agent_error)
    if state.agent_warn:
        notice("warn", *state.agent_warn)

    with st.container(key="card_agent_chat"):
        card_head("bot", "Conversation", "Your questions and the assistant's answers.")
        _render_chat(state.agent_msgs)
        clip = state.agent_audio
        if clip:
            st.caption("Spoken answer (use the player to play, pause or replay):")
            st.audio(clip["audio"], format=clip["mime"], autoplay=bool(clip.get("fresh")))
            clip["fresh"] = False
