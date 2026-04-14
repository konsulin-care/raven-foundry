# Raven CLI System Initialization Proposal

## Project Overview

Raven is an offline-first, CLI-based research system designed for long-term academic knowledge curation. It prioritizes local computation, minimal hardware usage (1 CPU / 2GB RAM), and scalable storage over decades of data accumulation (50+ GB).

The system integrates semantic retrieval, structured ingestion of scientific publications, and optional LLM-assisted reasoning while minimizing external dependencies.

It is distributed as a pip-installable CLI tool:

```bash
raven --query "dna methylation in depression"
```

---

## Tech Stack Summary

### Core Application

* Python (CLI-based architecture)

### Database

* SQLite (primary storage)
* sqliteai-vector extension (vector similarity search)

### Embeddings

* multilingual-e5-small (384-dimensional embeddings, CPU inference)

### LLM Integration

* Groq API
* GPT OSS 120B model

### Data Processing

* Microsoft MarkItDown (PDF → Markdown conversion)
* Regex + heuristic text cleaning

### External API

* OpenAlex API (open-access scientific publication metadata)

### Infrastructure Design

* Offline-first / local-first architecture
* Queue-based scheduling system
* Token-aware rate limiting (Groq constraints)
* Local caching layer (LLM outputs + embeddings)

---

## Setup Instructions

### 1. Clone Repository

```bash
git clone <repo-url>
cd raven-cli
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install CLI Tool

```bash
pip install -e .
```

This registers the CLI command:

```bash
raven
```

---

### 4. Configure Environment

```bash
cp .env.example .env
```

Required variables:

* GROQ_API_KEY

---

### 5. Initialize Database

```bash
python scripts/init_db.py
```

---

## Directory Structure Explanation

```
raven-cli/
├── pyproject.toml              # Packaging + CLI entrypoint (raven)
├── src/
│   └── raven/
│       ├── main.py             # CLI entrypoint
│       ├── cli/                # Argument parsing + command routing
│       ├── core/               # Config, logging, utilities
│       ├── ingestion/          # OpenAlex + PDF ingestion pipeline
│       ├── embeddings/         # Embedding generation pipeline
│       ├── storage/            # SQLite + vector store layer
│       ├── llm/                # Groq integration + caching
│       ├── retrieval/          # Search + ranking pipeline
│       ├── scheduler/          # Queue + rate limiting system
│       └── models/             # Data models
├── data/                       # Local DB + cache storage
├── scripts/                    # Maintenance utilities
└── docs/                       # Module documentation
```

---

## Agent System Explanation

Raven uses distributed `AGENTS.md` files to guide AI-assisted development while keeping instructions minimal and modular.

### Design Principles

* Minimal, high-signal instructions per module
* Strict separation of concerns
* Progressive disclosure via `/docs`
* Avoid bloated global instruction sets

---

## AGENTS.md Placement Strategy

| Location                          | Purpose                                  |
| --------------------------------- | ---------------------------------------- |
| `/AGENTS.md`                      | Global CLI behavior + system constraints |
| `/src/raven/ingestion/AGENTS.md`  | Ingestion rules (OpenAlex, PDF parsing)  |
| `/src/raven/embeddings/AGENTS.md` | Embedding constraints and model rules    |
| `/src/raven/llm/AGENTS.md`        | Groq usage, batching, rate limits        |
| `/src/raven/storage/AGENTS.md`    | Database + vector indexing rules         |

---

## First Development Steps

### Step 1: CLI Foundation

* Implement `raven.main:main`
* Add argument parsing (`--query`)
* Connect CLI → command router

### Step 2: OpenAlex Integration

* Implement API client
* Normalize publication metadata
* Add DOI deduplication logic

### Step 3: Storage Layer

* Define SQLite schema
* Enable sqliteai-vector
* Implement insert/query abstraction

### Step 4: Embedding Pipeline

* Integrate multilingual-e5-small
* Generate embeddings for text units
* Store vectors in database

### Step 5: Retrieval Engine

* Query embedding generation
* Vector similarity search
* OpenAlex fallback search
* Ranking and top-N selection

---

## Execution Flow Example

```bash
raven --query "dna methylation in depression"
```

Pipeline:

1. Query refinement via Groq
2. Hypothesis generation
3. Local vector search
4. OpenAlex API search
5. Merge + rank results
6. Optional ingestion of new papers

---

## Long-Term Considerations

* Use WAL mode + periodic VACUUM
* Cache all embeddings and LLM outputs
* Monitor database growth (50GB+ scale)
* Introduce cold storage strategy if needed (archival DB or external vector store)
* Maintain strict rate-limit compliance for Groq API
