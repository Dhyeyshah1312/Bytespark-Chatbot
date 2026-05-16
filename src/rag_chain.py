
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
load_dotenv(override=True)

from langchain_openai import ChatOpenAI
from src.prompt import get_prompt
from src.sales import SalesAgent
from src.meeting import schedule_meeting
from src.retriever import hybrid_retrieval
from src.storage import save_chat, save_lead, save_session, save_lead_summary

# try:
#     from langchain_groq import ChatGroq
#     GROQ_AVAILABLE = True
# except ImportError:
#     ChatGroq = None
#     GROQ_AVAILABLE = False

# ──────────────────────────────────────────────
# LLM (Using Groq for free, ultra-fast inference)
# ──────────────────────────────────────────────

groq_api_key = os.getenv("GROQ_API_KEY")
llm_provider = os.getenv("LLM_PROVIDER", "groq")  # Default to groq

# if GROQ_AVAILABLE and groq_api_key and llm_provider == "groq":
#     llm = ChatGroq(
#         model="mixtral-8x7b-32768",
#         temperature=0.4,
#         api_key=groq_api_key,
#         max_retries=2,
#         request_timeout=20,
#     )
#     print("[rag_chain] Using Groq (fast inference)")
# else:
#     print("[rag_chain] WARNING: Groq not available or API key missing. Falling back to OpenAI")

