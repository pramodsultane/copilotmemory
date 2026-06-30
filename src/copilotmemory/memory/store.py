"""Session memory store using ChromaDB and SQLite."""

import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List, Optional

import chromadb

from ..utils.config import get_settings
from ..utils.logger import logger


class SessionMemoryStore:
    """
    Manages persistent storage of coding sessions and interactions.

    Combines ChromaDB for vector operations and SQLite for metadata
    to provide efficient semantic search with rich metadata queries.
    """

    def __init__(self):
        """Initialize the memory store."""
        self.settings = get_settings()
        self.settings.ensure_data_directories()

        # Initialize ChromaDB
        vector_path = Path(self.settings.vector_store_path)
        self.chroma_client = chromadb.PersistentClient(path=str(vector_path))
        self.vector_collection = self.chroma_client.get_or_create_collection(
            name="code_memories",
            metadata={"hnsw:space": "cosine"},
        )

        # Initialize SQLite for metadata
        db_path = self.settings.memory_db_path
        self.db_path = db_path
        self._init_database()

        logger.info(f"Memory store initialized: {db_path}")

    def _init_database(self) -> None:
        """Initialize SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    code_snippet TEXT NOT NULL,
                    language TEXT NOT NULL,
                    description TEXT,
                    tags TEXT,
                    file_path TEXT,
                    line_number INTEGER,
                    file_hash TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS search_history (
                    id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    results_count INTEGER,
                    execution_time_ms FLOAT,
                    timestamp TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_created_at 
                ON memories(created_at)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_language 
                ON memories(language)
                """
            )
            conn.commit()

    def store_memory(
        self,
        code_snippet: str,
        language: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
    ) -> str:
        """
        Store a new coding session memory.

        Args:
            code_snippet: The code content
            language: Programming language
            description: Optional description of the memory
            tags: Optional list of tags for categorization
            file_path: Optional source file path
            line_number: Optional line number where code starts

        Returns:
            Memory ID
        """
        memory_id = f"mem_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()

        tags_str = ",".join(tags) if tags else ""

        # Store in SQLite
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO memories 
                (id, created_at, updated_at, code_snippet, language, 
                 description, tags, file_path, line_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    now,
                    now,
                    code_snippet,
                    language,
                    description or "",
                    tags_str,
                    file_path or "",
                    line_number,
                ),
            )
            conn.commit()

        # Store in ChromaDB
        combined_text = f"{code_snippet}\n{description or ''}\n{' '.join(tags or [])}"

        self.vector_collection.add(
            ids=[memory_id],
            documents=[combined_text],
            metadatas=[
                {
                    "language": language,
                    "code_length": len(code_snippet),
                    "has_description": bool(description),
                    "tag_count": len(tags or []),
                }
            ],
        )

        logger.info(f"Stored memory: {memory_id} ({language})")
        return memory_id

    def retrieve_memory(self, memory_id: str) -> Optional[dict[str, Any]]:
        """
        Retrieve a specific memory by ID.

        Args:
            memory_id: The memory ID

        Returns:
            Memory record or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM memories WHERE id = ?",
                (memory_id,),
            )
            row = cursor.fetchone()

            if row:
                tags_str = row["tags"]
                return {
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "code_snippet": row["code_snippet"],
                    "language": row["language"],
                    "description": row["description"],
                    "tags": tags_str.split(",") if tags_str else [],
                    "file_path": row["file_path"],
                    "line_number": row["line_number"],
                }

        return None

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory by ID.

        Args:
            memory_id: The memory ID

        Returns:
            True if deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM memories WHERE id = ?",
                (memory_id,),
            )
            deleted = cursor.rowcount > 0
            conn.commit()

        if deleted:
            self.vector_collection.delete(ids=[memory_id])
            logger.info(f"Deleted memory: {memory_id}")

        return deleted

    def list_memories(
        self,
        language: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict[str, Any]]:
        """
        List stored memories with optional filtering.

        Args:
            language: Filter by programming language
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of memory records
        """
        query = "SELECT * FROM memories"
        params: List[Any] = []

        if language:
            query += " WHERE language = ?"
            params.append(language)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        memories = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)

            for row in cursor.fetchall():
                tags_str = row["tags"]
                memories.append(
                    {
                        "id": row["id"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "code_snippet": row["code_snippet"],
                        "language": row["language"],
                        "description": row["description"],
                        "tags": tags_str.split(",") if tags_str else [],
                        "file_path": row["file_path"],
                        "line_number": row["line_number"],
                    }
                )

        return memories

    def get_stats(self) -> dict[str, Any]:
        """
        Get statistics about the memory store.

        Returns:
            Dictionary with store statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) as total FROM memories")
            total_count = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT language, COUNT(*) as count FROM memories GROUP BY language"
            )
            language_dist = {row[0]: row[1] for row in cursor.fetchall()}

            cursor = conn.execute(
                "SELECT COUNT(*) as total FROM search_history"
            )
            search_count = cursor.fetchone()[0]

        return {
            "total_memories": total_count,
            "language_distribution": language_dist,
            "search_history_count": search_count,
            "vector_collection_count": self.vector_collection.count(),
        }

    def cleanup_old_memories(self, days: Optional[int] = None) -> int:
        """
        Delete memories older than specified days.

        Args:
            days: Number of days to retain (defaults to settings)

        Returns:
            Number of memories deleted
        """
        if days is None:
            days = self.settings.auto_cleanup_days

        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id FROM memories WHERE created_at < ?",
                (cutoff_date,),
            )
            old_ids = [row[0] for row in cursor.fetchall()]

            if old_ids:
                placeholders = ",".join("?" * len(old_ids))
                conn.execute(
                    f"DELETE FROM memories WHERE id IN ({placeholders})",
                    old_ids,
                )
                conn.commit()

                self.vector_collection.delete(ids=old_ids)
                logger.info(f"Cleaned up {len(old_ids)} old memories")

        return len(old_ids)
