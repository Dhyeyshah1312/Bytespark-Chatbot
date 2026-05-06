
"""
rag_chain.py – Core answer generation with:
  • Immediate lead capture (name + email detected anywhere in conversation)
  • Correct service-intent priority order
  • Full-name extraction
  • Complete email regex (no truncation)
  • Session-key threading through storage calls
  • Async summary generation (non-blocking)
  • Groq integration for fast inference
"""

import re
import os
import threading
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from langchain_openai import ChatOpenAI
from src.prompt import get_prompt
from src.sales import SalesAgent
from src.meeting import schedule_meeting
from src.retriever import hybrid_retrieval
from src.storage import save_chat, save_lead, save_session

try:
    from langchain_groq import ChatGroq
    GROQ_AVAILABLE = True
except ImportError:
    ChatGroq = None
    GROQ_AVAILABLE = False

# ──────────────────────────────────────────────
# LLM (Using Groq for free, ultra-fast inference)
# ──────────────────────────────────────────────

groq_api_key = os.getenv("GROQ_API_KEY")
llm_provider = os.getenv("LLM_PROVIDER", "groq")  # Default to groq

if GROQ_AVAILABLE and groq_api_key and llm_provider == "groq":
    llm = ChatGroq(
        model="mixtral-8x7b-32768",
        temperature=0.4,
        api_key=groq_api_key,
        max_retries=2,
        request_timeout=20,
    )
    print("[rag_chain] Using Groq (fast inference)")
else:
    print("[rag_chain] WARNING: Groq not available or API key missing. Falling back to OpenAI")
    llm = ChatOpenAI(
        model="openai/gpt-3.5-turbo",
        temperature=0.4,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_api_base="https://openrouter.ai/api/v1",
        max_retries=2,
        request_timeout=10,
    )

# One SalesAgent per process (stateful); ui.py resets it per Streamlit session
sales_agent = SalesAgent()


# ──────────────────────────────────────────────
# Background summary generation (non-blocking)
# ──────────────────────────────────────────────

def _generate_sales_summary_async(name: str, email: str, service_intent: str, session_key: str, llm_obj, conversation: list[dict]):
    """
    Generate sales summary in background thread.
    This is called async so it doesn't block the user response.
    """
    try:
        user_msgs = [turn["content"] for turn in conversation if turn["role"] == "user"]
        if not user_msgs:
            summary = f"Interested in {service_intent}"
        else:
            meaningful_msgs = [
                m for m in user_msgs
                if len(m) > 3 and m.lower() not in {"yes", "no", "yup", "sure", "ok", "okay", "everything"}
            ]
            if not meaningful_msgs:
                meaningful_msgs = user_msgs
            
            user_thread = "\n".join(f"- {m}" for m in meaningful_msgs[-6:])
            
            prompt = (
                "You are a sales assistant summarizing a prospect conversation for a CRM entry.\n\n"
                f"Service interest: {service_intent}\n\n"
                "Prospect messages (most recent last):\n"
                f"{user_thread}\n\n"
                "Write 2-3 concise sentences summarizing:\n"
                "1. What the prospect wants (project, goals, pain points)\n"
                "2. Specific details mentioned (team/company name, scope, timeline, budget hints)\n"
                "3. Their engagement level and next steps agreed\n\n"
                "Summary (be specific, no fluff):"
            )
            
            try:
                response = llm_obj.invoke(prompt).content.strip()
                if response.startswith("Summary:"):
                    response = response[8:].strip()
                summary = response[:350]
            except Exception as e:
                print(f"[rag_chain] Summary LLM error: {e}")
                first_msg = meaningful_msgs[0][:60] if meaningful_msgs else ""
                key_details = " | ".join(m for m in meaningful_msgs[-3:] if len(m) > 10)
                summary = f"Initial: {first_msg}... Recent: {key_details[:200]}"
        
        # Re-save lead with summary
        save_lead(name, email, service_intent, session_key, summary)
    except Exception as e:
        print(f"[rag_chain] Background summary failed: {e}")


def _start_summary_thread(name: str, email: str, service_intent: str, session_key: str, conversation: list[dict]):
    """Start background thread for summary generation."""
    thread = threading.Thread(
        target=_generate_sales_summary_async,
        args=(name, email, service_intent, session_key, llm, conversation),
        daemon=True
    )
    thread.start()
    return thread


# ──────────────────────────────────────────────
# Guards
# ──────────────────────────────────────────────

_SENSITIVE = [
    "api key", "password", "credentials", "internal",
    "database", "system prompt", "hack", "bypass", "admin",
]
_ABUSIVE = ["fuck", "shit", "idiot", "stupid"]


