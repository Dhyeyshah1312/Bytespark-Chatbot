"""
ui.py – Streamlit frontend for Spark (ByteSpark AI assistant).

Session lifecycle
─────────────────
1. A SessionManager is created once per browser tab (stored in st.session_state).
2. Every user message calls session.touch() to reset the inactivity clock.
3. A lightweight check runs on each rerun: if the session has been idle ≥ 30 min
   and hasn't been saved yet, it is persisted to sessions.xlsx automatically.
"""

import os

import streamlit as st

from src.rag_chain import generate_answer
from src.storage import save_chat, save_session
from src.memory import Memory
from src.session import SessionManager

# ──────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────

st.set_page_config(page_title="Spark – ByteSpark AI", page_icon="✦", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300&display=swap');

* { box-sizing: border-box; }

/* ── App shell ── */
[data-testid="stAppViewContainer"] {
    background: #0a0d14;
    background-image:
        radial-gradient(ellipse 80% 50% at 20% -10%, rgba(37, 99, 235, 0.15) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 110%, rgba(59, 130, 246, 0.10) 0%, transparent 55%),
        radial-gradient(ellipse 40% 30% at 50% 50%, rgba(30, 58, 138, 0.05) 0%, transparent 70%);
    min-height: 100vh;
    font-family: 'DM Sans', sans-serif;
}

[data-testid="stHeader"] { background: transparent !important; }

[data-testid="stMainBlockContainer"] {
    padding-top: 0 !important;
    max-width: 820px !important;
    margin: 0 auto;
}

/* ── Sidebar hidden ── */
[data-testid="stSidebar"] { display: none; }

/* ── Header ── */
.spark-header {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 48px 0 36px;
}

.spark-logo-ring {
    width: 64px;
    height: 64px;
    border-radius: 18px;
    background: linear-gradient(135deg, #2563eb, #3b82f6);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
    margin-bottom: 16px;
    box-shadow:
        0 0 0 1px rgba(37, 99, 235, 0.4),
        0 0 30px rgba(37, 99, 235, 0.25),
        0 8px 32px rgba(0, 0, 0, 0.4);
    animation: pulse-glow 3s ease-in-out infinite;
}

@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.4), 0 0 30px rgba(37, 99, 235, 0.25), 0 8px 32px rgba(0,0,0,0.4); }
    50%       { box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.6), 0 0 50px rgba(37, 99, 235, 0.4), 0 8px 32px rgba(0,0,0,0.4); }
}

.spark-title {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 2.2rem;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #ffffff 0%, #e2e8f0 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 6px;
    line-height: 1.1;
}

.spark-sub {
    font-family: 'DM Sans', sans-serif;
    font-weight: 300;
    font-size: 0.95rem;
    color: rgba(255, 255, 255, 0.7);
    letter-spacing: 0.04em;
    margin: 0;
}

.spark-divider {
    width: 100%;
    max-width: 820px;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(37, 99, 235, 0.3) 30%, rgba(59, 130, 246, 0.3) 70%, transparent);
    margin: 0 auto 8px;
}

/* ── Chat messages ── */
.stChatMessage {
    border-radius: 16px !important;
    margin: 6px 0 !important;
    padding: 0 !important;
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    animation: slide-up 0.3s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes slide-up {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* User bubble */
[data-testid="chat-message-container-user"] .stMarkdown,
[data-testid="chat-message-container-user"] p {
    background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%) !important;
    color: #ffffff !important;
    border-radius: 18px 18px 4px 18px !important;
    padding: 12px 18px !important;
    font-size: 0.95rem !important;
    line-height: 1.6 !important;
    box-shadow: 0 4px 20px rgba(37, 99, 235, 0.3) !important;
    max-width: 78% !important;
    margin-left: auto !important;
    display: block !important;
}

/* Assistant bubble */
[data-testid="chat-message-container-assistant"] .stMarkdown,
[data-testid="chat-message-container-assistant"] p {
    background: rgba(255, 255, 255, 0.08) !important;
    color: #f1f5f9 !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 18px 18px 18px 4px !important;
    padding: 12px 18px !important;
    font-size: 0.95rem !important;
    line-height: 1.6 !important;
    backdrop-filter: blur(12px) !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255,255,255,0.08) !important;
    max-width: 82% !important;
}

