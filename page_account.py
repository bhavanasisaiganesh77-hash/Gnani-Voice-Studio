"""My Profile and Settings."""

import streamlit as st

import database as db
import languages as L
import ui
from ui import notice


def profile_page():
    user = ui.require_login()
    ui.page_header("My Profile", "Your account details and activity.", "user")
    with st.container(key="card_profile"):
        st.markdown(
            f'<div class="user-card" style="border:0;padding:0;margin:0 0 1rem;background:none;box-shadow:none">'
            f'<span class="avatar big">{ui.esc(user["display_name"][:1].upper())}</span>'
            f'<div class="who"><b style="font-size:1.25rem">{ui.esc(user["display_name"])}</b>'
            f'<small>{ui.esc(user["email"])}</small><small>Member since {ui.esc(ui.fmt_ts(user["created_at"]))}</small></div></div>',
            unsafe_allow_html=True)
        ui.pill("Signed in with: " + ", ".join(db.sign_in_methods(user["id"])), "ready")
        s = db.usage_stats(user["id"])
        st.caption(f"{s['transcripts']} transcripts, {s['speech']} speech generations and {s['conversations']} conversations saved.")
        if st.button("Log out", key="gs_profile_logout"):
            ui.logout()


def settings_page():
    user = ui.require_login()
    ui.page_header("Settings", "Your name, preferences, password and setup status.", "user")

    with st.container(key="card_set_name"):
        st.subheader("Display name")
        with st.form("name_form"):
            new_name = st.text_input("Display name", value=user["display_name"])
            if st.form_submit_button("Save name", key="gp_set_name"):
                error = db.update_display_name(user["id"], new_name)
                if error:
                    notice("error", "Name not saved", error)
                else:
                    st.rerun()

    with st.container(key="card_set_prefs"):
        st.subheader("Preferences")
        with st.form("prefs_form"):
            ids = [l.id for l in L.usable_languages("stt")]
            default_id = user["default_language"] if user["default_language"] in ids else "telugu"
            pref_lang = st.selectbox("Default language", ids, index=ids.index(default_id),
                                     format_func=lambda i: L.label(L.get_language(i), "stt"))
            pref_hist = st.toggle("Save transcripts and generated speech to my history", value=user["save_history"])
            pref_itn = st.toggle("Write numbers, dates and currency in their usual form by default", value=user["apply_itn"])
            if st.form_submit_button("Save preferences", key="gp_set_prefs"):
                db.update_preferences(user["id"], pref_lang, pref_hist, pref_itn)
                st.session_state["lang_id"] = pref_lang
                st.toast("Preferences saved.")
                st.rerun()

    with st.container(key="card_set_pw"):
        st.subheader("Password")
        if not user["has_password"]:
            st.write("This account signs in with Google, so it has no password.")
        else:
            with st.form("pw_form", clear_on_submit=True):
                cur = st.text_input("Current password", type="password", autocomplete="current-password")
                new = st.text_input("New password", type="password", autocomplete="new-password", help="At least 8 characters, with a letter and a number.")
                conf = st.text_input("Confirm new password", type="password", autocomplete="new-password")
                if st.form_submit_button("Change password", key="gp_set_pw"):
                    if new != conf:
                        notice("error", "Passwords do not match", "Type the same new password in both fields.")
                    else:
                        error = db.change_password(user["id"], cur, new)
                        if error:
                            notice("error", "Password not changed", error)
                        else:
                            ui.logout("Password changed. Log in again with your new password.")

    with st.container(key="card_set_status"):
        st.subheader("Setup status")
        st.caption("Shows only whether each setting exists. Secret values are never displayed.")
        s = ui.service_status()
        ui.pill("Gnani API key (speech-to-text and text-to-speech): " + ("found" if s["gnani"] else "missing"), "done" if s["gnani"] else "warn")
        ui.pill("AI model for the voice agent: " + ("configured" if s["llm"] else "missing " + ", ".join(s["llm_missing"])), "done" if s["llm"] else "warn")
        ui.pill("Continue with Google: " + ("configured" if s["google"] else "not configured"), "done" if s["google"] else "warn")

    with st.expander("Delete account"):
        st.write("This permanently deletes your account and everything saved in it. It cannot be undone.")
        with st.form("delete_form"):
            pw = confirm = ""
            if user["has_password"]:
                pw = st.text_input("Confirm with your password", type="password", autocomplete="current-password")
            else:
                confirm = st.text_input("Type DELETE to confirm")
            sure = st.checkbox("I understand this is permanent")
            if st.form_submit_button("Delete my account", key="gs_set_delete"):
                if not sure:
                    notice("warn", "Tick the box to confirm", "")
                else:
                    error = db.delete_user(user["id"], pw, confirm)
                    if error:
                        notice("error", "Account not deleted", error)
                    else:
                        ui.logout("Your account has been deleted.")
