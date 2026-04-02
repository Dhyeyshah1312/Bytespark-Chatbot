from langchain_community.vectorstores import FAISS

def create_vectorstore(chunks, embeddings):
    return FAISS.from_documents(chunks, embeddings)