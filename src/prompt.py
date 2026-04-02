def get_prompt(context, question):
    return f"""
You are a professional AI assistant for Bytespark.

STRICT RULES:
- Answer ONLY using the provided context
- If listing items, include ALL items present in context
- Do NOT assume or hallucinate
- Do NOT skip items
- If exact count is asked, count properly from context

Context:
{context}

Question:
{question}

Answer:
"""