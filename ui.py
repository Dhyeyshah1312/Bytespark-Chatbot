import streamlit as st

from src.loader import load_data
from src.chunker import split_docs
from src.embeddings import get_embeddings
from src.vectorstore import create_vectorstore
from src.rag_chain import generate_answer
from src.memory import Memory

st.set_page_config(page_title="Spark — ByteSpark AI", layout="wide")

# 🎨 MODERN BYTESPARK UI
st.markdown("""
<style>
body {
    background: linear-gradient(135deg, #0b0f1a, #121a3a);
    font-family: 'Segoe UI', sans-serif;
    color: white;
}

[data-testid="stHeader"], [data-testid="stSidebar"] { display: none; }

/* NAVBAR */
.navbar {
    display: flex;
    justify-content: space-between;
    padding: 16px 60px;
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(10px);
    border-radius: 12px;
    margin: 20px;
}

.logo {
    font-size: 20px;
    font-weight: bold;
    background: linear-gradient(90deg, #5B8CFF, #9B5CFF);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.nav-links {
    color: #bbb;
    font-size: 14px;
}

/* HERO */
.hero {
    text-align: center;
    margin-top: 40px;
}

.hero-title {
    font-size: 48px;
    font-weight: 700;
    background: linear-gradient(90deg, #5B8CFF, #9B5CFF);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero-sub {
    color: #aaa;
    margin-top: 10px;
}

/* CHAT BOX */
.chat-container {
    max-width: 900px;
    margin: 40px auto;
    padding: 20px;
    border-radius: 20px;
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(15px);
}

/* USER */
.user-msg {
    text-align: right;
    margin: 10px 0;
}

.user-msg span {
    background: linear-gradient(135deg, #5B8CFF, #2F5BFF);
    padding: 12px 16px;
    border-radius: 16px;
    display: inline-block;
}

/* BOT */
.bot-msg {
    margin: 10px 0;
}

.bot-msg span {
    background: rgba(255,255,255,0.08);
    padding: 12px 16px;
    border-radius: 16px;
    display: inline-block;
    border: 1px solid rgba(255,255,255,0.1);
}

/* INPUT */
[data-testid="stChatInput"] {
    border-radius: 30px !important;
    border: none !important;
    background: rgba(255,255,255,0.08) !important;
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# 🔹 NAVBAR
st.markdown("""
<div class="navbar">
    <div class="logo">ByteSpark</div>
    <div class="nav-links">Home &nbsp;&nbsp; About &nbsp;&nbsp; Services &nbsp;&nbsp; Contact</div>
</div>
""", unsafe_allow_html=True)

# 🔹 HERO
st.markdown("""
<div class="hero">
    <div class="hero-title">Spark Your Digital Dreams</div>
    <div class="hero-sub">Your AI assistant for building powerful digital solutions 🚀</div>
</div>
""", unsafe_allow_html=True)

# 🔹 LOAD SYSTEM
@st.cache_resource
def load_system():
    docs1 = load_data("data/bytespark_companyinfo.pdf")
    docs2 = load_data("data/services_pricing.pdf")

    docs = docs1 + docs2
    chunks = split_docs(docs)
    embeddings = get_embeddings()
    db = create_vectorstore(chunks, embeddings)

    return db, chunks

db, chunks = load_system()

# 🔹 STATE
if "memory" not in st.session_state:
    st.session_state.memory = Memory()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "Hey! 👋 I’m Spark. What are you looking to build today?"}
    ]

# 🔹 CHAT
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

for chat in st.session_state.chat_history:
    if chat["role"] == "user":
        st.markdown(f'<div class="user-msg"><span>{chat["content"]}</span></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="bot-msg"><span>{chat["content"]}</span></div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# 🔹 INPUT
user_input = st.chat_input("Ask Spark...")

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    answer, _ = generate_answer(
        user_input,
        db,
        st.session_state.memory,
        chunks
    )

    st.session_state.chat_history.append({"role": "assistant", "content": answer})
    st.session_state.memory.add(user_input, answer)

    st.rerun()