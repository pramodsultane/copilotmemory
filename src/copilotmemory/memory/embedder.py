"""Code embedder using sentence-transformers for semantic embeddings."""

import hashlib
from typing import List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from ..utils.config import get_settings
from ..utils.logger import logger


class CodeEmbedder:
    """
    Generates semantic embeddings for code snippets and text queries.

    Uses sentence-transformers with a lightweight model optimized for
    code and natural language understanding.
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the embedder with a specific model.

        Args:
            model_name: Name of the sentence-transformers model to use.
                       Defaults to configured model.
        """
        if model_name is None:
            settings = get_settings()
            model_name = settings.embedding_model

        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        self._embedding_cache: dict[str, np.ndarray] = {}

    def embed_text(self, text: str, use_cache: bool = True) -> np.ndarray:
        """
        Generate embedding for text.

        Args:
            text: Text to embed
            use_cache: Whether to use cached embeddings

        Returns:
            Embedding vector as numpy array
        """
        text_hash = self._compute_hash(text)

        if use_cache and text_hash in self._embedding_cache:
            return self._embedding_cache[text_hash]

        embedding = self.model.encode(text, convert_to_numpy=True)

        if use_cache:
            self._embedding_cache[text_hash] = embedding

        return embedding

    def embed_batch(
        self,
        texts: List[str],
        use_cache: bool = True,
    ) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of texts to embed
            use_cache: Whether to use cached embeddings

        Returns:
            List of embedding vectors
        """
        results = []
        texts_to_embed = []
        indices_to_embed = []

        for idx, text in enumerate(texts):
            text_hash = self._compute_hash(text)
            if use_cache and text_hash in self._embedding_cache:
                results.append((idx, self._embedding_cache[text_hash]))
            else:
                texts_to_embed.append(text)
                indices_to_embed.append((idx, text_hash))

        if texts_to_embed:
            embeddings = self.model.encode(
                texts_to_embed,
                convert_to_numpy=True,
            )

            for (idx, text_hash), embedding in zip(indices_to_embed, embeddings):
                if use_cache:
                    self._embedding_cache[text_hash] = embedding
                results.append((idx, embedding))

        results.sort(key=lambda x: x[0])
        return [embedding for _, embedding in results]

    def normalize_code(self, code: str) -> str:
        """
        Normalize code for consistent embedding.

        Performs basic preprocessing:
        - Strips leading/trailing whitespace
        - Normalizes line endings
        - Preserves semantic structure

        Args:
            code: Raw code string

        Returns:
            Normalized code
        """
        lines = code.split("\n")
        normalized = []

        for line in lines:
            line = line.rstrip()
            normalized.append(line)

        return "\n".join(normalized)

    def similarity_score(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score between 0 and 1
        """
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(
            np.dot(embedding1, embedding2) / (norm1 * norm2)
        )

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._embedding_cache.clear()
        logger.info("Embedding cache cleared")

    def get_cache_size(self) -> int:
        """Get current cache size in number of embeddings."""
        return len(self._embedding_cache)

    @staticmethod
    def _compute_hash(text: str) -> str:
        """
        Compute SHA256 hash of text for deduplication.

        Args:
            text: Text to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(text.encode()).hexdigest()
