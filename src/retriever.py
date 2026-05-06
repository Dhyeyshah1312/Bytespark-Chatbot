from collections import defaultdict

# Keyword index cache (built once per session)
_keyword_index = None
_indexed_chunks = None


def _build_keyword_index(chunks):
    """Build efficient word-to-document index."""
    global _keyword_index, _indexed_chunks
    if _indexed_chunks is chunks:
        return _keyword_index
    
    _keyword_index = defaultdict(list)
    _indexed_chunks = chunks
    
    for i, doc in enumerate(chunks):
        words = set(doc.page_content.lower().split())
        for word in words:
            _keyword_index[word].append(i)
    
    return _keyword_index


def hybrid_retrieval(query, db, chunks, k=5):
    """
    Hybrid retrieval: vector similarity + keyword matching.
    Optimized with keyword indexing.
    """
    if not chunks or db is None:
        return []
    
    # Vector search (db call)
    vector_docs = db.similarity_search(query, k=k)
    vector_set = {doc.page_content for doc in vector_docs}
    
    # Fast keyword search using index
    query_words = set(query.lower().split())
    keyword_indices = set()
    
    index = _build_keyword_index(chunks)
    for word in query_words:
        if word in index:
            keyword_indices.update(index[word])
    
    keyword_docs = [chunks[i] for i in keyword_indices]
    
    # Combine and deduplicate
    combined = vector_docs + keyword_docs
    unique_dict = {}
    for doc in combined:
        if doc.page_content not in unique_dict:
            unique_dict[doc.page_content] = doc
    
    result = list(unique_dict.values())[:k]
    return result