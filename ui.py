"""Shared building blocks used by every page: icons, notices, session handling, language picker, copy button."""

import html
import json
import os
import time
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

import database as db
import languages as L

esc = html.escape
IDLE_TIMEOUT_SECONDS = int(os.getenv("SESSION_IDLE_MINUTES", "60")) * 60

# Filled in by streamlit_app.py so pages can link to each other: PAGES["tts"], PAGES["login"], ...
PAGES = {}

# ------------------------------------------------------------------------------ icons (Lucide style, 24x24, 2px round stroke)
_PATHS = {
    "mic": '<rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
    "upload": '<path d="M12 16V4M7 9l5-5 5 5M4 20h16"/>',
    "volume": '<path d="M11 5 6 9H2v6h4l5 4V5z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M19 5a9 9 0 0 1 0 14"/>',
    "bot": '<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 8V5M9 13v2M15 13v2"/><circle cx="12" cy="4" r="1"/>',
    "history": '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "wave": '<path d="M4 10v4M8 6v12M12 3v18M16 7v10M20 10v4"/>',
    "languages": '<path d="m5 8 6 6M4 14l6-6 2-3M2 5h12M7 2h1M22 22l-5-10-5 10M14 18h6"/>',
}


def icon(name: str, size: int = 22) -> str:
    return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{_PATHS[name]}</svg>')


BRAND_MARK = f'<span class="brand-mark" style="color:#fff">{icon("wave", 26)}</span>'
LOADING = ('<div class="loading" role="status" aria-live="polite"><div class="bars"><span></span><span></span><span></span>'
           '<span></span><span></span></div><div><b>{title}</b><small>{detail}</small></div></div>')


# ------------------------------------------------------------------------------ small components
def notice(kind, title, detail=""):
    st.markdown(f'<div class="notice {kind}" role="alert"><b>{esc(title)}</b>{esc(detail)}</div>', unsafe_allow_html=True)


def pill(text, kind="idle"):
    st.markdown(f'<span class="pill {kind}">{esc(text)}</span>', unsafe_allow_html=True)


def card_head(icon_name, title, desc):
    st.markdown(f'<div class="card-head"><span class="chip">{icon(icon_name)}</span><div><h3>{esc(title)}</h3><p>{esc(desc)}</p></div></div>',
                unsafe_allow_html=True)


def page_header(title, lede, icon_name=None):
    chip = f'<span class="chip">{icon(icon_name)}</span>' if icon_name else ""
    st.markdown(f'<div class="page-head">{chip}<h1 class="page-title">{esc(title)}</h1></div><p class="page-lede">{esc(lede)}</p>',
                unsafe_allow_html=True)


def show_loading(slot, title, detail=""):
    slot.markdown(LOADING.format(title=esc(title), detail=esc(detail)), unsafe_allow_html=True)


def empty_state(text):
    st.markdown(f'<div class="empty">{esc(text)}</div>', unsafe_allow_html=True)


def show_flash():
    flash = st.session_state.pop("flash", None)
    if flash:
        notice(*flash)


def fmt_ts(iso):
    try:
        return datetime.fromisoformat(iso).astimezone().strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return iso


def copy_button(text, disabled, aria_label, label="Copy Transcript"):
    """Glass copy button. It reads the live text box, so unsaved edits are copied too."""
    template = """
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@600&display=swap" rel="stylesheet">
<style>
  html,body{margin:0;background:transparent}
  button{width:100%;height:46px;border-radius:14px;font:600 15.5px 'Figtree',system-ui,sans-serif;color:#fff;cursor:pointer;
    border:1px solid rgba(255,255,255,.5);background:linear-gradient(135deg,rgba(200,76,6,.96),rgba(165,55,3,.97));
    box-shadow:0 12px 26px -12px rgba(165,55,3,.75),inset 0 1px 0 rgba(255,255,255,.38);transition:transform .18s,filter .18s}
  button:hover:not(:disabled){transform:translateY(-1px);filter:brightness(1.07)}
  button:active:not(:disabled){transform:scale(.985)}
  button:disabled{opacity:.5;cursor:not-allowed;box-shadow:none}
  button:focus-visible{outline:3px solid #FF9A57;outline-offset:2px}
  @media (prefers-reduced-motion:reduce){button{transition:none}}
</style>
<button id="b" __DISABLED__>__LABEL_TEXT__</button>
<script>
  const fallback = __TEXT__;
  const btn = document.getElementById('b');
  const idle = btn.textContent;
  function currentText(){
    try{ const ta = window.parent.document.querySelector('textarea[aria-label=__LABEL__]'); if(ta) return ta.value; }catch(e){}
    return fallback;
  }
  async function copy(t){
    try{ await navigator.clipboard.writeText(t); return true; }
    catch(e){
      const a=document.createElement('textarea'); a.value=t; document.body.appendChild(a); a.select();
      let ok=false; try{ ok=document.execCommand('copy'); }catch(_){} a.remove(); return ok;
    }
  }
  btn.addEventListener('click', async ()=>{
    const ok = await copy(currentText());
    btn.textContent = ok ? 'Copied to clipboard' : 'Copy failed';
    setTimeout(()=>{ btn.textContent = idle; }, 1800);
  });
</script>
"""
    safe = lambda s: json.dumps(s).replace("</", "<\\/")
    page_html = (template.replace("__TEXT__", safe(text)).replace("__LABEL__", safe(aria_label))
                 .replace("__LABEL_TEXT__", esc(label)).replace("__DISABLED__", "disabled" if disabled else ""))
    if hasattr(st, "iframe"):  # newer Streamlit: components.html is deprecated in favour of st.iframe
        st.iframe(page_html, height=50)
    else:
        components.html(page_html, height=50)


