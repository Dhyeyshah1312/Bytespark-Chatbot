from langchain_openai import OpenAIEmbeddings
import os
from functools import lru_cache

# Global embeddings instance (singleton)
_embeddings_instance = None


def get_embeddings():
    """Get or create a singleton embeddings instance with caching."""
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base="https://openrouter.ai/api/v1",
            cache_folder=".embeddings_cache",  # Cache embeddings locally
        )
    return _embeddings_instance