/* Avatar icons */
[data-testid="chat-message-container-user"] [data-testid="chatAvatarIcon-user"] {
    background: linear-gradient(135deg, #2563eb, #1e40af) !important;
    border: 1px solid rgba(37, 99, 235, 0.5) !important;
    box-shadow: 0 0 12px rgba(37, 99, 235, 0.3) !important;
}

[data-testid="chat-message-container-assistant"] [data-testid="chatAvatarIcon-assistant"] {
    background: linear-gradient(135deg, #3b82f6, #1e40af) !important;
    border: 1px solid rgba(59, 130, 246, 0.4) !important;
    box-shadow: 0 0 12px rgba(59, 130, 246, 0.25) !important;
}

/* ── Input area ── */
[data-testid="stBottom"] {
    background: linear-gradient(0deg, rgba(10, 13, 20, 0.98) 70%, transparent) !important;
    padding: 12px 0 20px !important;
}

[data-testid="stChatInput"] > div {
    background: rgba(255, 255, 255, 0.06) !important;
    border: 1px solid rgba(37, 99, 235, 0.3) !important;
    border-radius: 16px !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255,255,255,0.08) !important;
    backdrop-filter: blur(20px) !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}

[data-testid="stChatInput"] > div:focus-within {
    border-color: rgba(37, 99, 235, 0.7) !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12), 0 8px 32px rgba(0, 0, 0, 0.4) !important;
}

[data-testid="stChatInput"] textarea {
    color: #f1f5f9 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.95rem !important;
    background: transparent !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: rgba(148, 163, 184, 0.6) !important;
}

[data-testid="stChatInputSubmitButton"] button {
    background: linear-gradient(135deg, #2563eb, #1e40af) !important;
    border: none !important;
    border-radius: 10px !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4) !important;
    transition: all 0.2s ease !important;
}

[data-testid="stChatInputSubmitButton"] button:hover {
    background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
    box-shadow: 0 6px 18px rgba(37, 99, 235, 0.55) !important;
    transform: scale(1.05) !important;
}

/* ── Alerts ── */
.stAlert {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 12px !important;
    color: #f1f5f9 !important;
    backdrop-filter: blur(10px) !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(37, 99, 235, 0.3); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: rgba(37, 99, 235, 0.55); }

/* ── Suggestion label ── */
.suggestion-label {
    text-align: center;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.8rem;
    font-weight: 500;
    letter-spacing: 0.1em;
    color: rgba(255, 255, 255, 0.6);
    text-transform: uppercase;
    margin-top: 40px;
    margin-bottom: 14px;
}

/* ── Suggestion stacked buttons ── */
[data-testid="stButton"] button {
    background: rgba(255, 255, 255, 0.06) !important;
    border: 1px solid rgba(37, 99, 235, 0.28) !important;
    border-radius: 14px !important;
    padding: 14px 20px !important;
    font-size: 0.92rem !important;
    font-family: 'DM Sans', sans-serif !important;
    color: rgba(255, 255, 255, 0.9) !important;
    font-weight: 400 !important;
    box-shadow: none !important;
    transition: all 0.2s ease !important;
    white-space: normal !important;
    text-align: center !important;
    line-height: 1.4 !important;
    height: auto !important;
    width: 100% !important;
}

