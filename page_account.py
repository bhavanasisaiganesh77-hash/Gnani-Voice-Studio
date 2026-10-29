"""Profile and Settings."""

import streamlit as st

import database as db
import languages as L
import ui
from ui import notice


def profile_page():
    user = ui.require_login()
    ui.page_header("Profile", "user")
    with st.container(key="card_profile"):
        st.markdown(
            f'<div class="user-card plain"><span class="avatar big">{ui.esc(user["display_name"][:1].upper())}</span>'
            f'<div class="who"><b class="big">{ui.esc(user["display_name"])}</b><small>{ui.esc(user["email"])}</small></div></div>',
            unsafe_allow_html=True)
        if st.button("Sign out", key="gs_profile_logout"):
            ui.logout()


def settings_page():
    user = ui.require_login()
    ui.page_header("Settings", "user")

    with st.container(key="card_set_name"):
        st.subheader("Name")
        with st.form("name_form"):
            new_name = st.text_input("Display name", value=user["display_name"])
            if st.form_submit_button("Save", key="gp_set_name"):
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
            pref_hist = st.toggle("Save to history", value=user["save_history"])
            pref_itn = st.toggle("Format numbers", value=user["apply_itn"])
            if st.form_submit_button("Save", key="gp_set_prefs"):
                db.update_preferences(user["id"], pref_lang, pref_hist, pref_itn)
                st.session_state["lang_id"] = pref_lang
                st.toast("Saved")
                st.rerun()

    if user["has_password"]:
        with st.container(key="card_set_pw"):
            st.subheader("Password")
            with st.form("pw_form", clear_on_submit=True):
                cur = st.text_input("Current password", type="password", autocomplete="current-password")
                new = st.text_input("New password", type="password", autocomplete="new-password")
                conf = st.text_input("Confirm new password", type="password", autocomplete="new-password")
                if st.form_submit_button("Change password", key="gp_set_pw"):
                    if new != conf:
                        notice("error", "Passwords do not match")
                    else:
                        error = db.change_password(user["id"], cur, new)
                        if error:
                            notice("error", "Password not changed", error)
                        else:
                            ui.logout("Password changed. Log in again.")

    with st.expander("Delete account"):
        with st.form("delete_form"):
            pw = confirm = ""
            if user["has_password"]:
                pw = st.text_input("Password", type="password", autocomplete="current-password")
            else:
                confirm = st.text_input("Type DELETE to confirm")
            sure = st.checkbox("Delete my account and all saved data")
            if st.form_submit_button("Delete account", key="gs_set_delete"):
                if not sure:
                    notice("warn", "Tick the box to confirm")
                else:
                    error = db.delete_user(user["id"], pw, confirm)
                    if error:
                        notice("error", "Account not deleted", error)
                    else:
                        ui.logout("Your account has been deleted.")
