"""Dashboard: welcome, quick actions and recent activity."""

import streamlit as st

import database as db
import ui


def dashboard_page():
    user = ui.require_login()
    ui.show_flash()
    ui.page_header(f"Welcome, {user['display_name'].split(' ')[0]}")

    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(key="card_quick_stt"):
            ui.card_head("mic", "Speech to Text")
            st.page_link(ui.PAGES["live"], label="Speak Live")
            st.page_link(ui.PAGES["upload"], label="Record / Upload")
    with right:
        with st.container(key="card_quick_tts"):
            ui.card_head("volume", "Text to Speech")
            st.page_link(ui.PAGES["tts"], label="Generate Speech")

    stats = db.usage_stats(user["id"])
    if stats["transcripts"] or stats["speech"]:
        st.markdown(f'<div class="stats"><div class="stat"><b>{stats["transcripts"]}</b><span>Transcripts</span></div>'
                    f'<div class="stat"><b>{stats["speech"]}</b><span>Speech files</span></div></div>', unsafe_allow_html=True)

    recent = db.recent_activity(user["id"], 6)
    if recent:
        with st.container(key="card_dash_recent"):
            ui.card_head("history", "Recent activity")
            for r in recent:
                st.markdown(
                    f'<div class="activity"><span class="dot"></span><div><b>{ui.esc(r["kind"])} · {ui.esc(r["detail"])}</b>'
                    f'<small>{ui.esc(ui.fmt_ts(r["created_at"]))}</small></div></div>', unsafe_allow_html=True)