llm = ChatOpenAI(
    model="meta-llama/llama-3.1-70b-instruct:free",
    temperature=0.4,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_base="https://openrouter.ai/api/v1",
    max_tokens=1000,
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

def _generate_sales_summary(service_intent: str) -> str:
    """
    Builds the exact Markdown summary table as shown in the chat.
    """
    lead = sales_agent.lead
    summary = "### 📋 Project Summary Table\n\n"
    summary += "| Detail | Information |\n"
    summary += "| :--- | :--- |\n"
    summary += f"| **Service** | {service_intent.title()} |\n"
    summary += f"| **Core Purpose** | {lead.get('purpose', 'Not specified')} |\n"
    summary += f"| **Target Audience** | {lead.get('audience', 'Not specified')} |\n"
    summary += f"| **Platforms** | {lead.get('platforms', 'Not specified')} |\n"
    summary += f"| **Timeline** | {lead.get('timeline', 'Not specified')} |\n"
    summary += f"| **Budget** | {lead.get('budget', 'Not specified')} |\n"
    return summary


# ──────────────────────────────────────────────
# Main answer generator
# ──────────────────────────────────────────────


def _extract_project_details(llm, user_input, history):
    """Use LLM to extract project details and metadata (mood/engagement)."""
    prompt = f"""You are a data extraction assistant. Read the user message and conversation history, then extract structured info into JSON.

EXTRACTION RULES:
- Extract ANY value the user provides, even if vague or informal.
- "flexible", "low", "high", "any", "both", "open", "not sure", "you decide" ARE all valid values — extract them as-is.
- If the user's message directly answers a question from the history, extract it for that field.
- Only use "N/A" if there is genuinely NO information for that field anywhere.
- purpose: What project does the user want? (e.g. "app for F1 team", "website for business")
- audience: Who is the target user? (e.g. "fans", "customers", "both")
- platforms: What platforms? (e.g. "iOS and Android", "Desktop and Mobile", "Both"). CRITICAL: Do not extract generic terms like "web" or "app" unless the user specifically chooses between desktop/mobile or mobile platforms. If they just say "I want a website", return "N/A" for platforms so the bot can ask for specifics.
- timeline: When do they want it? (e.g. "1 week", "ASAP", "2 months")
- budget: How much can they spend? Extract values like "low", "flexible", "$5k", "no", "not decided". CRITICAL: If the user says "no" or "not decided", extract that text. Only use "N/A" if there is genuinely zero mention of budget.
- name: The user's personal name if shared.
- email: Email address if shared.
- meeting_time: When are they free for a call? (e.g. "Tuesday at 2pm", "Next Friday morning").
- mood: Frustrated | Impatient | Friendly | Neutral
- engagement: One-word | Detailed | Avoidant

Conversation History:
{history}

Current User Message: {user_input}

Return ONLY valid JSON with keys: purpose, audience, platforms, timeline, budget, name, email, meeting_time, mood, engagement. No explanation."""
    try:
        response = llm.invoke(prompt).content.strip()
        if "```json" in response: response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response: response = response.split("```")[1].split("```")[0].strip()
        import json
        data = json.loads(response)
        keys = ["purpose", "audience", "platforms", "timeline", "budget", "name", "email", "mood", "engagement"]
        for k in keys:
            if k not in data: data[k] = "N/A"
        return data
    except Exception as e:
        print(f"[rag_chain] Extraction error: {e}")
        return {k: "N/A" for k in ["purpose", "audience", "platforms", "timeline", "budget", "name", "email", "mood", "engagement"]}



def generate_answer(
    query: str,
    db=None,
    memory=None,
    chunks=None,
    session=None,
):
    q = query.strip()
    q_lower = q.lower()
    session_key = session.session_key if session else ""

    # Configuration for the models (Pro Tier)
    primary_model = "qwen/qwen-2.5-7b-instruct"
    secondary_model = "deepseek/deepseek-r1-distill-qwen-32b"
    tertiary_model = "mistralai/mistral-nemo"

    # DEBUG: See which key is being used
    print(f"[rag_chain] DEBUG: Active Key Starts with: {str(os.getenv('OPENAI_API_KEY'))}")

    llm = ChatOpenAI(
        model=primary_model,
        temperature=0.4,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_api_base="https://openrouter.ai/api/v1",
        max_tokens=800,          # Increased slightly for better paid model output
        max_retries=2,
        request_timeout=20,
    )

    # ── Guards ────────────────────────────────
    if is_sensitive(q):
        return "I can't help with sensitive or confidential information.", []
    if is_abusive(q):
        return "I'm here to help 🙂 Let me know what you need.", []

    # ── Extraction & State Update ───────────────────
    # Use LLM-based extraction for everything
    extracted = _extract_project_details(llm, q, memory.get_context() if memory else "")
    
    # Update sales agent state with extracted info
    name_found = extracted["name"] if extracted["name"] != "N/A" else None
    email_found = extracted["email"] if extracted["email"] != "N/A" else None
    
    sales_agent.update_state(
        q, 
        name_found, 
        email_found, 
        mood=extracted.get("mood", "Neutral"), 
        engagement=extracted.get("engagement", "Detailed")
    )
    
    # Update discovery fields
    if sales_agent.stage == "discovery" or sales_agent.stage == "contact_info":
        for key in ["purpose", "audience", "platforms", "timeline", "budget"]:
            val = extracted.get(key, "N/A")
            # We accept "Not Specified" as a terminal value to stop re-asking
            if val != "N/A" and not sales_agent.lead.get(key):
                sales_agent.lead[key] = val

    # ── Handle Meeting Intent ───────────────────────────────────────
    meeting_triggers = ["call", "meeting", "discuss", "connect", "schedule"]
    if any(t in q_lower for t in meeting_triggers) and sales_agent.lead["name"] and sales_agent.lead["email"]:
        result = schedule_meeting(sales_agent.lead["name"], sales_agent.lead["email"])
        sales_agent.stage = "done"
        return result, []

    # ── Service intent detection to trigger sales flow ───────────────────────
    service_intent = extract_service_intent(q)
    if service_intent != "general inquiry" and sales_agent.stage == "idle":
        sales_agent.start_flow(service_intent)

    # ── RAG & Prompt Generation ─────────────────────────────────────────
    context = ""
    docs = []
    try:
        if db is not None:
            docs = hybrid_retrieval(q, db, chunks)
            context = "\n\n".join(d.page_content for d in docs)
    except Exception as exc:
        print(f"[rag_chain] Retrieval error: {exc}")

    history = memory.get_context() if memory else ""
    directive = sales_agent.get_directive()
    prompt = get_prompt(context, history, q, directive)

    try:
        # 1. ATTEMPT PRIMARY (70B)
        response = llm.invoke(prompt)
        answer = response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        print(f"[rag_chain] Primary (70B) failed: {e}")
        try:
            # 2. ATTEMPT SECONDARY (8B)
            llm.model_name = secondary_model
            response = llm.invoke(prompt)
            answer = response.content if hasattr(response, "content") else str(response)
        except Exception as e2:
            print(f"[rag_chain] Secondary (8B) failed: {e2}")
            try:
                # 3. ATTEMPT TERTIARY (OpenRouter Auto-Free)
                llm.model_name = tertiary_model
                response = llm.invoke(prompt)
                answer = response.content if hasattr(response, "content") else str(response)
            except Exception as e3:
                print(f"[rag_chain] All models failed: {e3}")
                answer = "I'm temporarily overwhelmed with traffic. Could you please try again in a moment?"

    # ── Post-Response Lead Saving ───────────────────────────────────────
    # If we have name and email, and haven't saved this lead yet, save it!
    agent_name = sales_agent.lead.get("name")
    agent_email = sales_agent.lead.get("email")

    if agent_name and agent_email and sales_agent.stage == "wrap_up" and not sales_agent.lead.get("_lead_saved"):
        intent = service_intent if service_intent != "general inquiry" else "Consultation"
        
        # Pull details from sales_agent.lead
        lead_data = {
            "purpose":   sales_agent.lead.get("purpose", ""),
            "audience":  sales_agent.lead.get("audience", ""),
            "platforms": sales_agent.lead.get("platforms", ""),
            "timeline":  sales_agent.lead.get("timeline", ""),
            "budget":    sales_agent.lead.get("budget", ""),
        }
        
        print(f"[rag_chain] SAVING LEAD: {agent_name} | {agent_email} | {intent}")
        save_lead(
            agent_name, 
            agent_email, 
            intent, 
            session_key,
            **lead_data
        )
        
        # New: Save the exact Markdown summary table to the new Excel file
        summary_table = _generate_sales_summary(intent)
        save_lead_summary(agent_name, agent_email, session_key, summary_table)
        
        if session:
            session.register_lead(
                agent_name, 
                agent_email, 
                intent,
                **lead_data
            )
        
        sales_agent.lead["_lead_saved"] = True

    return answer, docs
