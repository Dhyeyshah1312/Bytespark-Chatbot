from langchain_openai import ChatOpenAI
import os

llm = ChatOpenAI(
    model="openrouter/auto",
    temperature=0,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    openai_api_base="https://openrouter.ai/api/v1"
)


def clean_output(text):
    text = text.strip().lower()
    if "yes" in text:
        return "YES"
    if "no" in text:
        return "NO"
    return text.upper()


def context_precision(query, retrieved_docs):
    context = "\n\n".join([doc.page_content for doc in retrieved_docs])

    prompt = f"""
Query: {query}
Context: {context}

Are retrieved docs relevant?

Answer ONLY YES or NO.
"""
    return clean_output(llm.invoke(prompt).content)


def faithfulness(answer, context):
    prompt = f"""
Answer: {answer}
Context: {context}

Is answer supported?

Answer ONLY YES or NO.
"""
    return clean_output(llm.invoke(prompt).content)


def answer_relevance(query, answer):
    prompt = f"""
Query: {query}
Answer: {answer}

Is answer relevant?

Answer ONLY YES or NO.
"""
    return clean_output(llm.invoke(prompt).content)