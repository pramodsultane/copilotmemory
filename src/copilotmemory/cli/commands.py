"""CLI commands for copilotmemory."""

import sys
from pathlib import Path
from typing import List, Optional

import typer
import uvicorn

from ..memory.retriever import ContextRetriever
from ..memory.store import SessionMemoryStore
from ..utils.config import get_settings
from ..utils.logger import logger

app = typer.Typer(
    help="copilotmemory - AI-powered memory layer for GitHub Copilot",
)


@app.command()
def store(
    file: Optional[Path] = typer.Option(
        None,
        "--file",
        "-f",
        help="Code file to store",
    ),
    code: Optional[str] = typer.Option(
        None,
        "--code",
        "-c",
        help="Code snippet to store (if not using --file)",
    ),
    language: str = typer.Option(
        "python",
        "--language",
        "-l",
        help="Programming language",
    ),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="Description of the memory",
    ),
    tags: Optional[str] = typer.Option(
        None,
        "--tags",
        "-t",
        help="Comma-separated tags",
    ),
) -> None:
    """Store a code snippet or file to memory."""
    store_service = SessionMemoryStore()

    if file:
        if not file.exists():
            typer.echo(f"Error: File not found: {file}", err=True)
            raise typer.Exit(code=1)
        code_snippet = file.read_text()
    elif code:
        code_snippet = code
    else:
        typer.echo("Error: Provide either --file or --code", err=True)
        raise typer.Exit(code=1)

    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    try:
        memory_id = store_service.store_memory(
            code_snippet=code_snippet,
            language=language,
            description=description,
            tags=tag_list,
            file_path=str(file) if file else None,
        )
        typer.echo(f"✓ Stored memory: {memory_id}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(5, "--limit", "-l", help="Max results"),
    threshold: float = typer.Option(
        0.6,
        "--threshold",
        "-t",
        help="Relevance threshold (0-1)",
    ),
) -> None:
    """Search for relevant memories."""
    retriever = ContextRetriever()

    try:
        results, exec_time = retriever.search(
            query=query,
            limit=limit,
            threshold=threshold,
        )

        if not results:
            typer.echo("No results found.")
            return

        typer.echo(f"\nFound {len(results)} matches in {exec_time:.2f}ms\n")

        for idx, result in enumerate(results, 1):
            relevance_pct = result.relevance * 100
            typer.echo(
                f"[{idx}] {result.memory_id} ({result.language}) - {relevance_pct:.1f}%"
            )
            typer.echo(f"    Tags: {', '.join(result.tags) or 'none'}")
            typer.echo(f"    Created: {result.created_at}")
            if result.description:
                typer.echo(f"    Description: {result.description}")
            typer.echo()

    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command()
def list(
    language: Optional[str] = typer.Option(
        None,
        "--language",
        "-l",
        help="Filter by language",
    ),
    limit: int = typer.Option(20, "--limit", help="Max results"),
) -> None:
    """List stored memories."""
    store_service = SessionMemoryStore()

    try:
        memories = store_service.list_memories(language=language, limit=limit)

        if not memories:
            typer.echo("No memories stored.")
            return

        typer.echo(f"\nTotal memories: {len(memories)}\n")

        for memory in memories:
            snippet_preview = memory["code_snippet"][:50].replace("\n", " ") + "..."
            typer.echo(f"{memory['id']} ({memory['language']})")
            typer.echo(f"  {snippet_preview}")
            typer.echo(f"  Created: {memory['created_at']}")
            typer.echo()

    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command()
def show(memory_id: str = typer.Argument(..., help="Memory ID")) -> None:
    """Display details of a specific memory."""
    store_service = SessionMemoryStore()

    try:
        memory = store_service.retrieve_memory(memory_id)

        if not memory:
            typer.echo(f"Memory not found: {memory_id}", err=True)
            raise typer.Exit(code=1)

        typer.echo(f"\nMemory: {memory['id']}")
        typer.echo(f"Language: {memory['language']}")
        typer.echo(f"Created: {memory['created_at']}")
        if memory['description']:
            typer.echo(f"Description: {memory['description']}")
        if memory['tags']:
            typer.echo(f"Tags: {', '.join(memory['tags'])}")
        typer.echo("\nCode:")
        typer.echo("---")
        typer.echo(memory["code_snippet"])
        typer.echo("---\n")

    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command()
def delete(memory_id: str = typer.Argument(..., help="Memory ID")) -> None:
    """Delete a memory."""
    store_service = SessionMemoryStore()

    if typer.confirm(f"Delete memory {memory_id}?"):
        try:
            if store_service.delete_memory(memory_id):
                typer.echo(f"✓ Deleted: {memory_id}", fg=typer.colors.GREEN)
            else:
                typer.echo(f"Memory not found: {memory_id}", err=True)
                raise typer.Exit(code=1)
        except Exception as e:
            typer.echo(f"Error: {str(e)}", err=True, fg=typer.colors.RED)
            raise typer.Exit(code=1)
    else:
        typer.echo("Cancelled.")


@app.command()
def stats() -> None:
    """Show memory store statistics."""
    store_service = SessionMemoryStore()

    try:
        stats_data = store_service.get_stats()

        typer.echo("\n=== Memory Store Statistics ===\n")
        typer.echo(f"Total memories: {stats_data['total_memories']}")
        typer.echo(f"Vector store entries: {stats_data['vector_collection_count']}")
        typer.echo(f"Search history entries: {stats_data['search_history_count']}")

        if stats_data["language_distribution"]:
            typer.echo("\nLanguage Distribution:")
            for lang, count in stats_data["language_distribution"].items():
                typer.echo(f"  {lang}: {count}")

        typer.echo()

    except Exception as e:
        typer.echo(f"Error: {str(e)}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command()
def cleanup(days: int = typer.Option(90, "--days", help="Days to retain")) -> None:
    """Clean up old memories."""
    store_service = SessionMemoryStore()

    if typer.confirm(f"Delete memories older than {days} days?"):
        try:
            deleted = store_service.cleanup_old_memories(days=days)
            typer.echo(
                f"✓ Cleaned up {deleted} memories",
                fg=typer.colors.GREEN,
            )
        except Exception as e:
            typer.echo(f"Error: {str(e)}", err=True, fg=typer.colors.RED)
            raise typer.Exit(code=1)
    else:
        typer.echo("Cancelled.")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Server host"),
    port: int = typer.Option(8000, "--port", "-p", help="Server port"),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of workers"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on changes"),
) -> None:
    """Start the FastAPI server."""
    settings = get_settings()

    if settings.allow_remote_access:
        host = "0.0.0.0"

    typer.echo(f"Starting server at http://{host}:{port}")
    typer.echo("API documentation available at http://localhost:8000/docs")

    uvicorn.run(
        "copilotmemory.api.routes:app",
        host=host,
        port=port,
        workers=workers,
        reload=reload,
    )


@app.callback()
def main(
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """copilotmemory - AI-powered memory for GitHub Copilot."""
    if debug:
        logger.setLevel("DEBUG")
        typer.echo("Debug mode enabled", err=True)


if __name__ == "__main__":
    app()
