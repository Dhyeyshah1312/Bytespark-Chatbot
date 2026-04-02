from langchain_openai import ChatOpenAI
from src.prompt import get_prompt
from src.sales import SalesAgent
from src.meeting import schedule_meeting
import os

# 🔹 LLM CONFIG
llm = ChatOpenAI(
    model="openrouter/auto",
    temperature=0,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_base="https://openrouter.ai/api/v1"
)

# 🔹 SALES AGENT
sales_agent = SalesAgent()

# 🔹 SERVICES LIST
service_names = [
    "Web Development",
    "App Development",
    "Cloud Services",
    "AI/ML Services",
    "UI/UX Design",
    "SEO Optimisation",
    "Digital Marketing"
]


# 🔹 RERANK
def rerank(query, docs):
    scored = []
    for doc in docs:
        text = doc.page_content.lower()
        score = sum(word in text for word in query.lower().split())
        scored.append((score, doc))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [doc for _, doc in scored[:5]]


# 🔥 SERVICE LIST DETECTOR
def detect_service_list(query):
    q = query.lower()

    triggers = [
        "services",
        "what do you offer",
        "what do you provide",
        "offerings",
        "solutions",
        "what can you do",
        "services provided",
        "list services",
        "all services"
    ]

    return any(t in q for t in triggers)


# 🔥 SERVICE DETECTOR
def detect_service(query):
    q = query.lower()

    mapping = {
        "seo": "SEO Optimisation",
        "web": "Web Development",
        "app": "App Development",
        "cloud": "Cloud Services",
        "ai": "AI/ML Services",
        "ui": "UI/UX Design",
        "marketing": "Digital Marketing"
    }

    for key, value in mapping.items():
        if key in q:
            return value

    return None


# 🔥 CONFIRMATION DETECTOR
def detect_confirmation(query):
    q = query.lower().strip()

    confirmations = [
        "yes",
        "okay",
        "ok",
        "yeah",
        "sure",
        "sounds good",
        "let's do it"
    ]

    return q in confirmations


# 🔹 INTENT CLASSIFIER
def classify_intent(query):

    prompt = f"""
Classify the user query into ONE of these intents:

1. service_count
2. service_detail
3. pricing
4. sales
5. general

Query: {query}

Return ONLY the intent name.
"""

    response = llm.invoke(prompt)
    return response.content.strip().lower().replace(".", "")


# 🔹 QUERY REWRITE
def rewrite_query(query, memory_context):

    if not memory_context.strip():
        return query

    prompt = f"""
Conversation:
{memory_context}

Query:
{query}

Rewrite clearly.
"""

    return llm.invoke(prompt).content.strip()


# 🔹 MULTI QUERY
def generate_queries(query):

    prompt = f"Generate 3 variations:\n{query}"

    response = llm.invoke(prompt).content.split("\n")

    return [q.strip() for q in response if q.strip()]


# 🔥 MAIN FUNCTION
def generate_answer(query, db, memory):

    q = query.lower().strip()

    # 🔥 GREETING
    if any(word in q for word in ["hi", "hello", "hey"]):
        return """Hey! 👋 I'm Bytespark's AI assistant.

I can help you with:
• Services & pricing
• Project consultation
• Booking a meeting

What would you like to explore? 😊
""", []

    # 🔥 SERVICE LIST
    if detect_service_list(query):
        return "\n".join([f"{i+1}. {name}" for i, name in enumerate(service_names)]), []

    # 🔥 DETECT SERVICE
    detected = detect_service(query)
    if detected:
        sales_agent.lead["service"] = detected

    # 🔥 CONFIRMATION → START SALES
    if detect_confirmation(query) and sales_agent.stage == "idle":
        service = sales_agent.lead.get("service", "your requirement")
        return sales_agent.start_flow(service), []

    # 🔹 INTENT
    intent = classify_intent(query)

    # 🔹 SERVICE COUNT
    if intent == "service_count":
        return f"Bytespark provides {len(service_names)} services.", []

    # 🔹 SALES FLOW CONTINUE
    sales_response = sales_agent.handle(query)

    if sales_agent.stage == "schedule_meeting":
        result = schedule_meeting(
            sales_agent.lead["name"],
            sales_agent.lead["email"]
        )
        sales_agent.stage = "done"
        return result, []

    if sales_response:
        return sales_response, []

    # 🔹 RAG FLOW
    memory_context = memory.get_context()
    new_query = rewrite_query(query, memory_context)

    queries = generate_queries(new_query)

    docs = []
    for q_var in queries:
        docs.extend(db.similarity_search(q_var, k=3))

    docs = list({doc.page_content: doc for doc in docs}.values())
    docs = rerank(new_query, docs)

    context = "\n\n".join([doc.page_content for doc in docs])

    prompt = get_prompt(context, new_query)

    response = llm.invoke(prompt)

    response_text = response.content

    # 🔥 SALES CTA
    if detected:
        response_text += """

🚀 This is a great choice.

Would you like me to:
• Connect you with our team
• Help plan your project
• Schedule a Google Meet

Just say "yes" 😊
"""

    return response_text, docs