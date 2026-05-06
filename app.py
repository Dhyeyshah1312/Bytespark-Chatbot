import streamlit as st
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

from src.rag_chain import generate_answer
from src.storage import save_chat

# Page config
st.set_page_config(
    page_title="Spark - ByteSpark AI",
    page_icon="✨",
    layout="wide"
)

# Custom styling (ByteSpark theme)
st.markdown("""
<style>
body {
    background-color: #0f172a;
}

.chat-container {
    max-width: 800px;
    margin: auto;
}

.user-msg {
    background-color: #2563eb;
    color: white;
    padding: 10px 14px;
    border-radius: 12px;
    margin: 8px 0;
    text-align: right;
}

.bot-msg {
    background-color: #1e293b;
    color: white;
    padding: 10px 14px;
    border-radius: 12px;
    margin: 8px 0;
    text-align: left;
}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div style="text-align:center; margin-top:20px;">
    <h1 style="color:#3b82f6;">✨ Spark</h1>
    <p style="color:#94a3b8;">Your AI assistant for ByteSpark 🚀</p>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Chat display
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

for msg in st.session_state.chat_history:
    if msg["role"] == "user":
        st.markdown(f'<div class="user-msg">{msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="bot-msg">{msg["content"]}</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Input box
user_input = st.chat_input("Ask Spark anything...")

if user_input:

    # Add user message
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_input
    })

    # Generate response
    answer, _ = generate_answer(
        user_input
    )

    # Add bot response
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": answer
    })

    # Save to Excel
    save_chat(user_input, answer)

    # Refresh UI
    st.rerun()