# copilotmemory Architecture

## System Overview

copilotmemory is built on a layered architecture that separates concerns across memory management, semantic search, API serving, and CLI interfaces.

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interfaces                           │
├──────────────────────────┬──────────────────────────────────┤
│   CLI (Typer)            │   REST API (FastAPI)             │
│  - Store commands        │  - /api/v1/memories              │
│  - Search commands       │  - /api/v1/search                │
│  - Management tools      │  - /api/v1/stats                 │
└──────────────────────────┴──────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────┐
│              Core Memory & Retrieval Layer                   │
├──────────────────────────┬──────────────────────────────────┤
│  ContextRetriever        │   SessionMemoryStore             │
│  - Semantic search       │  - CRUD operations               │
│  - Result ranking        │  - Metadata management           │
│  - Context assembly      │  - Cleanup & analytics           │
└──────────────────────────┴──────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────┐
│           Embedding & Storage Infrastructure                 │
├──────────────────────────┬──────────────────────────────────┤
│  CodeEmbedder            │   Storage Backend                │
│  - sentence-transformers │  - ChromaDB (vectors)            │
│  - Caching               │  - SQLite (metadata)             │
│  - Normalization         │  - File system                   │
└──────────────────────────┴──────────────────────────────────┘
```

## Component Details

### 1. Storage Layer

#### ChromaDB (Vector Store)
- **Purpose:** Store semantic embeddings for vector similarity search
- **Data:** Code embeddings, normalized documents
- **Operations:** Vector similarity queries, HNSW indexing
- **Location:** `./data/vectors/`

#### SQLite (Metadata Store)
- **Purpose:** Store structured metadata and search history
- **Tables:**
  - `memories` — Memory records with code, language, tags, timestamps
  - `search_history` — Search queries and performance metrics
- **Location:** `./data/memory.db`

### 2. Embedding System

#### CodeEmbedder
```python
class CodeEmbedder:
    - embed_text()          # Single text embedding
    - embed_batch()         # Batch processing for efficiency
    - normalize_code()      # Preprocessing and normalization
    - similarity_score()    # Cosine similarity calculation
    - caching               # Avoids redundant computations
```

**Model:** `all-MiniLM-L6-v2` (sentence-transformers)
- Lightweight (22M parameters)
- Fast inference
- Strong semantic understanding
- Supports code and natural language

### 3. Memory Store

#### SessionMemoryStore
```python
class SessionMemoryStore:
    - store_memory()        # Save new memories
    - retrieve_memory()     # Fetch specific memory
    - delete_memory()       # Remove from store
    - list_memories()       # Browse stored memories
    - cleanup_old_memories()# Retention policies
    - get_stats()          # Usage analytics
```

**Workflow:**
1. Accept code + metadata
2. Store metadata in SQLite
3. Generate embedding
4. Store embedding in ChromaDB
5. Return memory ID

### 4. Retrieval Engine

#### ContextRetriever
```python
class ContextRetriever:
    - search()              # Semantic search
    - assemble_context()    # Format for injection
    - filter_by_language()  # Post-search filtering
    - deduplicate_results() # Remove near-duplicates
    - _record_search()      # Analytics tracking
```

**Search Pipeline:**
1. Embed query using CodeEmbedder
2. Query ChromaDB for k-nearest neighbors
3. Fetch metadata from SQLite
4. Rank by relevance score
5. Filter by threshold
6. Format for presentation

### 5. API Layer

#### FastAPI Application
```
POST   /api/v1/memories         → Store memory
GET    /api/v1/search           → Search memories
GET    /api/v1/memories/{id}    → Retrieve memory
DELETE /api/v1/memories/{id}    → Delete memory
GET    /api/v1/memories         → List memories
GET    /api/v1/stats            → Get statistics
GET    /api/v1/health           → Health check
```

**Features:**
- Pydantic models for validation
- FastAPI async endpoints
- Automatic API documentation (`/docs`)
- Error handling and logging

### 6. CLI Interface

#### Typer Application
```
copilotmemory store           # Store code
copilotmemory search <query>  # Search
copilotmemory list            # List all
copilotmemory show <id>       # Show details
copilotmemory delete <id>     # Delete
copilotmemory stats           # Statistics
copilotmemory cleanup         # Cleanup old
copilotmemory serve           # Start server
```

## Data Flow

### Store Operation
```
User Input (code + metadata)
    ↓
