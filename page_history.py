"""History: transcripts, generated speech and agent conversations. Every query is scoped to the signed-in user."""

import streamlit as st

import database as db
import ui


def _more(key):
    st.session_state[key] = st.session_state.get(key, 10) + 10


def history_page():
    user = ui.require_login()
    uid = user["id"]  # always from the server-side session, never from user input
    ui.page_header("History", "Everything you saved. Only you can see it.", "history")
    t_trans, t_tts, t_conv = st.tabs(["Transcripts", "Speech", "Conversations"])

    with t_trans:
        total = db.count_history(uid)
        if total == 0:
            ui.empty_state("No saved transcripts yet. Transcriptions from Audio Upload are saved automatically (see Settings); "
                           "on Live Speech-to-Text press Save to history.")
        limit = st.session_state.get("hl_trans", 10)
        for it in db.list_history(uid, limit):
            with st.expander(f"{ui.fmt_ts(it['created_at'])} - {it['source']} - {it['language_name']}"):
                if it["filename"]:
                    st.caption(f"File: {it['filename']}")
                st.text_area("Transcript", it["transcript"], height=150, disabled=True, key=f"h_t_{it['id']}", label_visibility="collapsed")
                a, b = st.columns(2, gap="small")
                with a:
                    st.download_button("Download Transcript", it["transcript"].encode("utf-8"), file_name=f"transcript-{it['id']}.txt",
                                       mime="text/plain", key=f"gg_h_td_{it['id']}")
                with b:
                    st.button("Delete", key=f"gs_h_tx_{it['id']}", on_click=db.delete_history_item, args=(uid, it["id"]))
        if total > limit:
            st.button("Show more", key="gg_h_tmore", on_click=_more, args=("hl_trans",))
        if total:
            with st.expander("Delete all transcripts"):
                st.button("Delete all my transcripts", key="gs_h_tclear", on_click=db.clear_history, args=(uid,))

    with t_tts:
        total = db.count_tts(uid)
        if total == 0:
            ui.empty_state("No generated speech yet. Create some in Text-to-Speech.")
        limit = st.session_state.get("hl_tts", 10)
        for it in db.list_tts(uid, limit):
            with st.expander(f"{ui.fmt_ts(it['created_at'])} - {it['language_name']} - voice {it['voice']}"):
                st.caption(f"{it['model']}, {it['container'].upper()}, speed {it['speed']}")
                st.text_area("Text", it["text"], height=110, disabled=True, key=f"h_s_{it['id']}", label_visibility="collapsed")
                audio, container = db.get_tts_audio(uid, it["id"])
                if audio:
                    mime = "audio/mpeg" if container == "mp3" else "audio/wav"
                    st.audio(audio, format=mime)
                    st.download_button("Download Audio", audio, file_name=f"speech-{it['id']}.{container}", mime=mime, key=f"gg_h_sd_{it['id']}")
                else:
                    st.caption("The audio file was too large to keep, but your text is saved.")
                st.button("Delete", key=f"gs_h_sx_{it['id']}", on_click=db.delete_tts, args=(uid, it["id"]))
        if total > limit:
            st.button("Show more", key="gg_h_smore", on_click=_more, args=("hl_tts",))
        if total:
            with st.expander("Delete all generated speech"):
                st.button("Delete all my speech history", key="gs_h_sclear", on_click=db.clear_tts, args=(uid,))

    with t_conv:
        total = db.count_conversations(uid)
        if total == 0:
            ui.empty_state("No conversations yet. Start one in AI Voice Agent. Only the text is saved, not the audio.")
        limit = st.session_state.get("hl_conv", 10)
        for it in db.list_conversations(uid, limit):
            with st.expander(f"{ui.fmt_ts(it['updated_at'])} - {it['title']} ({it['message_count']} messages)"):
                rows = []
                for m in db.get_messages(uid, it["id"]):
                    who = "You" if m["role"] == "user" else "Assistant"
                    rows.append(f'<div class="bubble {m["role"]}"><small>{who}</small>{ui.esc(m["content"])}</div>')
                st.markdown(f'<div class="chat">{"".join(rows)}</div>', unsafe_allow_html=True)
                st.button("Delete", key=f"gs_h_cx_{it['id']}", on_click=db.delete_conversation, args=(uid, it["id"]))
        if total > limit:
            st.button("Show more", key="gg_h_cmore", on_click=_more, args=("hl_conv",))
        if total:
            with st.expander("Delete all conversations"):
                st.button("Delete all my conversations", key="gs_h_cclear", on_click=db.clear_conversations, args=(uid,))
