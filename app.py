from src.loader import load_data
from src.chunker import split_docs
from src.embeddings import get_embeddings
from src.vectorstore import create_vectorstore
from src.rag_chain import generate_answer
from src.memory import Memory

docs1 = load_data("data/bytespark_companyinfo.pdf")
docs2 = load_data("data/services_pricing.pdf")

docs = docs1 + docs2

print("🔹 Splitting documents...")
chunks = split_docs(docs)

print("🔹 Creating embeddings...")
embeddings = get_embeddings()

print("🔹 Creating vector database...")
db = create_vectorstore(chunks, embeddings)

memory = Memory()

print("\n✅ Sales Chatbot Ready!\n")

while True:
    query = input("Ask: ")

    if query.lower() == "exit":
        break

    answer, docs = generate_answer(query, db, memory, chunks)

    print("\n💬", answer, "\n")

    memory.add(query, answer)