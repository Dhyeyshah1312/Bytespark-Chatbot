"""ui.py – ByteSpark Spark AI Chatbot — Brand-matched UI"""

import os
import streamlit as st
from src.rag_chain import generate_answer
from src.storage import save_chat, save_session
from src.memory import Memory
from src.session import SessionManager

st.set_page_config(
    page_title="Spark – ByteSpark AI",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Montserrat:wght@600;700;800&display=swap');

:root {
    --primary:   #1E60FF;
    --secondary: #00D4FF;
    --tertiary:  #7000FF;
    --neutral:   #F8FAFC;
    --text:      #1E293B;
    --subtext:   #64748B;
    --border:    #E2E8F0;
}

*, *::before, *::after { box-sizing: border-box; }

html, body,
[data-testid="stAppViewContainer"],
section[data-testid="stMain"] {
    background: #F0F4FF !important;
    font-family: 'Inter', sans-serif !important;
}

[data-testid="stHeader"]     { display: none !important; }
[data-testid="stSidebar"]    { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
#MainMenu, footer            { visibility: hidden; }

/* ── Chat frame — separated from the website ── */
.block-container {
    padding: 0 0 90px 0 !important;
    max-width: 740px !important;
    background: #FFFFFF !important;
    border-radius: 20px !important;
    border: 1px solid var(--border) !important;
    box-shadow: 0 8px 40px rgba(30,96,255,0.10), 0 2px 8px rgba(0,0,0,0.06) !important;
    overflow: visible !important;
    margin-top: 12px !important;
    margin-bottom: 12px !important;
}

/* ── Gradient accent line under navbar ── */
.sp-gradient-bar {
    height: 3px;
    background: linear-gradient(90deg, var(--primary) 0%, var(--secondary) 50%, var(--tertiary) 100%);
}

/* ── Message entrance animation ── */
@keyframes msgSlideIn {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
}
[data-testid="stChatMessage"] {
    animation: msgSlideIn 0.28s ease both;
}

/* ── Status dot pulse ── */
@keyframes statusPulse {
    0%,100% { box-shadow: 0 0 0 0 rgba(16,185,129,0.5); }
    60%     { box-shadow: 0 0 0 5px rgba(16,185,129,0); }
}
.sp-status::before { animation: statusPulse 2.2s infinite; }

/* ── Navbar ── */
.sp-nav {
    background: rgba(255,255,255,0.96);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border);
    padding: 10px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 999;
}
.sp-nav-left { display: flex; align-items: center; gap: 10px; }
.sp-avatar {
    width: 36px; height: 36px;
    background: var(--primary);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    color: white; font-size: 15px; font-weight: 700;
    box-shadow: 0 2px 8px rgba(30,96,255,0.28);
}
.sp-name {
    font-family: 'Montserrat', sans-serif;
    font-weight: 700; font-size: 1rem; color: var(--text);
}
.sp-status {
    font-size: 0.68rem; color: #10b981; font-weight: 600;
    display: flex; align-items: center; gap: 4px;
}
.sp-status::before {
    content: '';
    display: inline-block;
    width: 6px; height: 6px;
    background: #10b981; border-radius: 50%;
}
.sp-nav-right { display: flex; gap: 14px; color: var(--subtext); font-size: 1.1rem; }

/* ── Welcome ── */
.sp-welcome {
    text-align: center;
    padding: 52px 20px 28px;
}
.sp-welcome h2 {
    font-family: 'Montserrat', sans-serif;
    font-size: 1.75rem; font-weight: 800; color: var(--text); margin-bottom: 10px;
}
.sp-welcome p {
    color: var(--subtext); font-size: 0.93rem;
    max-width: 360px; margin: 0 auto; line-height: 1.65;
}
.sp-try-label {
    text-align: center; font-size: 0.68rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.12em;
    color: #94A3B8; margin: 20px 0 10px;
}

/* ── Suggestion Buttons ── */
[data-testid="stButton"] > button {
    background: #FFFFFF !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    color: var(--text) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    padding: 13px 16px !important;
    text-align: left !important;
    width: 100% !important;
    height: auto !important;
    white-space: normal !important;
    line-height: 1.4 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
    transition: all 0.18s ease !important;
}
[data-testid="stButton"] > button:hover {
    border-color: var(--primary) !important;
    color: var(--primary) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 14px rgba(30,96,255,0.1) !important;
}

/* ── Date Pill ── */
.sp-date { text-align: center; margin: 18px 0 10px; }
.sp-date span {
    background: #F1F5F9; color: var(--subtext);
    font-size: 0.7rem; font-weight: 500;
    padding: 4px 14px; border-radius: 100px;
}

/* ── Chat Messages ── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 3px 0 !important;
}

/* ── Custom Avatars ── */
[data-testid="chatAvatarIcon-user"] {
    background: var(--primary) !important;
    border-radius: 50% !important;
    width: 32px !important; height: 32px !important;
    min-width: 32px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 14px !important;
    color: white !important;
    box-shadow: 0 2px 8px rgba(30,96,255,0.25) !important;
    overflow: hidden !important;
}
[data-testid="chatAvatarIcon-user"] > img { display: none !important; }
[data-testid="chatAvatarIcon-user"]::after {
    content: '👤';
    font-size: 15px;
}
[data-testid="chatAvatarIcon-assistant"] {
    background: linear-gradient(135deg, var(--primary), var(--tertiary)) !important;
    border-radius: 50% !important;
    width: 32px !important; height: 32px !important;
    min-width: 32px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 14px !important;
    color: white !important;
    box-shadow: 0 2px 8px rgba(112,0,255,0.2) !important;
    overflow: hidden !important;
}
[data-testid="chatAvatarIcon-assistant"] > img { display: none !important; }
[data-testid="chatAvatarIcon-assistant"]::after {
    content: '⚡';
    font-size: 15px;
}

/* User bubble – right aligned, Primary Blue */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    display: flex !important;
    justify-content: flex-end !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) .stMarkdown p {
    background: var(--primary) !important;
    color: #FFFFFF !important;
    padding: 12px 18px !important;
    border-radius: 18px 18px 4px 18px !important;
    font-size: 0.93rem !important;
    line-height: 1.6 !important;
    max-width: 78% !important;
    margin-left: auto !important;
    box-shadow: 0 4px 14px rgba(30,96,255,0.18) !important;
    display: inline-block !important;
    word-break: break-word !important;
}

