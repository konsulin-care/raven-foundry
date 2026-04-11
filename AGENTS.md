Raven is an offline-first CLI research system for academic knowledge curation.

CLI command: raven --query "..."
Entry point: raven.main:main

Stack:
- Python CLI application
- SQLite + sqlite-vector for local storage
- OpenAlex API for scientific metadata
- Groq LLM for reasoning tasks (rate-limited + cached)

Rules:
- Prefer local computation over external APIs
- Do not use LLMs for deterministic tasks (parsing, cleaning, embeddings)
- Maintain compatibility with pip-installable CLI entrypoint

Module-specific rules are defined in `src/raven/*/AGENTS.md` files:
- @src/raven/ingestion/AGENTS.md: Handles ingestion of scientific publications.
- @src/raven/embeddings/AGENTS.md: Handles semantic embedding generation
- @src/raven/llm/AGENTS.md: Handles all LLM interactions via Groq
- @src/raven/storage/AGENTS.md: Manages SQLite database and vector storage
