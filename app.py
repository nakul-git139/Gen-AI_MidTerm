import streamlit as st
import sys
from pathlib import Path

# Ensure local modules are accessible
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from rag import answer

# Page Configuration
st.set_page_config(
    page_title="HR Policy Assistant",
    page_icon="📋",
    layout="wide"
)

# Header
st.title("HR Policy Assistant")
st.subheader("Ask questions about the NovaPay Employee Handbook")
st.caption("Enter any question regarding company policies, benefits, travel allowances, or code of conduct.")

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Minimal Sidebar
with st.sidebar:
    st.header("HR Policy Assistant")
    st.caption("Official NovaPay Employee Handbook Knowledge Base")
    st.markdown("---")
    st.markdown("**Instructions:**")
    st.info("Type any policy question in the main chat box to search the handbook.")
    st.markdown("---")
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()

# Prominent Free-Text Question Input Section
with st.container():
    col1, col2 = st.columns([5, 1])
    with col1:
        text_query = st.text_input(
            "Ask any question about the handbook:",
            placeholder="Type your question here (e.g., 'What are the parental leave rules?')...",
            key="free_text_box",
            label_visibility="collapsed"
        )
    with col2:
        submit_btn = st.button("Ask HR 🔍", use_container_width=True, type="primary")

# Bottom Chat Input
bottom_chat_query = st.chat_input("Or type your question here...")

# Determine Active Question
active_question = None

if submit_btn and text_query and text_query.strip():
    active_question = text_query.strip()
elif bottom_chat_query and bottom_chat_query.strip():
    active_question = bottom_chat_query.strip()

# Display Conversation History
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        if msg["content"] == "[not found]":
            st.warning("⚠️ **[not found]** — The requested information is not available in the NovaPay Employee Handbook.")
        else:
            st.markdown(msg["content"])

        if msg.get("sources"):
            st.caption(f"📍 **Sources:** {', '.join(msg['sources'])}")

# Execute Active Question
if active_question:
    # 1. Append user question to session state & display
    st.session_state["messages"].append({
        "role": "user",
        "content": active_question,
        "sources": []
    })
    with st.chat_message("user"):
        st.markdown(active_question)

    # 2. Query RAG backend with loading indicator
    with st.chat_message("assistant"):
        with st.spinner("Searching employee handbook and verifying evidence..."):
            try:
                res = answer(active_question)
                ans_text = res.get("answer", "[not found]")
                sources = res.get("sources", [])

                if ans_text == "[not found]":
                    st.warning("⚠️ **[not found]** — The requested information is not available in the NovaPay Employee Handbook.")
                else:
                    st.markdown(ans_text)

                if sources:
                    st.caption(f"📍 **Sources:** {', '.join(sources)}")

                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": ans_text,
                    "sources": sources
                })
            except Exception as e:
                err_msg = f"An error occurred while answering your question: {e}"
                st.error(err_msg)
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": err_msg,
                    "sources": []
                })
