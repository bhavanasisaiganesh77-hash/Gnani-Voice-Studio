"""Floating help assistant, fixed at the bottom-right of every signed-in page.

It is a Streamlit *fragment*: opening it, closing it and chatting only re-run this small function,
never the page behind it. The question is queued by a button callback and answered in the body, so a
double click or a quick re-run cannot send the same question twice.

The conversation lives only in this browser session (st.session_state). Nothing is saved or shared.
The answer logic is in agent_service.py.
"""

import streamlit as st

import agent_service as agent
import ui

DEFAULTS = {"assist_open": False, "assist_msgs": [], "assist_pending": None, "assist_ai_used": 0}


def _toggle():
    st.session_state["assist_open"] = not st.session_state["assist_open"]


def _enqueue(question: str):
    """Button callback. Records the question; the answer is produced in assistant()."""
    question = agent.clean_question(question)
    state = st.session_state
    if not question or state["assist_pending"]:  # ignore empty input and clicks while an answer is in progress
        return
    state["assist_msgs"] = state["assist_msgs"] + [{"role": "user", "content": question}]
    state["assist_pending"] = question


def _submit():
    _enqueue(st.session_state.get("assist_input", ""))


def _clear():
    st.session_state["assist_msgs"] = []
    st.session_state["assist_pending"] = None


def _chat_html(messages, typing=False):
    """Newest message first in the HTML: the CSS flips the list so the view stays pinned to the latest message."""
    bubbles = []
    if typing:
        bubbles.append('<div class="bubble assistant typing" aria-label="Assistant is typing"><i></i><i></i><i></i></div>')
    for m in reversed(messages):
        bubbles.append(f'<div class="bubble {m["role"]}">{ui.esc(m["content"])}</div>')
    bubbles.append(f'<div class="bubble assistant">{ui.esc(agent.GREETING)}</div>')
    return f'<div class="assist-scroll" role="log" aria-live="polite">{"".join(bubbles)}</div>'


@st.fragment
def render():
    """Call once, after the page has rendered, and only for signed-in users."""
    state = st.session_state
    for key, default in DEFAULTS.items():
        state.setdefault(key, default)
    is_open = state["assist_open"]

    with st.container(key="assist_fab"):
        st.button("Assistant", key="gp_assist_fab", on_click=_toggle,
                  icon=":material/close:" if is_open else ":material/auto_awesome:")

    if not is_open:
        return

    with st.container(key="assist_panel"):
        head, clear = st.columns([3, 1], vertical_alignment="center")
        with head:
            st.markdown('<div class="assist-title">Assistant</div>', unsafe_allow_html=True)
        with clear:
            if state["assist_msgs"]:
                st.button("Clear", key="gg_assist_clear", on_click=_clear)

        chat = st.empty()
        pending = state["assist_pending"]
        chat.markdown(_chat_html(state["assist_msgs"], typing=bool(pending)), unsafe_allow_html=True)

        if pending:
            earlier = state["assist_msgs"][:-1]
            reply, used_ai = agent.answer(pending, earlier, state["assist_ai_used"])
            # one assignment block with no Streamlit calls in between, so an interruption cannot half-save it
            state["assist_msgs"] = state["assist_msgs"] + [{"role": "assistant", "content": reply}]
            state["assist_ai_used"] += 1 if used_ai else 0
            state["assist_pending"] = None
            chat.markdown(_chat_html(state["assist_msgs"]), unsafe_allow_html=True)

        if not state["assist_msgs"]:
            with st.container(key="assist_chips"):
                for i, suggestion in enumerate(agent.SUGGESTIONS):
                    st.button(suggestion, key=f"gg_assist_chip_{i}", on_click=_enqueue, args=(suggestion,))

        with st.form("assist_form", clear_on_submit=True, border=False):
            st.text_input("Message", key="assist_input", placeholder="Ask anything", max_chars=agent.MAX_QUESTION_CHARS,
                          label_visibility="collapsed")
            st.form_submit_button("Send", key="gp_assist_send", icon=":material/send:", on_click=_submit)
