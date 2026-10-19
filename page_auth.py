"""Log in, Sign up, and Continue with Google (signed-out pages)."""

import streamlit as st

import database as db
import google_auth
import languages as L
import ui
from styles import AUTH_CSS
from ui import notice


def _brand_panel():
    with st.container(key="auth_brand"):
        have, total = L.coverage("agent")
        st.markdown(
            f"{ui.BRAND_MARK}<h2>Speak in your language. Get text, voices and answers.</h2>"
            "<p>Gnani Voice Studio turns speech into text, text into speech, and lets you talk to an AI assistant.</p>"
            f"<ul><li>{have} of the 22 Eighth Schedule languages fully supported, plus English</li>"
            "<li>Speech-to-text, text-to-speech and a voice agent</li>"
            "<li>Your transcripts and history stay private to your account</li></ul>",
            unsafe_allow_html=True,
        )


def _google_section():
    st.markdown('<div class="or-line">or</div>', unsafe_allow_html=True)
    if google_auth.is_configured():
        if st.button("Continue with Google", key="gg_google"):
            st.login("google")
        return
    missing = google_auth.missing_settings()
    if not google_auth.authlib_installed():
        missing = missing + ["the Authlib package (run: pip install -r requirements.txt)"]
    notice("info", "Continue with Google is not set up yet",
           "The site owner still needs to add Google sign-in settings in .streamlit/secrets.toml. Missing: "
           + ", ".join(missing) + ". Until then, use your email and password.")


def login_page():
    if ui.current_user():
        st.switch_page(ui.PAGES["dashboard"])
    st.markdown(AUTH_CSS, unsafe_allow_html=True)
    left, right = st.columns(2, gap="large")
    with left:
        _brand_panel()
    with right:
        with st.container(key="card_auth"):
            st.markdown('<h1 class="auth-title">Welcome back</h1><p class="auth-sub">Log in to your Voice Studio.</p>',
                        unsafe_allow_html=True)
            ui.show_flash()
            with st.form("login_form"):
                email = st.text_input("Email address", autocomplete="email")
                password = st.text_input("Password", type="password", autocomplete="current-password")
                submitted = st.form_submit_button("Log in", key="gp_login_submit")
            if submitted:
                user, error = db.authenticate(email, password)
                if error:
                    notice("error", "Could not log in", error)
                    st.caption("If you created your account with Google, use Continue with Google below.")
                else:
                    ui.start_session(user)
                    st.rerun()
            _google_section()
            st.page_link(ui.PAGES["signup"], label="New here? Create an account")


def signup_page():
    if ui.current_user():
        st.switch_page(ui.PAGES["dashboard"])
    st.markdown(AUTH_CSS, unsafe_allow_html=True)
    left, right = st.columns(2, gap="large")
    with left:
        _brand_panel()
    with right:
        with st.container(key="card_auth"):
            st.markdown('<h1 class="auth-title">Create your account</h1><p class="auth-sub">It takes less than a minute.</p>',
                        unsafe_allow_html=True)
            with st.form("signup_form"):
                name = st.text_input("Display name", autocomplete="name")
                email = st.text_input("Email address", autocomplete="email")
                password = st.text_input("Password", type="password", autocomplete="new-password",
                                         help="At least 8 characters, with a letter and a number.")
                confirm = st.text_input("Confirm password", type="password", autocomplete="new-password")
                submitted = st.form_submit_button("Create account", key="gp_signup_submit")
            if submitted:
                if password != confirm:
                    notice("error", "Passwords do not match", "Type the same password in both fields.")
                else:
                    user, error = db.create_user(email, name, password)
                    if error:
                        notice("error", "Could not create the account", error)
                    else:
                        st.session_state["flash"] = ("ok", "Account created. Log in to continue.")
                        st.switch_page(ui.PAGES["login"])
            _google_section()
            st.page_link(ui.PAGES["login"], label="Already have an account? Log in")


def sync_google_login():
    """Called on every run. If Google has authenticated this browser, start (or refresh) our own session."""
    if ui.current_user():
        return
    claims = google_auth.identity()
    if claims is None:
        return
    ok, reason = google_auth.validate_claims(claims)
    if not ok:
        if reason != "expired":  # an old cookie just means "please sign in again", so stay quiet
            st.session_state["flash"] = ("error", reason)
        st.logout()
        return
    user, error, note = db.sign_in_with_google(claims["sub"], claims["email"], claims["email_verified"], claims.get("name") or "")
    if error:
        st.logout()
        return
    ui.start_session(user)
    if note:
        st.session_state["flash"] = ("info", note)
