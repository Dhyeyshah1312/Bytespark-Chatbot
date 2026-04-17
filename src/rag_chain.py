from langchain_openai import ChatOpenAI
from src.prompt import get_prompt
from src.sales import SalesAgent
from src.meeting import schedule_meeting
from src.retriever import hybrid_retrieval
import os

llm = ChatOpenAI(
    model="openai/gpt-oss-20b",
    temperature=0.4,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_base="https://openrouter.ai/api/v1"
)

sales_agent = SalesAgent()


# 🔐 SECURITY
def is_sensitive(query):
    keywords = [
        "api key", "password", "credentials",
        "internal", "database", "system prompt",
        "hack", "bypass", "admin"
    ]
    return any(k in query.lower() for k in keywords)


# 🚫 ABUSE
def is_abusive(query):
    abusive = ["fuck", "shit", "idiot", "stupid"]
    return any(a in query.lower() for a in abusive)


def generate_answer(query, db, memory, chunks):

    q = query.strip()
    q_lower = q.lower()

    # 🔐 SECURITY
    if is_sensitive(q):
        return "I can’t help with sensitive or confidential information.", []

    # 🚫 ABUSE
    if is_abusive(q):
        return "I'm here to help 🙂 Let me know what you need.", []

    # 🔁 CONTINUE SALES FLOW (ONLY WHEN ACTIVE)
    sales_response = sales_agent.handle(q)

    if sales_agent.stage == "schedule_meeting":
        result = schedule_meeting(
            sales_agent.lead.get("name"),
            sales_agent.lead.get("email")
        )
        sales_agent.stage = "done"
        return result, []

    if sales_response:
        return sales_response, []

    # 🔍 RAG
    docs = hybrid_retrieval(q, db, chunks)
    context = "\n\n".join([doc.page_content for doc in docs])

    history = memory.get_context()

    prompt = get_prompt(context, history, q)

    try:
        response = llm.invoke(prompt).content
    except Exception:
        return "Something went wrong. Please try again.", []

    # 🧠 SMART MEETING DETECTION (NOT FORCED)
    meeting_intent = ["call", "meeting", "discuss", "connect"]

    if any(word in q_lower for word in meeting_intent):
        if sales_agent.stage == "idle":
            return sales_agent.start_flow(None), []

    return response, docs