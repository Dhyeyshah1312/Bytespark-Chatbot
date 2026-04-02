from src.loader import load_data
from src.chunker import split_docs
from src.embeddings import get_embeddings
from src.vectorstore import create_vectorstore
from src.rag_chain import generate_answer


# 🔹 SIMPLE MEMORY CLASS
class Memory:
    def __init__(self):
        self.history = []

    def add(self, user, bot):
        self.history.append((user, bot))

    def get_context(self):
        context = ""
        for u, b in self.history[-5:]:
            context += f"User: {u}\nAssistant: {b}\n"
        return context


# 🔹 LOAD DATA
docs1 = load_data("data/bytespark_companyinfo.pdf")
docs2 = load_data("data/services_pricing.pdf")

docs = docs1 + docs2

# 🔹 CHUNKING
print("🔹 Splitting documents...")
chunks = split_docs(docs)

# 🔹 EMBEDDINGS
print("🔹 Creating embeddings...")
embeddings = get_embeddings()

# 🔹 VECTOR DB
print("🔹 Creating vector database...")
db = create_vectorstore(chunks, embeddings)

# 🔹 MEMORY INIT
memory = Memory()

print("\n✅ Sales Chatbot Ready!\n")


# 🔹 CHAT LOOP
while True:
    query = input("Ask: ")

    if query.lower() == "exit":
        break

    answer, docs = generate_answer(query, db, memory)

    print("\n💬", answer, "\n")

    # 🔹 SAVE MEMORY
    memory.add(query, answer)