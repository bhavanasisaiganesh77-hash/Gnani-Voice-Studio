"""Gnani Voice Studio - launch this file: streamlit run streamlit_app.py

This file sets up the app, background, and navigation.
Each page lives in its own file.
"""
import base64
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Gnani Voice Studio",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="auto",
)

import assistant
import database as db
import ui
from page_account import profile_page, settings_page
from page_auth import login_page, signup_page, sync_google_login
from page_dashboard import dashboard_page
from page_history import history_page
from page_stt import live_page, upload_page
from page_tts import tts_page
from styles import BASE_CSS


def add_background():
    """Apply the local JPEG background without breaking the app if missing."""
    image_path = (
        Path(__file__).resolve().parent
        / "assets"
        / "gnani_background.jpeg"
    )

    if not image_path.is_file():
        return

    try:
        image_data = base64.b64encode(
            image_path.read_bytes()
        ).decode("utf-8")

        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image:
                    linear-gradient(
                        rgba(255, 255, 255, 0.35),
                        rgba(255, 255, 255, 0.35)
                    ),
                    url("data:image/jpeg;base64,{image_data}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
    except OSError:
        # A background image problem should never prevent the app from loading.
        pass


@st.cache_resource
def _init_database():
    db.init_db()
    return True


_init_database()

P = st.Page

pages = {
    "login": P(
        login_page,
        title="Log in",
        icon=":material/login:",
        url_path="login",
        default=True,
    ),
    "signup": P(
        signup_page,
        title="Sign up",
        icon=":material/person_add:",
        url_path="signup",
    ),
    "dashboard": P(
        dashboard_page,
        title="Dashboard",
        icon=":material/dashboard:",
        url_path="dashboard",
        default=True,
    ),
    "live": P(
        live_page,
        title="Speak Live",
        icon=":material/mic:",
        url_path="live-speech-to-text",
    ),
    "upload": P(
        upload_page,
        title="Record / Upload",
        icon=":material/upload_file:",
        url_path="audio-upload",
    ),
    "tts": P(
        tts_page,
        title="Text to Speech",
        icon=":material/record_voice_over:",
        url_path="text-to-speech",
    ),
    "history": P(
        history_page,
        title="History",
        icon=":material/history:",
        url_path="history",
    ),
    "profile": P(
        profile_page,
        title="Profile",
        icon=":material/person:",
        url_path="profile",
    ),
    "settings": P(
        settings_page,
        title="Settings",
        icon=":material/settings:",
        url_path="settings",
    ),
}

ui.PAGES.update(pages)

ui.enforce_session()
sync_google_login()

# Keep the existing app styling, then apply the background.
st.markdown(BASE_CSS, unsafe_allow_html=True)
add_background()

user = ui.current_user()

if user:
    logo = Path(__file__).resolve().parent / "assets" / "logo.svg"

    if logo.exists():
        st.logo(str(logo), size="large")

    nav = st.navigation(
        [
            pages[k]
            for k in (
                "dashboard",
                "live",
                "upload",
                "tts",
                "history",
                "profile",
                "settings",
            )
        ],
        position="sidebar",
    )

    with st.sidebar:
        st.markdown(
            f'<div class="user-card">'
            f'<span class="avatar">'
            f'{ui.esc(user["display_name"][:1].upper())}'
            f'</span>'
            f'<div class="who">'
            f'<b>{ui.esc(user["display_name"])}</b>'
            f'<small>{ui.esc(user["email"])}</small>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        if st.button("Sign out", key="gs_sidebar_signout"):
            ui.logout()

else:
    nav = st.navigation(
        [pages["login"], pages["signup"]],
        position="hidden",
    )

nav.run()

if user:
    # Keep the existing floating assistant behavior.
    assistant.render()