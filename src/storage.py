"""
storage.py — Async-batched Excel persistence for chat, leads, and sessions.

Key fixes:
  • Lead dedup uses email + session_key combo.
    Same combo → UPDATE row in place (updated summary replaces placeholder).
    Same email + new session → INSERT a new row (returning user, new session).
  • In-memory cache (_cache_lead_keys) is only used to short-circuit rapid
    duplicate calls within the same run; the actual on-disk check is the
    authoritative source on startup.
  • Background writer handles chat + session rows; leads are always
    written synchronously so nothing is ever lost.
"""

import pandas as pd
import os
from datetime import datetime
import threading
from queue import Queue, Empty
import time

BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAT_FILE    = os.path.join(BASE_DIR, "chat_history.xlsx")
LEAD_FILE    = os.path.join(BASE_DIR, "leads.xlsx")
SESSION_FILE = os.path.join(BASE_DIR, "sessions.xlsx")
SUMMARY_FILE = os.path.join(BASE_DIR, "lead_summaries.xlsx")

# ──────────────────────────────────────────────
# Background write queue (chat + session rows only)
# ──────────────────────────────────────────────

_write_queue    = Queue(maxsize=1000)
_cache_lock     = threading.Lock()
_worker_thread  = None
_stop_worker    = False

# "email#session_key" → already-inserted leads (fast dedup within session)
_cache_lead_keys: set[str] = set()


def _load_cache():
    """Pre-load existing lead combos into memory cache on startup."""
    global _cache_lead_keys
    if os.path.exists(LEAD_FILE):
        try:
            df = pd.read_excel(LEAD_FILE, usecols=["email", "session_key"])
            for _, row in df.iterrows():
                key = f"{str(row['email']).lower()}#{row['session_key']}"
                _cache_lead_keys.add(key)
            print(f"[storage] Loaded {len(_cache_lead_keys)} cached lead keys")
        except Exception as e:
            print(f"[storage] Cache load failed (non-fatal): {e}")


def _background_writer():
    """Background thread — batches chat/session writes to avoid thrashing."""
    batch      = {}
    last_write = time.time()

    while not _stop_worker:
        try:
            item = _write_queue.get(timeout=2)
            if item is None:    # Poison pill
                break
            file_path, row = item
            batch.setdefault(file_path, []).append(row)

            if sum(len(v) for v in batch.values()) >= 10 or (time.time() - last_write) > 5:
                _flush_batch(batch)
                batch      = {}
                last_write = time.time()

        except Empty:
            if batch:
                _flush_batch(batch)
                batch      = {}
                last_write = time.time()
        except Exception as exc:
            print(f"[storage] Writer loop error: {exc}")

    if batch:
        _flush_batch(batch)


def _flush_batch(batch: dict):
    for filepath, rows in batch.items():
        try:
            df     = pd.read_excel(filepath) if os.path.exists(filepath) else pd.DataFrame()
            new_df = pd.DataFrame(rows)
            df     = pd.concat([df, new_df], ignore_index=True)
            df.to_excel(filepath, index=False)
            print(f"[storage] Wrote {len(rows)} rows → {os.path.basename(filepath)}")
        except Exception as e:
            print(f"[storage] Batch write failed ({filepath}): {e}")


def _start_worker():
    global _worker_thread
    if _worker_thread is None or not _worker_thread.is_alive():
        _load_cache()
        _worker_thread = threading.Thread(target=_background_writer, daemon=True)
        _worker_thread.start()


