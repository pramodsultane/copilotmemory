"""FastAPI application and routes for copilotmemory."""

from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from ..memory.retriever import ContextRetriever
from ..memory.store import SessionMemoryStore
from ..utils.config import get_settings
from ..utils.logger import logger


# Pydantic models
class MemoryInput(BaseModel):
    """Input model for storing a memory."""

    code_snippet: str
    language: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None


class MemoryResponse(BaseModel):
    """Response model for a stored memory."""

    id: str
    code_snippet: str
    language: str
    description: Optional[str]
    tags: List[str]
    created_at: str
    updated_at: str


class SearchResultItem(BaseModel):
    """Single search result."""

    id: str
    code: str
    language: str
    description: Optional[str]
    relevance: float
    created_at: str
    tags: List[str]


class SearchResponse(BaseModel):
    """Response model for search results."""

    results: List[SearchResultItem]
    execution_time_ms: float
    query_count: int


class StatsResponse(BaseModel):
    """Response model for store statistics."""

    total_memories: int
    language_distribution: dict
    search_history_count: int
    vector_collection_count: int


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="copilotmemory",
        description="AI-powered memory layer for GitHub Copilot",
        version="0.1.0",
    )

    # Initialize core storage service eagerly.
    # Retriever is initialized lazily because model download can fail in
    # restricted network/certificate environments.
    store = SessionMemoryStore()
    retriever: Optional[ContextRetriever] = None

    def get_retriever() -> ContextRetriever:
        nonlocal retriever
        if retriever is None:
            retriever = ContextRetriever()
        return retriever

    # Health check
    @app.get("/api/v1/health")
    async def health_check() -> dict:
        """Check API health status."""
        try:
            stats = store.get_stats()
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "memory_count": stats["total_memories"],
            }
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Health check failed")

    # Store a new memory
    @app.post("/api/v1/memories", response_model=MemoryResponse)
    async def store_memory(memory: MemoryInput) -> dict:
        """
        Store a new coding interaction.

        Args:
            memory: Memory input data

        Returns:
            Stored memory details
        """
        try:
            memory_id = store.store_memory(
                code_snippet=memory.code_snippet,
                language=memory.language,
                description=memory.description,
                tags=memory.tags,
                file_path=memory.file_path,
                line_number=memory.line_number,
            )

            stored = store.retrieve_memory(memory_id)
            if not stored:
                raise HTTPException(status_code=500, detail="Failed to retrieve stored memory")

            return MemoryResponse(
                id=stored["id"],
                code_snippet=stored["code_snippet"],
                language=stored["language"],
                description=stored["description"],
                tags=stored["tags"],
                created_at=stored["created_at"],
                updated_at=stored["updated_at"],
            )

        except Exception as e:
            logger.error(f"Failed to store memory: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    # Search memories
    @app.get("/api/v1/search", response_model=SearchResponse)
    async def search_memories(
        query: str = Query(..., min_length=1),
        limit: int = Query(5, ge=1, le=50),
        threshold: float = Query(0.6, ge=0.0, le=1.0),
    ) -> dict:
        """
        Search for relevant memories.

        Args:
            query: Search query (natural language or code)
            limit: Maximum results to return
            threshold: Minimum relevance threshold

        Returns:
            Search results and metadata
        """
        try:
            active_retriever = get_retriever()
            results, execution_time = active_retriever.search(
                query=query,
                limit=limit,
                threshold=threshold,
            )

            return SearchResponse(
                results=[
                    SearchResultItem(
                        id=r.memory_id,
                        code=r.code,
                        language=r.language,
                        description=r.description,
                        relevance=r.relevance,
                        created_at=r.created_at,
                        tags=r.tags,
                    )
                    for r in results
                ],
                execution_time_ms=execution_time,
                query_count=len(results),
            )

        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            # Return actionable guidance for model/bootstrap failures
            # while still allowing non-search endpoints to work.
            raise HTTPException(
                status_code=503,
                detail=(
                    "Search unavailable. Embedding model could not be initialized. "
                    "Check network/certificates or pre-download the model."
                ),
            )

    # Retrieve specific memory
    @app.get("/api/v1/memories/{memory_id}", response_model=MemoryResponse)
    async def get_memory(memory_id: str) -> dict:
        """
        Retrieve a specific memory by ID.

        Args:
            memory_id: The memory ID

        Returns:
            Memory details
        """
        memory = store.retrieve_memory(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        return MemoryResponse(
            id=memory["id"],
            code_snippet=memory["code_snippet"],
            language=memory["language"],
            description=memory["description"],
            tags=memory["tags"],
            created_at=memory["created_at"],
            updated_at=memory["updated_at"],
        )

    # Delete memory
    @app.delete("/api/v1/memories/{memory_id}")
    async def delete_memory(memory_id: str) -> dict:
        """
        Delete a memory by ID.

        Args:
            memory_id: The memory ID

        Returns:
            Deletion confirmation
        """
        if store.delete_memory(memory_id):
            return {
                "status": "success",
                "message": f"Memory {memory_id} deleted",
            }
        else:
            raise HTTPException(status_code=404, detail="Memory not found")

    # List memories
    @app.get("/api/v1/memories")
    async def list_memories(
        language: Optional[str] = Query(None),
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ) -> dict:
        """
        List stored memories with optional filtering.

        Args:
            language: Filter by programming language
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of memories
        """
        try:
            memories = store.list_memories(
                language=language,
                limit=limit,
                offset=offset,
            )

            return {
                "memories": [
                    {
                        "id": m["id"],
                        "language": m["language"],
                        "code_snippet": m["code_snippet"][:100],
                        "description": m["description"],
                        "tags": m["tags"],
                        "created_at": m["created_at"],
                    }
                    for m in memories
                ],
                "count": len(memories),
            }

        except Exception as e:
            logger.error(f"Failed to list memories: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to list memories")

    # Statistics
    @app.get("/api/v1/stats", response_model=StatsResponse)
    async def get_stats() -> dict:
        """Get memory store statistics."""
        try:
            stats = store.get_stats()
            return StatsResponse(**stats)
        except Exception as e:
            logger.error(f"Failed to get stats: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get statistics")

    return app


# Create the app instance
app = create_app()
