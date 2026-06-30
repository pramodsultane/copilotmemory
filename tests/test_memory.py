"""Tests for copilotmemory core functionality."""

import pytest

from copilotmemory.memory.embedder import CodeEmbedder
from copilotmemory.memory.retriever import ContextRetriever
from copilotmemory.memory.store import SessionMemoryStore


@pytest.fixture
def store():
    """Create a temporary memory store for testing."""
    return SessionMemoryStore()


@pytest.fixture
def embedder():
    """Create an embedder instance."""
    return CodeEmbedder()


@pytest.fixture
def retriever():
    """Create a retriever instance."""
    return ContextRetriever()


class TestEmbedder:
    """Tests for code embedder."""

    def test_embed_text(self, embedder):
        """Test embedding generation."""
        text = "def hello_world(): print('Hello')"
        embedding = embedder.embed_text(text)
        assert embedding is not None
        assert len(embedding) > 0

    def test_embed_batch(self, embedder):
        """Test batch embedding."""
        texts = [
            "def function1(): pass",
            "def function2(): pass",
        ]
        embeddings = embedder.embed_batch(texts)
        assert len(embeddings) == len(texts)

    def test_similarity_score(self, embedder):
        """Test similarity calculation."""
        text1 = "def cache_function(): return cache"
        text2 = "def cache_function(): return cache"

        emb1 = embedder.embed_text(text1)
        emb2 = embedder.embed_text(text2)

        similarity = embedder.similarity_score(emb1, emb2)
        assert 0.95 <= similarity <= 1.0

    def test_normalize_code(self, embedder):
        """Test code normalization."""
        code = "def test():\n  pass\n"
        normalized = embedder.normalize_code(code)
        assert "\n" in normalized
        assert "def test():" in normalized


class TestMemoryStore:
    """Tests for session memory store."""

    def test_store_memory(self, store):
        """Test storing a memory."""
        memory_id = store.store_memory(
            code_snippet="def test(): pass",
            language="python",
            description="Test function",
            tags=["test", "demo"],
        )
        assert memory_id.startswith("mem_")

    def test_retrieve_memory(self, store):
        """Test retrieving a stored memory."""
        memory_id = store.store_memory(
            code_snippet="def test(): pass",
            language="python",
            description="Test function",
        )

        memory = store.retrieve_memory(memory_id)
        assert memory is not None
        assert memory["code_snippet"] == "def test(): pass"
        assert memory["language"] == "python"

    def test_delete_memory(self, store):
        """Test deleting a memory."""
        memory_id = store.store_memory(
            code_snippet="def test(): pass",
            language="python",
        )

        assert store.delete_memory(memory_id)
        assert store.retrieve_memory(memory_id) is None

    def test_list_memories(self, store):
        """Test listing memories."""
        store.store_memory("code1", "python")
        store.store_memory("code2", "javascript")

        memories = store.list_memories()
        assert len(memories) >= 2

    def test_get_stats(self, store):
        """Test getting store statistics."""
        store.store_memory("code", "python")
        stats = store.get_stats()

        assert "total_memories" in stats
        assert "language_distribution" in stats


class TestContextRetriever:
    """Tests for context retriever."""

    def test_search_empty_query(self, retriever):
        """Test search with no results."""
        results, exec_time = retriever.search("completely_unique_query_xyz")
        assert len(results) == 0
        assert exec_time > 0

    def test_assemble_context(self, retriever):
        """Test context assembly."""
        from copilotmemory.memory.retriever import SearchResult

        result = SearchResult(
            memory_id="mem_123",
            code="def test(): pass",
            language="python",
            description="Test",
            relevance=0.95,
            created_at="2024-01-01T00:00:00",
            tags=["test"],
        )

        context = retriever.assemble_context([result])
        assert "mem_123" in context
        assert "def test()" in context
        assert "python" in context

    def test_filter_by_language(self, retriever):
        """Test language filtering."""
        from copilotmemory.memory.retriever import SearchResult

        results = [
            SearchResult(
                memory_id="mem_1",
                code="code1",
                language="python",
                description="",
                relevance=0.9,
                created_at="2024-01-01",
                tags=[],
            ),
            SearchResult(
                memory_id="mem_2",
                code="code2",
                language="javascript",
                description="",
                relevance=0.8,
                created_at="2024-01-01",
                tags=[],
            ),
        ]

        filtered = retriever.filter_by_language(results, "python")
        assert len(filtered) == 1
        assert filtered[0].memory_id == "mem_1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
