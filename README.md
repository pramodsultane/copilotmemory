# copilotmemory

An AI-powered memory layer for GitHub Copilot that stores, retrieves, and contextualizes past coding interactions to improve suggestion relevance over time.

## Vision

GitHub Copilot is an excellent code completion assistant, but it has no memory of your past work, decisions, or patterns within your codebase. **copilotmemory** bridges that gap by maintaining a semantic memory store of your coding interactions, enabling Copilot to provide more relevant, context-aware suggestions.

### How It Works

1. **Capture** — Records your coding sessions, function signatures, design decisions, and error patterns
2. **Embed** — Converts interactions into semantic embeddings for similarity-based retrieval
3. **Retrieve** — Finds relevant past context when you're writing new code
4. **Inject** — Automatically surfaces historical context to Copilot prompts
5. **Manage** — Simple CLI and web interface to organize, tag, and maintain your memory

## Features

- **Session Memory Store** — Lightweight local vector store for coding interactions
- **Semantic Search** — Similarity-based retrieval using embeddings
- **Context Injection** — Automatic surface of relevant historical context
- **Memory Management** — CLI tools to view, tag, and delete memories
- **Privacy-First** — All data stored locally; zero cloud dependencies

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Language** | Python 3.10+ |
| **Vector Database** | ChromaDB |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) |
| **API Framework** | FastAPI |
| **CLI** | Typer |
| **Metadata Store** | SQLite |
| **Testing** | pytest |

## Installation

### Prerequisites

- Python 3.10 or later
- pip or Poetry

### Quick Start

```bash
# Clone the repository
git clone https://github.com/pramodsultane/copilotmemory.git
cd copilotmemory

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Start the API server
copilotmemory serve
```

### Docker

```bash
docker build -t copilotmemory .
docker run -p 8000:8000 copilotmemory
```

## Usage

### CLI Commands

#### Store a coding session

```bash
copilotmemory store --file session.py --language python --tags "refactoring,optimization"
```

#### Search for relevant memories

```bash
copilotmemory search "how did I implement caching?" --limit 5
```

#### List all stored sessions

```bash
copilotmemory list
```

#### Delete a memory

```bash
copilotmemory delete <memory-id>
```

#### View memory details

```bash
copilotmemory show <memory-id>
```

#### Start API server

```bash
copilotmemory serve --host 0.0.0.0 --port 8000
```

### API Endpoints

#### `POST /api/v1/memories`
Store a new coding interaction or session.

**Request:**
```json
{
  "code_snippet": "def cache_layer(...): ...",
  "language": "python",
  "description": "Implemented caching layer for API responses",
  "tags": ["performance", "caching"]
}
```

**Response:**
```json
{
  "id": "mem_abc123def456",
  "created_at": "2024-06-30T10:30:00Z",
  "relevance_score": 0.95
}
```

#### `GET /api/v1/search`
Search for memories by semantic similarity.

**Query Parameters:**
- `query` (required): Natural language query
- `limit` (optional, default=5): Max results to return
- `threshold` (optional, default=0.6): Minimum relevance threshold

**Response:**
```json
{
  "results": [
    {
      "id": "mem_abc123def456",
      "code": "def cache_layer(...): ...",
      "description": "Implemented caching layer",
      "relevance": 0.94,
      "created_at": "2024-06-30T10:30:00Z"
    }
  ],
  "execution_time_ms": 45
}
```

#### `GET /api/v1/memories/{memory_id}`
Retrieve a specific memory by ID.

#### `DELETE /api/v1/memories/{memory_id}`
Delete a memory from the store.

#### `GET /api/v1/health`
Check API health status.

## Architecture

```
copilotmemory/
├── Session Capture Layer
│   └── Intercepts user coding interactions
├── Embedding Pipeline
│   ├── Code parsing & normalization
│   └── Vector generation (sentence-transformers)
├── Vector Store (ChromaDB)
│   ├── Semantic storage
│   └── Similarity search
├── Metadata Layer (SQLite)
│   ├── Timestamps, tags, lineage
│   └── Audit trails
├── Retrieval Engine
│   └── Context assembly & ranking
└── Integration Points
    ├── FastAPI (HTTP)
    ├── Typer (CLI)
    └── Direct Python API
```

### Core Components

1. **Memory Store** (`src/memory/store.py`)
   - Manages session persistence
   - Handles CRUD operations
   - Enforces privacy boundaries