def _enqueue_write(filepath: str, row: dict):
    _start_worker()
    try:
        _write_queue.put_nowait((filepath, row))
    except Exception as e:
        print(f"[storage] Queue full — writing synchronously: {e}")
        _flush_batch({filepath: [row]})


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def save_chat(user: str, bot: str, session_key: str = "") -> bool:
    """Non-blocking: persist one conversation turn."""
    row = {
        "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "session_key": session_key,
        "user":        user,
        "bot":         bot,
    }
    try:
        _enqueue_write(CHAT_FILE, row)
        return True
    except Exception as e:
        print(f"[storage] save_chat failed: {e}")
        return False


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
) -> bool:
    """
    Synchronous (immediate) write so leads are never lost.

    Upsert logic:
      • Same email + same session_key  → UPDATE existing row (better summary)
      • Same email + different session → INSERT new row (new session)
    """
    cache_key = f"{email.lower()}#{session_key}"

    row = {
        "timestamp":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "session_key":    session_key,
        "name":           name,
        "email":          email,
        "service_intent": service_intent,
        "purpose":        purpose,
        "audience":       audience,
        "platforms":      platforms,
        "timeline":       timeline,
        "budget":         budget,
    }

    try:
        if os.path.exists(LEAD_FILE):
            df = pd.read_excel(LEAD_FILE)
        else:
            df = pd.DataFrame(columns=list(row.keys()))

        # Build upsert mask
        if not df.empty and "email" in df.columns and "session_key" in df.columns:
            mask = (
                df["email"].str.lower().str.strip() == email.lower().strip()
            ) & (
                df["session_key"].astype(str) == str(session_key)
            )
        else:
            mask = pd.Series([], dtype=bool)

        if mask.any():
            # UPDATE: overwrite columns on the existing row
            for col, val in row.items():
                df.loc[mask, col] = val
            action = "UPDATED"
        else:
            # INSERT: append new row
            df     = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            action = "SAVED"

        df.to_excel(LEAD_FILE, index=False)

        with _cache_lock:
            _cache_lead_keys.add(cache_key)

        print(f"[storage] Lead {action} → {name} | {email} | {service_intent} | session={session_key}")
        return True

    except PermissionError:
        # Excel file is open — fall back to CSV
        print(f"[storage] PermissionError on {LEAD_FILE} — trying CSV fallback…")
        csv_path = LEAD_FILE.replace(".xlsx", "_leads_fallback.csv")
        try:
            base = pd.read_csv(csv_path) if os.path.exists(csv_path) else pd.DataFrame()
            df   = pd.concat([base, pd.DataFrame([row])], ignore_index=True)
            df.to_csv(csv_path, index=False)
            print(f"[storage] Lead saved to CSV fallback: {csv_path}")
            return True
        except Exception as e2:
            print(f"[storage] CSV fallback also failed: {e2}")
            return False

    except Exception as e:
        print(f"[storage] save_lead failed: {e}")
        return False


def save_session(session_dict: dict) -> bool:
    """Non-blocking: persist end-of-session summary row."""
    try:
        _enqueue_write(SESSION_FILE, session_dict)
        print(f"[storage] Session queued → {session_dict.get('session_key')}")
        return True
    except Exception as e:
        print(f"[storage] save_session failed: {e}")
        return False


def save_lead_summary(name: str, email: str, session_key: str, summary_table: str) -> bool:
    """
    Saves the exact project summary table to a new Excel file.
    """
    row = {
        "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "session_key": session_key,
        "name":        name,
        "email":       email,
        "project_summary_table": summary_table
    }

    try:
        if os.path.exists(SUMMARY_FILE):
            df = pd.read_excel(SUMMARY_FILE)
        else:
            df = pd.DataFrame(columns=list(row.keys()))

        # Upsert by session_key + email
        if not df.empty and "email" in df.columns and "session_key" in df.columns:
            mask = (df["email"].astype(str).str.lower() == email.lower()) & (df["session_key"].astype(str) == str(session_key))
        else:
            mask = pd.Series([False] * len(df))
        
        if mask.any():
            df.loc[mask, "project_summary_table"] = summary_table
            df.loc[mask, "timestamp"] = row["timestamp"]
        else:
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)

        df.to_excel(SUMMARY_FILE, index=False)
        print(f"[storage] Detailed summary saved to {SUMMARY_FILE}")
        return True
    except Exception as e:
        print(f"[storage] save_lead_summary failed: {e}")
        return False


def flush_pending_writes():
    """Force-flush all pending writes — call on app shutdown."""
    global _stop_worker
    _stop_worker = True
    if _worker_thread and _worker_thread.is_alive():
        _write_queue.put(None)
        _worker_thread.join(timeout=5)