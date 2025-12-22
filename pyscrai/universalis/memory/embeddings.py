"""
Embeddings - Sentence transformer integration for PyScrAI Universalis.

This module provides embedding functions for semantic memory retrieval
using sentence-transformers.
"""

from typing import List, Optional, Callable
import numpy as np

from pyscrai.utils.logger import get_logger

logger = get_logger(__name__)

# Lazy load sentence-transformers to avoid import overhead
_model = None
_model_name = "all-MiniLM-L6-v2"


def _get_model():
    """Lazy load the sentence transformer model."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(_model_name)
            logger.info(f"Loaded sentence transformer model: {_model_name}")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
            raise
    return _model


def embed_text(text: str) -> List[float]:
    """
    Generate embedding for a single text.
    
    Args:
        text: Text to embed
    
    Returns:
        Embedding vector as list of floats
    """
    model = _get_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts.
    
    Args:
        texts: List of texts to embed
    
    Returns:
        List of embedding vectors
    """
    model = _get_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    return [e.tolist() for e in embeddings]


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
    
    Returns:
        Cosine similarity score (-1 to 1)
    """
    a = np.array(vec1)
    b = np.array(vec2)
    
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)


def get_embedding_function() -> Callable[[str], List[float]]:
    """
    Get the default embedding function.
    
    Returns:
        Function that takes text and returns embedding
    """
    return embed_text


def set_model(model_name: str) -> None:
    """
    Set the sentence transformer model to use.
    
    Args:
        model_name: Name of the model (from HuggingFace)
    """
    global _model, _model_name
    _model_name = model_name
    _model = None  # Force reload on next use
    logger.info(f"Embedding model set to: {model_name}")


class EmbeddingCache:
    """
    Cache for embeddings to avoid recomputation.
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize the cache.
        
        Args:
            max_size: Maximum number of embeddings to cache
        """
        self._cache: dict = {}
        self._max_size = max_size
        self._access_order: List[str] = []
    
    def get(self, text: str) -> Optional[List[float]]:
        """Get cached embedding or None."""
        return self._cache.get(text)
    
    def put(self, text: str, embedding: List[float]) -> None:
        """Add embedding to cache."""
        if text in self._cache:
            return
        
        # Evict oldest if full
        if len(self._cache) >= self._max_size:
            oldest = self._access_order.pop(0)
            del self._cache[oldest]
        
        self._cache[text] = embedding
        self._access_order.append(text)
    
    def embed_with_cache(self, text: str) -> List[float]:
        """
        Get embedding, using cache if available.
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector
        """
        cached = self.get(text)
        if cached is not None:
            return cached
        
        embedding = embed_text(text)
        self.put(text, embedding)
        return embedding
    
    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._access_order.clear()


# Default cache instance
_embedding_cache = EmbeddingCache()


def get_cached_embedding(text: str) -> List[float]:
    """
    Get embedding with caching.
    
    Args:
        text: Text to embed
    
    Returns:
        Embedding vector
    """
    return _embedding_cache.embed_with_cache(text)

