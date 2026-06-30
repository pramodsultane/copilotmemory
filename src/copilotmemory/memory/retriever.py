"""Context retriever for semantic search and memory ranking."""

import sqlite3
import time
import uuid
from typing import Any, List, Optional

from .embedder import CodeEmbedder
from .store import SessionMemoryStore
from ..utils.config import get_settings
from ..utils.logger import logger


class SearchResult:
    """Represents a single search result."""

    def __init__(
        self,
        memory_id: str,
        code: str,
        language: str,
        description: str,
        relevance: float,
        created_at: str,
        tags: List[str],
    ):
        """Initialize search result."""
        self.memory_id = memory_id
        self.code = code
        self.language = language
        self.description = description
        self.relevance = relevance
        self.created_at = created_at
        self.tags = tags

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.memory_id,
            "code": self.code,
            "language": self.language,
            "description": self.description,
            "relevance": round(self.relevance, 4),
            "created_at": self.created_at,
            "tags": self.tags,
        }


class ContextRetriever:
    """
    Retrieves relevant memories through semantic search.

    Handles embedding queries, ranking results, and assembling
    context for injection into Copilot prompts.
    """

    def __init__(self):
        """Initialize the retriever."""
        self.store = SessionMemoryStore()
        self.embedder = CodeEmbedder()
        self.settings = get_settings()
        logger.info("Context retriever initialized")

    def search(
        self,
        query: str,
        limit: int = 5,
        threshold: Optional[float] = None,
    ) -> tuple[List[SearchResult], float]:
        """
        Search for relevant memories using semantic similarity.

        Args:
            query: Natural language query or code snippet
            limit: Maximum number of results to return
            threshold: Minimum relevance threshold (0-1)

        Returns:
            Tuple of (search results, execution time in ms)
        """
        if threshold is None:
            threshold = self.settings.similarity_threshold

        start_time = time.time()

        try:
            query_embedding = self.embedder.embed_text(query)

            results = self.store.vector_collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=min(limit, 20),
                include=["documents", "metadatas", "distances"],
            )

            search_results = []

            if results and results["ids"]:
                for idx, (memory_id, distance) in enumerate(
                    zip(results["ids"][0], results["distances"][0])
                ):
                    relevance = max(0, 1 - distance)

                    if relevance >= threshold:
                        memory = self.store.retrieve_memory(memory_id)
                        if memory:
                            search_results.append(
                                SearchResult(
                                    memory_id=memory_id,
                                    code=memory["code_snippet"],
                                    language=memory["language"],
                                    description=memory["description"],
                                    relevance=relevance,
                                    created_at=memory["created_at"],
                                    tags=memory["tags"],
                                )
                            )

            search_results.sort(
                key=lambda r: r.relevance,
                reverse=True,
            )
            search_results = search_results[:limit]

            execution_time_ms = (time.time() - start_time) * 1000
            self._record_search(query, len(search_results), execution_time_ms)

            logger.info(
                f"Search completed: {len(search_results)} results in {execution_time_ms:.2f}ms"
            )

            return search_results, execution_time_ms

        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return [], (time.time() - start_time) * 1000

    def assemble_context(
        self,
        search_results: List[SearchResult],
        max_tokens: int = 2000,
    ) -> str:
        """
        Assemble search results into formatted context.

        Args:
            search_results: List of search results
            max_tokens: Maximum approximate tokens for context

        Returns:
            Formatted context string
        """
        if not search_results:
            return ""

        context_parts = []
        context_parts.append("## Relevant Past Work\n")

        for idx, result in enumerate(search_results, 1):
            tags_str = ", ".join(result.tags) if result.tags else "no tags"
            section = (
                f"### Memory #{idx} (Match: {result.relevance:.1%})\n"
                f"**Language:** {result.language}\n"
                f"**Tags:** {tags_str}\n"
                f"**Created:** {result.created_at}\n"
                f"```{result.language}\n"
                f"{result.code[:500]}"
                f"{'...' if len(result.code) > 500 else ''}\n"
                f"```\n"
            )
            if result.description:
                section += f"**Notes:** {result.description}\n"

            context_parts.append(section)

        context = "\n".join(context_parts)

        # Truncate if necessary (rough token estimation: ~4 chars per token)
        if len(context) > max_tokens * 4:
            context = context[: max_tokens * 4] + "\n\n[... truncated]"

        return context

    def filter_by_language(
        self,
        results: List[SearchResult],
        language: str,
    ) -> List[SearchResult]:
        """
        Filter search results by programming language.

        Args:
            results: Search results to filter
            language: Programming language to filter by

        Returns:
            Filtered results
        """
        return [r for r in results if r.language.lower() == language.lower()]

    def deduplicate_results(
        self,
        results: List[SearchResult],
        similarity_threshold: float = 0.95,
    ) -> List[SearchResult]:
        """
        Remove near-duplicate results based on code similarity.

        Args:
            results: Search results to deduplicate
            similarity_threshold: Threshold for considering codes as duplicates

        Returns:
            Deduplicated results
        """
        deduplicated = []
        seen_hashes = set()

        for result in results:
            code_embedding = self.embedder.embed_text(result.code)

            is_duplicate = False
            for seen_code in [r.code for r in deduplicated]:
                seen_embedding = self.embedder.embed_text(seen_code)
                similarity = self.embedder.similarity_score(
                    code_embedding,
                    seen_embedding,
                )
                if similarity > similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                deduplicated.append(result)

        return deduplicated

    def _record_search(
        self,
        query: str,
        results_count: int,
        execution_time_ms: float,
    ) -> None:
        """
        Record search in history for analytics.

        Args:
            query: Search query
            results_count: Number of results returned
            execution_time_ms: Query execution time
        """
        import datetime

        search_id = f"srch_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.datetime.utcnow().isoformat()

        with sqlite3.connect(self.store.db_path) as conn:
            conn.execute(
                """
                INSERT INTO search_history
                (id, query, results_count, execution_time_ms, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (search_id, query, results_count, execution_time_ms, timestamp),
            )
            conn.commit()
