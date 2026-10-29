"""History: transcripts, generated speech, and older conversations. Every query is scoped to the signed-in user."""

import streamlit as st

import database as db
import ui


def _more(key):
    st.session_state[key] = st.session_state.get(key, 10) + 10


def _transcripts(uid):
    total = db.count_history(uid)
    if not total:
        ui.empty_state("Nothing saved yet")
        return
    limit = st.session_state.get("hl_trans", 10)
    for it in db.list_history(uid, limit):
        with st.expander(f"{ui.fmt_ts(it['created_at'])} · {it['language_name']}"):
            st.text_area("Transcript", it["transcript"], height=140, disabled=True, key=f"h_t_{it['id']}", label_visibility="collapsed")
            a, b = st.columns(2, gap="small")
            with a:
                st.download_button("Download", it["transcript"].encode("utf-8"), file_name=f"transcript-{it['id']}.txt",
                                   mime="text/plain", key=f"gg_h_td_{it['id']}")
            with b:
                st.button("Delete", key=f"gs_h_tx_{it['id']}", on_click=db.delete_history_item, args=(uid, it["id"]))
    if total > limit:
        st.button("Show more", key="gg_h_tmore", on_click=_more, args=("hl_trans",))
    with st.expander("Delete all"):
        st.button("Delete all transcripts", key="gs_h_tclear", on_click=db.clear_history, args=(uid,))


def _speech(uid):
    total = db.count_tts(uid)
    if not total:
        ui.empty_state("Nothing saved yet")
        return
    limit = st.session_state.get("hl_tts", 10)
    for it in db.list_tts(uid, limit):
        with st.expander(f"{ui.fmt_ts(it['created_at'])} · {it['language_name']} · {it['voice']}"):
            st.text_area("Text", it["text"], height=110, disabled=True, key=f"h_s_{it['id']}", label_visibility="collapsed")
            if it["has_audio"] and st.toggle("Play", key=f"h_play_{it['id']}"):  # audio is loaded only when asked for
                audio, container = db.get_tts_audio(uid, it["id"])
                if audio:
                    mime = "audio/mpeg" if container == "mp3" else "audio/wav"
                    st.audio(audio, format=mime)
                    st.download_button("Download Audio", audio, file_name=f"speech-{it['id']}.{container}", mime=mime, key=f"gg_h_sd_{it['id']}")
            st.button("Delete", key=f"gs_h_sx_{it['id']}", on_click=db.delete_tts, args=(uid, it["id"]))
    if total > limit:
        st.button("Show more", key="gg_h_smore", on_click=_more, args=("hl_tts",))
    with st.expander("Delete all"):
        st.button("Delete all speech", key="gs_h_sclear", on_click=db.clear_tts, args=(uid,))


def _conversations(uid):
    limit = st.session_state.get("hl_conv", 10)
    for it in db.list_conversations(uid, limit):
        with st.expander(f"{ui.fmt_ts(it['updated_at'])} · {it['title']}"):
            rows = []
            for m in db.get_messages(uid, it["id"]):
                rows.append(f'<div class="bubble {m["role"]}">{ui.esc(m["content"])}</div>')
            st.markdown(f'<div class="chat">{"".join(rows)}</div>', unsafe_allow_html=True)
            st.button("Delete", key=f"gs_h_cx_{it['id']}", on_click=db.delete_conversation, args=(uid, it["id"]))
    if db.count_conversations(uid) > limit:
        st.button("Show more", key="gg_h_cmore", on_click=_more, args=("hl_conv",))


def history_page():
    user = ui.require_login()
    uid = user["id"]  # always from the server-side session, never from user input
    ui.page_header("History", "history")
    # older conversations (from the removed voice agent) stay reachable, but only for users who have some
    has_conversations = db.count_conversations(uid) > 0
    tabs = st.tabs(["Transcripts", "Speech"] + (["Conversations"] if has_conversations else []))
    with tabs[0]:
        _transcripts(uid)
    with tabs[1]:
        _speech(uid)
    if has_conversations:
        with tabs[2]:
            _conversations(uid)