# ------------------------------------------------------------------------------ session
def current_user():
    return st.session_state.get("user")


def start_session(user):
    st.session_state.clear()
    st.session_state["user"] = user
    st.session_state["auth_version"] = user["auth_version"]
    st.session_state["last_active"] = time.time()


def logout(message="You have been logged out."):
    from google_auth import identity
    was_google = identity() is not None
    st.session_state.clear()
    st.session_state["flash"] = ("info", message)
    if was_google:
        st.logout()  # clears Streamlit's Google identity cookie, otherwise the next run would sign in again
    else:
        st.rerun()


def enforce_session():
    """Expire idle sessions, and sign out sessions invalidated by a password change or account removal."""
    user = current_user()
    if not user:
        return
    now = time.time()
    if now - st.session_state.get("last_active", now) > IDLE_TIMEOUT_SECONDS:
        logout("Your session expired because it was idle. Log in again to continue.")
    st.session_state["last_active"] = now
    fresh = db.get_user(user["id"])
    if fresh is None:
        logout("This account no longer exists.")
    if fresh["auth_version"] != st.session_state.get("auth_version"):
        logout("Your sign-in details changed, so you were signed out. Log in again.")
    st.session_state["user"] = fresh


def require_login():
    user = current_user()
    if not user:
        st.session_state["flash"] = ("info", "Log in to continue.")
        st.switch_page(PAGES["login"])
        st.stop()
    return user


# ------------------------------------------------------------------------------ language picker (central config)
CAPABILITY_NAME = {"stt": "speech-to-text", "tts": "text-to-speech", "agent": "the voice agent"}


def language_picker(page_key: str, capability: str):
    """Searchable selector for one capability. Returns (language, usable).

    Unsupported languages stay visible, are labelled, and block the action so nobody assumes they work.
    """
    user = current_user()
    only_usable = st.toggle("Show only supported languages", value=False, key=f"{page_key}_only_usable")
    langs = L.usable_languages(capability) if only_usable else L.languages_for(capability)
    ids = [l.id for l in langs]
    current = st.session_state.get("lang_id") or user["default_language"]
    index = ids.index(current) if current in ids else 0
    chosen = st.selectbox("Language (click and type to search)", ids, index=index,
                          format_func=lambda i: L.label(L.get_language(i), capability), key=f"{page_key}_lang")
    st.session_state["lang_id"] = chosen
    lang = L.get_language(chosen)
    s, c = L.status(lang, capability), L.code(lang, capability)
    if s == L.SUPPORTED:
        pill(f"Supported for {CAPABILITY_NAME[capability]}, code {c}", "ready")
        if lang.note and capability != "agent":
            st.caption(lang.note)
        if capability == "agent":
            st.caption("The agent needs verified speech-to-text and text-to-speech for this language. "
                       "How well your AI model answers in it is not verified by this app, so test it.")
    elif s == L.EXPERIMENTAL:
        notice("warn", "Experimental option", lang.note)
    else:
        why = lang.note
        if capability == "agent" and lang.stt_status != L.UNSUPPORTED and lang.tts_status != L.UNSUPPORTED:
            why = "The agent needs both verified speech-to-text and text-to-speech for a language."
        notice("warn", f"{lang.name} is not supported yet for {CAPABILITY_NAME[capability]}",
               f"{why} Choose a supported language to continue.")
    return lang, L.is_usable(lang, capability)


def coverage_expander():
    stt, total = L.coverage("stt")
    tts, _ = L.coverage("tts")
    with st.expander(f"Language coverage: {stt} of {total} Eighth Schedule languages for speech-to-text, {tts} for text-to-speech"):
        st.caption("Codes come from Gnani's official API documentation. Gnani publishes no regional-dialect codes, so none are offered. "
                   "The voice agent needs both.")
        rows = [{"Language": l.name, "Native name": l.native,
                 "Speech-to-text": l.stt_code or "not supported yet",
                 "Text-to-speech": l.tts_code or "not supported yet",
                 "Voice agent": "Supported" if l.agent_status == L.SUPPORTED else "Not supported yet"}
                for l in L.languages_for("agent")]
        st.dataframe(rows, hide_index=True)


def service_status() -> dict:
    """Simple yes/no setup checks. Never returns a secret value."""
    import google_auth
    import gnani_client
    import llm_client
    return {
        "gnani": bool(gnani_client.get_api_key()),
        "llm": llm_client.is_configured(),
        "llm_missing": llm_client.missing_settings(),
        "google": google_auth.is_configured(),
        "google_missing": google_auth.missing_settings(),
    }
