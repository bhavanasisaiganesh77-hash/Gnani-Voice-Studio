"""Gnani Voice Studio - launch this file:  streamlit run streamlit_app.py

This file only sets up the app and the navigation. Each page lives in its own file:
  page_auth.py (login, sign up, Google)   page_dashboard.py   page_stt.py (live + upload)
  page_tts.py   page_agent.py   page_history.py   page_account.py (profile + settings)
API calls live in gnani_client.py (speech) and llm_client.py (AI model). Data lives in database.py.
"""

from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Gnani Voice Studio", page_icon="🎙️", layout="wide", initial_sidebar_state="auto")

import database as db
import ui
from page_account import profile_page, settings_page
from page_agent import agent_page
from page_auth import login_page, signup_page, sync_google_login
from page_dashboard import dashboard_page
from page_history import history_page
from page_stt import live_page, upload_page
from page_tts import tts_page
from styles import BASE_CSS


@st.cache_resource
def _init_database():
    db.init_db()
    return True


_init_database()

P = st.Page
pages = {
    "login": P(login_page, title="Log in", icon=":material/login:", url_path="login", default=True),
    "signup": P(signup_page, title="Sign up", icon=":material/person_add:", url_path="signup"),
    "dashboard": P(dashboard_page, title="Dashboard", icon=":material/dashboard:", url_path="dashboard", default=True),
    "live": P(live_page, title="Live Speech-to-Text", icon=":material/mic:", url_path="live-speech-to-text"),
    "upload": P(upload_page, title="Audio Upload & Transcription", icon=":material/upload_file:", url_path="audio-upload"),
    "tts": P(tts_page, title="Text-to-Speech", icon=":material/record_voice_over:", url_path="text-to-speech"),
    "agent": P(agent_page, title="AI Voice Agent", icon=":material/smart_toy:", url_path="ai-voice-agent"),
    "history": P(history_page, title="History", icon=":material/history:", url_path="history"),
    "profile": P(profile_page, title="My Profile", icon=":material/person:", url_path="profile"),
    "settings": P(settings_page, title="Settings", icon=":material/settings:", url_path="settings"),
}
ui.PAGES.update(pages)

ui.enforce_session()
sync_google_login()  # if Google has authenticated this browser, start our own session
st.markdown(BASE_CSS, unsafe_allow_html=True)

user = ui.current_user()
if user:
    logo = Path(__file__).parent / "assets" / "logo.svg"
    if logo.exists():  # a missing logo file must never stop the app
        st.logo(str(logo), size="large")
    nav = st.navigation(
        {"Workspace": [pages["dashboard"], pages["live"], pages["upload"], pages["tts"], pages["agent"]],
         "Account": [pages["history"], pages["profile"], pages["settings"]]},
        position="sidebar",
    )
    with st.sidebar:
        st.markdown(f'<div class="user-card"><span class="avatar">{ui.esc(user["display_name"][:1].upper())}</span>'
                    f'<div class="who"><b>{ui.esc(user["display_name"])}</b><small>{ui.esc(user["email"])}</small></div></div>',
                    unsafe_allow_html=True)
        if st.button("Sign out", key="gs_sidebar_signout"):
            ui.logout()
else:
    nav = st.navigation([pages["login"], pages["signup"]], position="hidden")

nav.run()