[data-testid="stButton"] button:hover {
    background: rgba(37, 99, 235, 0.14) !important;
    border-color: rgba(37, 99, 235, 0.55) !important;
    color: #ffffff !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(37, 99, 235, 0.18) !important;
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────

st.markdown("""
<div class="spark-header">
    <div class="spark-logo-ring">✦</div>
    <h1 class="spark-title">Spark</h1>
    <p class="spark-sub">AI assistant for ByteSpark &nbsp;·&nbsp; always on</p>
</div>
<div class="spark-divider"></div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Session-state initialisation (runs once per tab)
# ──────────────────────────────────────────────

if "session" not in st.session_state:
    st.session_state.session = SessionManager()

if "memory" not in st.session_state:
    st.session_state.memory = Memory()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

session: SessionManager = st.session_state.session

# ──────────────────────────────────────────────
# Debug panel — file save status (collapsed by default)
# ──────────────────────────────────────────────

with st.sidebar:
    with st.expander("Debug — Save Status", expanded=False):
        st.markdown("**File paths (project root):**")
        import src.storage as storage_mod
        for label, path in [
            ("Chat history", storage_mod.CHAT_FILE),
            ("Leads", storage_mod.LEAD_FILE),
            ("Sessions", storage_mod.SESSION_FILE),
        ]:
            exists = os.path.exists(path)
            st.markdown(
                f"{'✅' if exists else '❌'} `{label}`  \\n"
                f"`{path}`"
            )
        st.markdown("---")
        st.markdown(f"**Session key:** `{session.session_key}`")
        st.markdown(f"**Turns:** `{len(session.conversation) // 2}`")
        st.markdown(f"**Leads captured:** `{len(session.leads)}`")
        if session.leads:
            st.json(session.leads)

# ──────────────────────────────────────────────
# Inactivity timeout check
# ──────────────────────────────────────────────

if session.is_expired() and not session.saved:
    save_session(session.to_dict())
    session.saved = True
    st.warning(
        f"Session **{session.session_key}** was idle for 30 minutes and has been saved automatically.",
        icon="💾",
    )

# ──────────────────────────────────────────────
# Empty state – functional suggestion buttons
# ──────────────────────────────────────────────

SUGGESTIONS = [
    "What does ByteSpark do?",
    "What are the services provided by ByteSpark?",
]

# ──────────────────────────────────────────────
# Empty state – suggestion buttons
# ──────────────────────────────────────────────

if not st.session_state.chat_history and "active_input" not in st.session_state:
    st.markdown('<p class="suggestion-label">Try asking</p>', unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 4, 1])
    with mid:
        for i, question in enumerate(SUGGESTIONS):
            if st.button(question, key=f"suggestion_{i}", use_container_width=True):
                st.session_state.active_input = question

# ──────────────────────────────────────────────
# Chat display
# ──────────────────────────────────────────────

for msg in st.session_state.chat_history:
    st.chat_message(msg["role"]).write(msg["content"])

# ──────────────────────────────────────────────
# Typed input
# ──────────────────────────────────────────────

user_input = st.chat_input("Ask Spark anything…")
if user_input:
    st.session_state.active_input = user_input

# ──────────────────────────────────────────────
# Process any pending input (button or typed)
# Runs in the SAME script execution — no st.rerun() needed for buttons
# ──────────────────────────────────────────────

if "active_input" in st.session_state and st.session_state.active_input:
    active_input = st.session_state.active_input
    del st.session_state.active_input  # clear before processing

    session.touch()

    st.chat_message("user").write(active_input)
    st.session_state.chat_history.append({"role": "user", "content": active_input})

    # Show thinking indicator
    with st.chat_message("assistant"):
        thinking_placeholder = st.empty()
        thinking_placeholder.markdown("""
        <div style="display: flex; align-items: center; gap: 8px; padding: 12px 18px; background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 18px; backdrop-filter: blur(12px);">
            <div style="width: 8px; height: 8px; border-radius: 50%; background: linear-gradient(135deg, #2563eb, #3b82f6); animation: pulse 1.5s ease-in-out infinite;"></div>
            <span style="color: #f1f5f9; font-family: 'DM Sans', sans-serif; font-size: 0.95rem;">Spark is thinking...</span>
        </div>
        <style>
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.6; transform: scale(0.8); }
        }
        </style>
        """, unsafe_allow_html=True)

    leads_before = len(session.leads)

    answer, _ = generate_answer(
        active_input,
        db=None,
        memory=st.session_state.memory,
        chunks=None,
        session=session,
    )

    # Clear thinking indicator and show actual response
    thinking_placeholder.empty()
    st.markdown(f'<div style="color: #f1f5f9; font-family: \'DM Sans\', sans-serif; font-size: 0.95rem; line-height: 1.6;">{answer}</div>', unsafe_allow_html=True)
    st.session_state.chat_history.append({"role": "assistant", "content": answer})

    # Notify if a new lead was captured this turn
    if len(session.leads) > leads_before:
        st.toast("🎯 Lead captured!", icon="✅")

    st.session_state.memory.add(active_input, answer)
    session.add_turn(active_input, answer)
    
    # Save chat with feedback
    chat_saved = save_chat(active_input, answer, session_key=session.session_key)
    if chat_saved:
        st.toast("💾 Chat saved", icon="✅")
    else:
        st.toast("⚠️ Chat save failed — check terminal for details", icon="⚠️")
    
    st.rerun()