/* Assistant bubble – left aligned, Neutral */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    display: flex !important;
    justify-content: flex-start !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stMarkdown {
    background: var(--neutral) !important;
    color: var(--text) !important;
    padding: 13px 18px !important;
    border-radius: 18px 18px 18px 4px !important;
    font-size: 0.93rem !important;
    line-height: 1.65 !important;
    max-width: 82% !important;
    border: 1px solid var(--border) !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
    word-break: break-word !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stMarkdown * {
    color: var(--text) !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) table {
    border-collapse: collapse; width: 100%;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) th {
    background: #EFF6FF !important; color: var(--primary) !important;
    padding: 8px 12px !important; font-size: 0.82rem !important;
    text-align: left !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) td {
    border-top: 1px solid var(--border) !important;
    padding: 8px 12px !important; font-size: 0.88rem !important;
}

/* ── Input Dock — Purple/Pink gradient background ── */
[data-testid="stBottom"] {
    background: linear-gradient(135deg, #7000FF 0%, #C026D3 60%, #1E60FF 100%) !important;
    border-top: none !important;
    padding: 14px 16px 18px !important;
    border-radius: 0 0 20px 20px !important;
}
[data-testid="stBottom"] > div,
[data-testid="stBottom"] > div > div {
    background: transparent !important;
}
[data-testid="stChatInput"] > div {
    background: rgba(255,255,255,0.18) !important;
    border: 1px solid rgba(255,255,255,0.4) !important;
    border-radius: 28px !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.15) !important;
    backdrop-filter: blur(8px) !important;
}
[data-testid="stChatInput"] > div:focus-within {
    border-color: rgba(255,255,255,0.8) !important;
    box-shadow: 0 0 0 3px rgba(255,255,255,0.15) !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: #FFFFFF !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.93rem !important;
    border: none !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: rgba(255,255,255,0.65) !important; }

[data-testid="stChatInputSubmitButton"] > button {
    background: #FFFFFF !important;
    border: none !important;
    border-radius: 50% !important;
    width: 40px !important; height: 40px !important;
    color: var(--tertiary) !important;
    font-size: 1.1rem !important;
    box-shadow: 0 4px 14px rgba(0,0,0,0.2) !important;
    transition: transform 0.15s, box-shadow 0.15s !important;
}
[data-testid="stChatInputSubmitButton"] > button:hover {
    transform: scale(1.1) !important;
    box-shadow: 0 6px 20px rgba(0,0,0,0.28) !important;
}

/* ── Footer hint (inside dock) ── */
.sp-footer {
    text-align: center;
    font-size: 0.62rem;
    color: rgba(255,255,255,0.55);
    padding: 6px 0 0;
    letter-spacing: 0.02em;
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Navbar
# ──────────────────────────────────────────────
st.markdown("""
<div class="sp-nav">
  <div class="sp-nav-left">
    <div class="sp-avatar">⚡</div>
    <div>
      <div class="sp-name">Spark &nbsp;<span style="font-size:0.65rem;font-weight:500;color:#94A3B8;font-family:Inter,sans-serif;">by ByteSpark</span></div>
      <div class="sp-status">Online</div>
    </div>
  </div>
  <div class="sp-nav-right">
    <span title="History">🕒</span>
    <span title="Settings">⚙️</span>
  </div>
</div>
<div class="sp-gradient-bar"></div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Session State
# ──────────────────────────────────────────────
if "session" not in st.session_state:
    st.session_state.session = SessionManager()
if "memory" not in st.session_state:
    st.session_state.memory = Memory()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

session: SessionManager = st.session_state.session

if session.is_expired() and not session.saved:
    save_session(session.to_dict())
    session.saved = True

# ──────────────────────────────────────────────
# Welcome Screen
# ──────────────────────────────────────────────
SUGGESTIONS = [
    "What does ByteSpark do?",
    "What services do you provide?",
]

if not st.session_state.chat_history and "active_input" not in st.session_state:
    st.markdown("""
    <div class="sp-welcome">
      <h2>How can Spark help you today?</h2>
      <p>Your AI guide to ByteSpark — ask about our services, capabilities, or how we can help grow your business.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="sp-try-label">Try asking</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button(SUGGESTIONS[0], key="s0", use_container_width=True):
            st.session_state.active_input = SUGGESTIONS[0]
    with col2:
        if st.button(SUGGESTIONS[1], key="s1", use_container_width=True):
            st.session_state.active_input = SUGGESTIONS[1]

# ── Chat History ──
if st.session_state.chat_history:
    st.markdown('<div class="sp-date"><span>Today</span></div>', unsafe_allow_html=True)

for msg in st.session_state.chat_history:
    st.chat_message(msg["role"]).write(msg["content"])

# ── Input + Processing ──
user_input = st.chat_input("Message Spark...")
if user_input:
    st.session_state.active_input = user_input

if "active_input" in st.session_state and st.session_state.active_input:
    active_input = st.session_state.active_input
    del st.session_state.active_input

    session.touch()
    st.chat_message("user").write(active_input)
    st.session_state.chat_history.append({"role": "user", "content": active_input})

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            answer, _ = generate_answer(
                active_input,
                db=None,
                memory=st.session_state.memory,
                chunks=None,
                session=session,
            )
        st.write(answer)
        st.session_state.chat_history.append({"role": "assistant", "content": answer})

    st.session_state.memory.add(active_input, answer)
    session.add_turn(active_input, answer)
    save_chat(active_input, answer, session_key=session.session_key)
    st.rerun()

st.markdown('<div class="sp-footer">Spark can make mistakes. Consider checking important information.</div>', unsafe_allow_html=True)