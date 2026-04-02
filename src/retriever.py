def hybrid_retrieval(query, db, chunks, k=5):

    vector_docs = db.similarity_search(query, k=k)

    keyword_docs = [
        doc for doc in chunks
        if any(word in doc.page_content.lower() for word in query.lower().split())
    ]

    combined = vector_docs + keyword_docs

    unique_docs = list({doc.page_content: doc for doc in combined}.values())

    return unique_docs[:10]