SessionMemoryStore.store_memory()
    ├─→ SQLite: INSERT memory record
    ├─→ CodeEmbedder: Generate embedding
    └─→ ChromaDB: Store embedding
    ↓
Return memory_id
```

### Search Operation
```
Search Query
    ↓
CodeEmbedder.embed_text()
    ↓
ChromaDB.query() [vector similarity]
    ↓
Fetch metadata from SQLite
    ↓
ContextRetriever: Rank & filter
    ↓
Format & return results
    ↓
Record in search_history
```

## Configuration Management

### ApplicationSettings (Pydantic)
```python
- memory_db_path          # SQLite location
- vector_store_path       # ChromaDB location
- embedding_model         # sentence-transformers model
- api_host, api_port      # Server binding
- similarity_threshold    # Search relevance cutoff
- batch_size              # Processing batch size
- auto_cleanup_days       # Retention policy
```

**Loading:** `.env` file or environment variables

## Performance Considerations

### Embedding Optimization
- **Caching:** In-memory cache for frequently embedded texts
- **Batch Processing:** Vectorize multiple texts in parallel
- **Model Selection:** Lightweight model for speed

### Search Optimization
- **HNSW Indexing:** Approximate nearest neighbors (ChromaDB default)
- **Threshold Filtering:** Reduce irrelevant results early
- **Pagination:** Limit result set size

### Storage Efficiency
- **Vector Compression:** ChromaDB handles compression
- **Metadata Normalization:** SQLite for indexed queries
- **Automatic Cleanup:** Remove old memories per policy

## Extensibility Points

### Custom Embedders
Replace `CodeEmbedder` with alternative models:
```python
embedder = CodeEmbedder("model-name")
```

### Storage Backends
Switch vector/metadata stores:
- ChromaDB alternatives: Weaviate, Pinecone, Milvus
- SQLite alternatives: PostgreSQL, MySQL

### Search Filtering
Extend `ContextRetriever` with domain-specific filters:
```python
retriever.filter_by_complexity(results, max_complexity=3)
```

## Privacy & Security Architecture

### Local Storage
- All data stored on developer's machine
- No default cloud synchronization
- User controls data lifecycle

### Encryption (Future)
- SQLite encryption support (SQLCipher)
- Vector store encryption
- Optional credential scrubbing

### Access Logging
- `search_history` tracks all queries
- Metadata audit trails
- Compliance-ready design

## Testing Strategy

### Unit Tests
- Embedder: text encoding, normalization, similarity
- Store: CRUD operations, schema, cleanup
- Retriever: search logic, filtering, deduplication

### Integration Tests
- Store → Retriever → API pipeline
- CLI command execution
- End-to-end search workflow

### Performance Tests
- Embedding throughput
- Search latency
- Storage scalability (100K+ memories)

## Deployment Options

### Standalone CLI
```bash
pip install copilotmemory
copilotmemory serve
```

### Docker Container
```bash
docker build -t copilotmemory .
docker run -p 8000:8000 copilotmemory serve
```

### Integrated Extension
- VS Code extension (future)
- Copilot Chat integration (future)

## Roadmap

### Phase 1 (Current)
- Core memory store
- Semantic search
- CLI interface
- REST API

### Phase 2 (Next)
- VS Code extension
- Advanced filtering
- Memory analytics

### Phase 3 (Future)
- Copilot Chat plugin
- Collaborative sharing
- Knowledge graphs