def is_sensitive(q: str) -> bool:
    ql = q.lower()
    return any(k in ql for k in _SENSITIVE)


def is_abusive(q: str) -> bool:
    ql = q.lower()
    return any(a in ql for a in _ABUSIVE)


# ──────────────────────────────────────────────
# Service-intent detection  (priority order matters)
# ──────────────────────────────────────────────

_SERVICE_RULES = [
    ("website",           ["web development", "website development", "web dev", "web site", "online platform"]),
    ("digital marketing", ["digital marketing", "marketing campaign", "social media marketing"]),
    ("app",               ["app development", "mobile app", "application development", "mobile application"]),
    ("seo",               ["seo optimization", "search engine optimization", "seo services"]),
    ("cloud",             ["cloud hosting", "cloud infrastructure", "cloud services", "aws", "azure"]),
    ("ai/ml",             ["machine learning", "artificial intelligence", "ai solutions", "ml models", "data science"]),
    ("ui/ux",             ["ui design", "ux design", "user interface", "user experience"]),
    # Broader terms as fallbacks
    ("website",           ["website", "web", "site", "online", "domain", "landing page"]),
    ("digital marketing", ["marketing", "digital", "social media", "ads", "campaign"]),
    ("app",               ["app", "application", "mobile", "ios", "android"]),
    ("cloud",             ["backup", "hosting", "server", "scalable", "storage", "infrastructure"]),
    ("ai/ml",             ["dashboard", "prediction", "predict", "analytics", "data analysis", "automation", "ai", "ml"]),
]


def extract_service_intent(text: str) -> str:
    """
    Return the first matching service label, using _SERVICE_RULES priority order.
    Falls back to 'general inquiry'.
    """
    tl = text.lower()
    for label, keywords in _SERVICE_RULES:
        if any(kw in tl for kw in keywords):
            return label
    return "general inquiry"


# ──────────────────────────────────────────────
# Name / email extraction
# ──────────────────────────────────────────────

# Full-name patterns (first + last) tried before single-name fallbacks
# NOTE: 'i am' / 'i'm' are intentionally EXCLUDED — they cause massive false positives
_NAME_PATTERNS = [
    r"(?:name\s+is|my\s+name\s+is|this\s+is|call\s+me)\s+([A-Za-z]+(?:\s+[A-Za-z]+)+)",
    r"([A-Za-z]+(?:\s+[A-Za-z]+)+)\s+here\b",
    # Name followed by comma/email  e.g. "Liam Lawson, liam@vcarb.com"
    r"(?:^|\n|\s)([A-Za-z]+(?:\s+[A-Za-z]+){0,3})(?:,|\s)\s*[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
    # Single-name fallbacks
    r"(?:name\s+is|my\s+name\s+is|this\s+is|call\s+me)\s+([A-Za-z]+)",
    r"([A-Za-z]+)\s+here\b",
]

# RFC-5321-ish – handles subdomains, plus-addressing, dots; no truncation
_EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
    re.IGNORECASE,
)


def extract_name(text: str) -> str | None:
    for pattern in _NAME_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip().title()
            # Reject obvious non-names (stop-words, single chars)
            if len(candidate) >= 2 and candidate.lower() not in {
                "the", "a", "an", "is", "are", "was", "been",
                "going", "looking", "interested", "thinking",
                "everything", "sure", "thanks", "okay", "yes", "no",
            }:
                return candidate

    # Fallback: if there's an email but no explicit name prefix,
    # look for 1-3 words (any case) before the email
    if _EMAIL_RE.search(text):
        fallback = re.search(
            r"(?:^|\n|\s)([A-Za-z]+(?:\s+[A-Za-z]+){0,2})(?:,|\s)\s*[A-Za-z0-9._%+\-]+@",
            text,
            re.IGNORECASE,
        )
        if fallback:
            candidate = fallback.group(1).strip().title()
            if len(candidate) >= 2 and candidate.lower() not in {
                "the", "a", "an", "is", "are", "was", "been",
                "going", "looking", "interested", "thinking",
                "everything", "sure", "thanks", "okay", "yes", "no",
            }:
                return candidate
    return None


def extract_email(text: str) -> str | None:
    m = _EMAIL_RE.search(text)
    return m.group(0).strip() if m else None

# ──────────────────────────────────────────────
# Sales summary generator
# ──────────────────────────────────────────────