2. **Embedder** (`src/memory/embedder.py`)
   - Generates semantic embeddings
   - Normalizes code snippets
   - Caches embedding results

3. **Retriever** (`src/memory/retriever.py`)
   - Performs similarity search
   - Ranks results by relevance
   - Formats context for injection

4. **API Server** (`src/api/routes.py`)
   - RESTful endpoints for integration
   - Request validation & response formatting
   - Error handling & logging

5. **CLI Interface** (`src/cli/commands.py`)
   - User-facing commands
   - Local memory management
   - Interactive exploration

## Configuration

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

### Environment Variables

```env
# Memory Store
MEMORY_DB_PATH=./data/memory.db
VECTOR_STORE_PATH=./data/vectors
EMBEDDING_MODEL=all-MiniLM-L6-v2

# API Server
API_HOST=127.0.0.1
API_PORT=8000
API_LOG_LEVEL=INFO

# Privacy & Security
MAX_MEMORY_SIZE_MB=1000
AUTO_CLEANUP_DAYS=90
ALLOW_REMOTE_ACCESS=false
```

## Development

### Project Structure

```
src/
├── copilotmemory/
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── store.py         # Vector store operations
│   │   ├── embedder.py      # Embedding generation
│   │   └── retriever.py     # Search & retrieval
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py        # FastAPI application
│   ├── cli/
│   │   ├── __init__.py
│   │   └── commands.py      # Typer CLI commands
│   └── utils/
│       ├── __init__.py
│       ├── config.py        # Configuration management
│       └── logger.py        # Logging utilities
tests/
├── test_memory.py
├── test_api.py
└── test_cli.py
docs/
└── architecture.md
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/copilotmemory

# Run specific test file
pytest tests/test_memory.py -v

# Run with markers
pytest -m "not integration"
```

### Code Style

We use `black`, `ruff`, and `mypy` for code quality:

```bash
black src/ tests/
ruff check src/ tests/
mypy src/
```

## Privacy & Security

### Key Principles

- **Local Storage First** — All data stored on your machine by default
- **No Cloud Sync** — No automatic data transmission
- **User Control** — Explicit consent for any data operations
- **Encrypted Storage** — Optional encryption for sensitive memories
- **Access Logging** — Track all memory access and modifications
- **Data Retention** — Configurable auto-cleanup policies

### What Gets Stored

- Code snippets and patterns
- Function signatures and implementations
- Design decisions and architectural notes
- Error patterns and debugging insights
- Search queries and retrieval results
- Metadata: timestamps, tags, language, file paths

### What Does NOT Get Stored

- Variable names or sensitive credentials (with proper scrubbing)
- API keys or authentication tokens
- Third-party service credentials
- Personal identifying information (PII)
- Any content explicitly marked as private

## Contributing

We welcome contributions! Please follow these guidelines:

1. **Fork the repository** and create a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Write tests** for new functionality
   ```bash
   pytest tests/
   ```

3. **Follow code standards**
   ```bash
   black src/ tests/
   ruff check src/ tests/
   mypy src/
   ```

4. **Update documentation** if adding features

5. **Commit with clear messages**
   ```bash
   git commit -m "feat: add [feature description]"
   ```

6. **Push and open a Pull Request**

### Development Setup

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

### Roadmap

- [ ] Advanced filtering and tagging system
- [ ] Integration with VS Code extension
- [ ] Copilot Chat plugin integration
- [ ] Knowledge graph relationships between memories
- [ ] Collaborative memory sharing (opt-in)
- [ ] Custom embedding models support
- [ ] Memory analytics dashboard
- [ ] Integration with popular code hosts (GitHub, GitLab)

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

**Copyright © 2024 Pramod Sultane**

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

## Support

- **Documentation** — See [docs/](docs/) directory
- **Issues** — Report bugs or feature requests on [GitHub Issues](https://github.com/pramodsultane/copilotmemory/issues)
- **Discussions** — Join [GitHub Discussions](https://github.com/pramodsultane/copilotmemory/discussions)

## Acknowledgments

Built with [FastAPI](https://fastapi.tiangolo.com/), [ChromaDB](https://www.trychroma.com/), and [sentence-transformers](https://www.sbert.net/).

---

**Made with ❤️ for developers who want their AI assistant to remember.**
