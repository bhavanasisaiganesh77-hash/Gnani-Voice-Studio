"""Shared building blocks used by every page: icons, notices, session handling, language picker, copy button."""

import html
import json
import logging
import os
import time
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

import database as db
import languages as L

esc = html.escape
log = logging.getLogger("voicestudio.ui")
_logged = set()
IDLE_TIMEOUT_SECONDS = int(os.getenv("SESSION_IDLE_MINUTES", "60")) * 60

# Filled in by streamlit_app.py so pages can link to each other: PAGES["tts"], PAGES["login"], ...
PAGES = {}

# ------------------------------------------------------------------------------ icons (Lucide style, 24x24, 2px round stroke)
_PATHS = {
    "mic": '<rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
    "upload": '<path d="M12 16V4M7 9l5-5 5 5M4 20h16"/>',
    "volume": '<path d="M11 5 6 9H2v6h4l5 4V5z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M19 5a9 9 0 0 1 0 14"/>',
    "history": '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "wave": '<path d="M4 10v4M8 6v12M12 3v18M16 7v10M20 10v4"/>',
}


def icon(name: str, size: int = 22) -> str:
    return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{_PATHS[name]}</svg>')


BRAND_MARK = f'<span class="brand-mark" style="color:#fff">{icon("wave", 26)}</span>'
LOADING = ('<div class="loading" role="status" aria-live="polite"><div class="bars"><span></span><span></span><span></span>'
           '<span></span><span></span></div><b>{title}</b></div>')


# ------------------------------------------------------------------------------ small components
def notice(kind, title, detail=""):
    st.markdown(f'<div class="notice {kind}" role="alert"><b>{esc(title)}</b>{esc(detail)}</div>', unsafe_allow_html=True)


def pill(text, kind="idle"):
    st.markdown(f'<span class="pill {kind}">{esc(text)}</span>', unsafe_allow_html=True)


def card_head(icon_name, title):
    st.markdown(f'<div class="card-head"><span class="chip">{icon(icon_name)}</span><h3>{esc(title)}</h3></div>', unsafe_allow_html=True)


def page_header(title, icon_name=None):
    chip = f'<span class="chip">{icon(icon_name)}</span>' if icon_name else ""
    st.markdown(f'<div class="page-head">{chip}<h1 class="page-title">{esc(title)}</h1></div>', unsafe_allow_html=True)


def show_loading(slot, title):
    slot.markdown(LOADING.format(title=esc(title)), unsafe_allow_html=True)


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


def speech_ready() -> bool:
    """True when speech services are configured. If not, the problem goes to the server log, not the screen."""
    from gnani_client import get_api_key
    ok = bool(get_api_key())
    if not ok and "gnani" not in _logged:
        _logged.add("gnani")
        log.error("GNANI_API_KEY is not set; speech features are disabled.")
    return ok


def unavailable():
    notice("error", "Service unavailable", "Please try again later.")


# ------------------------------------------------------------------------------ duplicate-click guard
def debounce(name: str, fingerprint, seconds: float = 8.0) -> bool:
    """True if the action should run. The same input submitted again within a few seconds is ignored,
    so double clicks never trigger two paid API calls."""
    now = time.time()
    last = st.session_state.get(f"_debounce_{name}")
    if last and last[0] == fingerprint and now - last[1] < seconds:
        return False
    st.session_state[f"_debounce_{name}"] = (fingerprint, now)
    return True


# ------------------------------------------------------------------------------ language picker (central config)
def language_picker(page_key: str, capability: str):
    """Searchable selector for one capability. Returns (language, usable).

    Unavailable languages stay visible and labelled, and block the action.
    """
    user = current_user()
    langs = L.languages_for(capability)
    ids = [l.id for l in langs]
    current = st.session_state.get("lang_id") or user["default_language"]
    index = ids.index(current) if current in ids else 0
    chosen = st.selectbox("Language", ids, index=index,
                          format_func=lambda i: L.label(L.get_language(i), capability), key=f"{page_key}_lang")
    st.session_state["lang_id"] = chosen
    lang = L.get_language(chosen)
    usable = L.is_usable(lang, capability)
    if not usable:
        notice("warn", f"{lang.name} isn't available yet")
    return lang, usable
