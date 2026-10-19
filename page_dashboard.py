"""Dashboard: welcome, quick-access cards, real usage numbers, language support checker, recent activity."""

import streamlit as st

import database as db
import languages as L
import ui

QUICK = [
    ("stt", "mic", "Speech-to-Text", "Record a clip or upload a file and get an editable transcript."),
    ("tts", "volume", "Text-to-Speech", "Turn text into natural Indian-language speech and download it."),
    ("agent", "bot", "AI Voice Agent", "Ask questions by voice and hear the answer."),
]


def dashboard_page():
    user = ui.require_login()
    ui.show_flash()
    first = user["display_name"].split(" ")[0]
    ui.page_header(f"Welcome, {first}", "Pick a workspace below, or review what you have done so far.", "wave")

    cols = st.columns(3, gap="medium")
    targets = {"stt": "live", "tts": "tts", "agent": "agent"}
    for col, (key, icon_name, title, desc) in zip(cols, QUICK):
        with col:
            with st.container(key=f"card_quick_{key}"):
                ui.card_head(icon_name, title, desc)
                st.page_link(ui.PAGES[targets[key]], label=f"Open {title}")

    stats = db.usage_stats(user["id"])
    st.markdown(
        '<div class="stats" style="margin-top:1.4rem">'
        f'<div class="stat"><b>{stats["transcripts"]}</b><span>Saved transcripts</span></div>'
        f'<div class="stat"><b>{stats["speech"]}</b><span>Speech generations</span></div>'
        f'<div class="stat"><b>{stats["conversations"]}</b><span>Agent conversations</span></div>'
        f'<div class="stat"><b>{stats["words"]}</b><span>Words transcribed</span></div>'
        '</div>', unsafe_allow_html=True)

    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(key="card_dash_lang"):
            ui.card_head("languages", "Language support", "Check what each language can do today.")
            ids = [l.id for l in L.languages_for("agent")]
            current = st.session_state.get("lang_id") or user["default_language"]
            chosen = st.selectbox("Language (click and type to search)", ids, index=ids.index(current) if current in ids else 0,
                                  format_func=lambda i: L.get_language(i).name, key="dash_lang")
            st.session_state["lang_id"] = chosen
            lang = L.get_language(chosen)
            for cap, name in (("stt", "Speech-to-Text"), ("tts", "Text-to-Speech"), ("agent", "Voice Agent")):
                s, c = L.status(lang, cap), L.code(lang, cap)
                kind = {L.SUPPORTED: "ready", L.EXPERIMENTAL: "warn"}.get(s, "idle")
                ui.pill(f"{name}: {L.STATUS_TEXT[s]}" + (f" ({c})" if c and cap != "agent" else ""), kind)
            if lang.note:
                st.caption(lang.note)
    with right:
        with st.container(key="card_dash_recent"):
            ui.card_head("history", "Recent activity", "Your latest work across all workspaces.")
            recent = db.recent_activity(user["id"], 6)
            if not recent:
                ui.empty_state("Nothing here yet. Try a workspace on the left to get started.")
            for r in recent:
                st.markdown(f'<div class="activity"><span class="dot"></span><div><b>{ui.esc(r["kind"])}, {ui.esc(r["detail"])}</b>'
                            f'<small>{ui.esc(ui.fmt_ts(r["created_at"]))}</small><br><small>{ui.esc(r["preview"] or "")}</small></div></div>',
                            unsafe_allow_html=True)
