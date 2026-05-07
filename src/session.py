import uuid
import time
from datetime import datetime


class SessionManager:
    """
    Manages per-user chat sessions with inactivity timeout support.
    All state is kept in-memory; persistence is handled by storage.py.
    """

    TIMEOUT_SECONDS = 30 * 60  # 30 minutes

    def __init__(self):
        self.session_key: str = self._generate_key()
        self.start_time: datetime = datetime.now()
        self.last_activity: float = time.monotonic()
        self.conversation: list[dict] = []   # {"role": ..., "content": ...}
        self.leads: list[dict] = []          # captured lead dicts
        self.service_intent: str = "general inquiry"
        self.saved: bool = False             # prevent double-save

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def touch(self):
        """Call on every user message to reset the inactivity clock."""
        self.last_activity = time.monotonic()

    def is_expired(self) -> bool:
        """Return True when the session has been idle ≥ 30 minutes."""
        return (time.monotonic() - self.last_activity) >= self.TIMEOUT_SECONDS

    def add_turn(self, user: str, bot: str):
        """Append a conversation turn."""
        self.conversation.append({"role": "user",    "content": user})
        self.conversation.append({"role": "assistant", "content": bot})

    def register_lead(
        self, 
        name: str, 
        email: str, 
        service_intent: str, 
        purpose: str = "", 
        audience: str = "", 
        platforms: str = "", 
        timeline: str = "", 
        budget: str = ""
    ):
        """Record a captured lead (deduplicates by email)."""
        emails = {l["email"].lower() for l in self.leads}
        if email.lower() not in emails:
            self.leads.append({
                "name": name,
                "email": email,
                "service_intent": service_intent,
                "purpose": purpose,
                "audience": audience,
                "platforms": platforms,
                "timeline": timeline,
                "budget": budget,
                "captured_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
        self.service_intent = service_intent

    def generate_chat_summary(self, max_chars: int = 400) -> str:
        """
        Build a concise summary from the user's messages so far.
        Format: first user message + key follow-ups, truncated.
        """
        user_msgs = [
            turn["content"]
            for turn in self.conversation
            if turn["role"] == "user"
        ]
        if not user_msgs:
            return ""
        summary = " | ".join(user_msgs)
        if len(summary) > max_chars:
            summary = summary[: max_chars - 3].rsplit(" | ", 1)[0] + " …"
        return summary

    def summary(self) -> str:
        """One-line plain-text summary of the conversation."""
        turns = len(self.conversation) // 2
        lead_count = len(self.leads)
        return (
            f"{turns} turn(s); "
            f"{lead_count} lead(s) captured; "
            f"intent={self.service_intent}"
        )

    def to_dict(self) -> dict:
        """Serialise session metadata for storage."""
        end = datetime.now()
        duration_mins = round((end - self.start_time).total_seconds() / 60, 1)
        return {
            "session_key":          self.session_key,
            "start_time":           self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time":             end.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_minutes":     duration_mins,
            "conversation_summary": self.summary(),
            "leads_captured":       len(self.leads),
            "service_intent":       self.service_intent,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_key() -> str:
        """UUID4-based key, e.g. 'BS-3f2a1b4c'."""
        return "BS-" + uuid.uuid4().hex[:8].upper()
