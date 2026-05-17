"""
storage.py — Dual-sheet Excel persistence for ByteSpark.
- chat_history.xlsx: Every message log.
- leads.xlsx: Master prospect list with final project summaries.
"""

import pandas as pd
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAT_FILE = os.path.join(BASE_DIR, "chat_history.xlsx")
LEAD_FILE = os.path.join(BASE_DIR, "leads.xlsx")
SUMMARY_FILE = os.path.join(BASE_DIR, "chat_summaries.xlsx")

def _safe_save_excel(df, filepath):
    """Saves to Excel with CSV fallback if file is locked."""
    try:
        df.to_excel(filepath, index=False)
        return True
    except PermissionError:
        csv_fallback = filepath.replace(".xlsx", "_FALLBACK.csv")
        print(f"[storage] {filepath} is locked. Saving to {csv_fallback}")
        df.to_csv(csv_fallback, index=False)
        return True
    except Exception as e:
        print(f"[storage] Save failed: {e}")
        return False

def save_chat(user: str, bot: str, session_key: str = "") -> bool:
    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "session_key": session_key,
        "user_msg": user,
        "bot_msg": bot
    }
    
    df = pd.read_excel(CHAT_FILE) if os.path.exists(CHAT_FILE) else pd.DataFrame()
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    return _safe_save_excel(df, CHAT_FILE)

def save_lead(
    name: str,
    email: str,
    service_intent: str = "",
    session_key: str    = "",
    purpose: str        = "",
    audience: str       = "",
    platforms: str      = "",
    timeline: str       = "",
    budget: str         = "",
    meeting_time: str   = ""
) -> bool:
    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "session_key": session_key,
        "name": name,
        "email": email,
        "service": service_intent,
        "purpose": purpose,
        "audience": audience,
        "platforms": platforms,
        "timeline": timeline,
        "budget": budget,
        "meeting_time": meeting_time,
        "project_summary": "" # Placeholder
    }

    df = pd.read_excel(LEAD_FILE) if os.path.exists(LEAD_FILE) else pd.DataFrame(columns=list(row.keys()))

    # Upsert by email + session_key
    if not df.empty and "email" in df.columns and "session_key" in df.columns:
        mask = (df["email"].astype(str).str.lower() == email.lower()) & (df["session_key"].astype(str) == str(session_key))
    else:
        mask = pd.Series([False] * len(df))

    if mask.any():
        for col, val in row.items():
            if col != "project_summary": # Don't overwrite summary if it exists
                df.loc[mask, col] = val
    else:
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)

    return _safe_save_excel(df, LEAD_FILE)

def save_lead_summary(name: str, email: str, session_key: str, summary_text: str) -> bool:
    """Updates the lead row with the final project summary."""
    if not os.path.exists(LEAD_FILE):
        return False
        
    df = pd.read_excel(LEAD_FILE)
    mask = (df["email"].astype(str).str.lower() == email.lower()) & (df["session_key"].astype(str) == str(session_key))
    
    if mask.any():
        df.loc[mask, "project_summary"] = summary_text
        return _safe_save_excel(df, LEAD_FILE)
    return False

def save_separate_summary(name: str, email: str, session_key: str, summary_text: str) -> bool:
    """Saves the exact generated summary into a brand new standalone Excel file."""
    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "session_key": session_key,
        "name": name,
        "email": email,
        "summary": summary_text
    }
    
    df = pd.read_excel(SUMMARY_FILE) if os.path.exists(SUMMARY_FILE) else pd.DataFrame()
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    return _safe_save_excel(df, SUMMARY_FILE)

def save_session(session_dict: dict) -> bool:
    """Saves session metadata to sessions.xlsx."""
    SESSION_FILE = os.path.join(BASE_DIR, "sessions.xlsx")
    df = pd.read_excel(SESSION_FILE) if os.path.exists(SESSION_FILE) else pd.DataFrame()
    df = pd.concat([df, pd.DataFrame([session_dict])], ignore_index=True)
    return _safe_save_excel(df, SESSION_FILE)

def flush_pending_writes():
    pass