def _generate_sales_summary(llm, conversation: list[dict], service_intent: str) -> str:
    """
    Generate sales summary in structured format.
    Format: Interest: X; Need: Y; Budget: Z; Timeline: W; Next: V
    """
    user_msgs = [turn["content"] for turn in conversation if turn["role"] == "user"]
    if not user_msgs:
        return ""

    # Extract key information
    interest = service_intent
    need = ""
    budget = "not specified"
    timeline = "not specified"
    next_step = "schedule discovery call"
    
    # Analyze messages for details
    full_text = " ".join(user_msgs).lower()
    
    # Extract what they need
    if "website" in full_text or "web" in full_text or "web dev" in full_text:
        need = "web development"
    elif "app" in full_text or "mobile" in full_text:
        need = "mobile app development"
    elif "marketing" in full_text or "digital marketing" in full_text:
        need = "digital marketing services"
    elif "cloud" in full_text or "cloud services" in full_text:
        need = "cloud services"
    elif "ai" in full_text or "ml" in full_text:
        need = "AI/ML solutions"
    else:
        need = f"{service_intent} services"
    
    # Extract budget
    budget_patterns = [
        r"(\d+)k?\s*budget",
        r"budget\s*(is|:)?\s*(\$?\d+k?)",
        r"(\$?\d+k?)\s*budget",
        r"(\$\d+(?:,\d{3})*(?:\.\d{2})?)\s*budget",
        r"budget\s*(of)?\s*(\$?\d+(?:,\d{3})*(?:\.\d{2})?)",
        r"(\d+)\s*(?:k|thousand)?\s*(?:dollars?|usd)?\s*budget",
        r"(\d+)k?\s*(?:and)?\s*(\d+)k?\s*budget",  # for "10k and 5k budget"
        r"(\d+)k",  # standalone like "10k"
        r"budget\s*(is)?\s*(\d+)k"
    ]
    
    for pattern in budget_patterns:
        m = re.search(pattern, full_text, re.IGNORECASE)
        if m:
            # Find the last group that has digits
            for i in reversed(range(len(m.groups()) + 1)):
                if m.group(i) and re.search(r'\d', m.group(i)):
                    budget = m.group(i)
                    if 'k' in budget.lower() and not budget.startswith('$'):
                        budget = f"${budget}"
                    break
            else:
                budget = m.group(1) if m.group(1) else "not specified"
            break
    
    # Extract timeline
    timeline_patterns = [
        r"(\d+)\s*(weeks?|days?|months?)",
        r"timeline\s*(is|:)?\s*(\d+\s*(?:weeks?|days?|months?))",
        r"(\d+)\s*weeks?",
        r"(\d+)\s*days?",
        r"(\d+)\s*months?"
    ]
    
    for pattern in timeline_patterns:
        m = re.search(pattern, full_text, re.IGNORECASE)
        if m:
            timeline = m.group(1) + " " + m.group(2) if m.group(2) else m.group(1) + " weeks"
            break
    
    return f"Interest: {interest}; Need: {need}; Budget: {budget}; Timeline: {timeline}; Next: {next_step}"


# ──────────────────────────────────────────────
# Main answer generator
# ──────────────────────────────────────────────


