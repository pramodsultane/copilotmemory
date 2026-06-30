"""copilotmemory - AI-powered memory layer for GitHub Copilot."""

__version__ = "0.1.0"
__author__ = "Pramod Sultane"
__license__ = "MIT"

from .memory.store import SessionMemoryStore
from .memory.embedder import CodeEmbedder
from .memory.retriever import ContextRetriever

__all__ = [
    "SessionMemoryStore",
    "CodeEmbedder",
    "ContextRetriever",
]