def generate_answer(
    query: str,
    db=None,
    memory=None,
    chunks=None,
    session=None,          # SessionManager instance (optional)
):
    q = query.strip()
    q_lower = q.lower()
    session_key = session.session_key if session else ""

    # ── Guards ────────────────────────────────
    if is_sensitive(q):
        return "I can't help with sensitive or confidential information.", []
    if is_abusive(q):
        return "I'm here to help 🙂 Let me know what you need.", []

    # ── Build full conversation text for extraction ───────────────────
    history_text = ""
    if memory:
        history_text = memory.get_context()
    # Also include the current message so same-turn captures work
    full_text = history_text + f"\nUser: {q}"

    # ── Immediate lead capture ────────────────────────────────────────
    # Prefer the sales-agent's directly-collected info (user answered
    # "May I know your name?") over regex-mining the whole history,
    # which is prone to false positives (e.g. "i am in complete dark").
    name_found  = sales_agent.lead.get("name")  or extract_name(q)
    email_found = sales_agent.lead.get("email") or extract_email(q)

    if name_found and email_found:
        current_name  = sales_agent.lead.get("name", "")
        current_email = sales_agent.lead.get("email", "")

        # Only save when we have a *new* lead (avoids duplicate Excel rows)
        # Check if this is a new lead or if we just completed the info
        is_new_lead = (current_name.lower()  != name_found.lower() or
                       current_email.lower() != email_found.lower())
        just_completed = (name_found and email_found and 
                         not current_name and not current_email)
        
        if is_new_lead or just_completed:

            intent = extract_service_intent(q)  # Use only current message for service intent
            
            # Generate summary immediately
            if session:
                try:
                    chat_summary = _generate_sales_summary(llm, session.conversation, intent)
                except NameError:
                    # Fallback if function not defined due to module caching
                    user_msgs = [turn["content"] for turn in session.conversation if turn["role"] == "user"]
                    if user_msgs:
                        chat_summary = f"Interest: {intent}. Recent: {user_msgs[-1][:100]}"
                    else:
                        chat_summary = ""
            else:
                chat_summary = ""
            save_lead(name_found, email_found, intent, session_key, chat_summary)
            
            # Propagate to session object
            if session:
                session.register_lead(name_found, email_found, intent, chat_summary)
                # Persist session summary immediately so it doesn't get lost
                if not session.saved:
                    save_session(session.to_dict())
                    session.saved = True

            # Sync agent state ONLY if it was empty (don't overwrite direct answers)
            if not sales_agent.lead.get("name"):
                sales_agent.lead["name"] = name_found
            if not sales_agent.lead.get("email"):
                sales_agent.lead["email"] = email_found

            print(f"[rag_chain] LEAD CAPTURED: {name_found} | {email_found} | {intent}")

    # ── Sales flow ────────────────────────────────────────────────────
    sales_response = sales_agent.handle(q)

    if sales_agent.stage == "schedule_meeting":
        name  = sales_agent.lead.get("name")
        email = sales_agent.lead.get("email")

        if name and email:
            intent = extract_service_intent(q)  # Use only current message for service intent
            # Lead already saved above; avoid duplicate unless agent advanced
            if not sales_agent.lead.get("_meeting_saved"):
                # Generate summary immediately
                if session:
                    try:
                        chat_summary = _generate_sales_summary(llm, session.conversation, intent)
                    except NameError:
                        # Fallback if function not defined due to module caching
                        user_msgs = [turn["content"] for turn in session.conversation if turn["role"] == "user"]
                        if user_msgs:
                            chat_summary = f"Interest: {intent}. Recent: {user_msgs[-1][:100]}"
                        else:
                            chat_summary = ""
                else:
                    chat_summary = ""
                save_lead(name, email, intent, session_key, chat_summary)
                if session:
                    session.register_lead(name, email, intent, chat_summary)
                sales_agent.lead["_meeting_saved"] = True

        result = schedule_meeting(name, email)
        sales_agent.stage = "done"
        return result, []

    if sales_response:
        return sales_response, []

    # ── Meeting intent shortcut ───────────────────────────────────────
    meeting_triggers = ["call", "meeting", "discuss", "connect", "schedule"]
    if any(t in q_lower for t in meeting_triggers):
        if sales_agent.stage == "idle":
            if name_found and email_found:
                # We already have lead info – book directly
                result = schedule_meeting(name_found, email_found)
                return result, []
            # Otherwise kick off the collection flow
            return sales_agent.start_flow(None), []

    # ── RAG retrieval ─────────────────────────────────────────────────
    context = ""
    docs    = []
    try:
        if db is not None:
            docs    = hybrid_retrieval(q, db, chunks)
            context = "\n\n".join(d.page_content for d in docs)
    except Exception as exc:
        print(f"[rag_chain] Retrieval error: {exc}")

    history = memory.get_context() if memory else ""

    # Inject a dynamic closing note once we hit 5+ turns
    closing_note = ""
    if session and len(session.conversation) >= 8:  # 4 user + 4 bot turns = 4 back-and-forth exchanges
        closing_note = (
            "URGENT: This conversation has already gone back-and-forth several times. "
            "You MUST NOT ask another exploratory question. "
            "Instead, warmly summarize what you've learned, express excitement about the project, "
            "and propose a quick call or meeting to nail down the details. "
            "Ask for the user's name and email so the team can reach out."
        )

    prompt  = get_prompt(context, history, q, closing_note)

    try:
        response = llm.invoke(prompt).content.strip()
    except Exception as exc:
        error_msg = str(exc)
        print(f"[rag_chain] LLM error: {error_msg}")
        import traceback
        traceback.print_exc()
        
        # Provide helpful error message
        if "401" in error_msg or "authentication" in error_msg.lower():
            return "⚠️ API authentication failed. Please check your GROQ_API_KEY.", []
        elif "rate_limit" in error_msg.lower() or "429" in error_msg:
            return "⚠️ Rate limited. Please try again in a moment.", []
        elif "timeout" in error_msg.lower():
            return "⚠️ Request timed out. The API is slow. Please try again.", []
        else:
            return f"⚠️ Error: {error_msg[:100]}", []

    return response, docs
