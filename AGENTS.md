Raven is an offline-first CLI research system for academic knowledge curation.

CLI command: raven --query "..."
Entry point: raven.main:main

Stack:
- Python CLI application
- SQLite + sqliteai-vector for local storage
- OpenAlex API for scientific metadata
- Groq LLM for reasoning tasks (rate-limited + cached)

Rules:
- Prefer local computation over external APIs
- Do not use LLMs for deterministic tasks (parsing, cleaning, embeddings)
- Maintain compatibility with pip-installable CLI entrypoint
- Implement unit tests for each new functionality, unless the unit tests would introduce redundancy to the current test suites
- Tests should pass in pre-commit hooks (.pre-commit-config.yaml)
- OpenAlex API is the default search platform to use
- Use Context7 when implementing search using OpenAlex API
- Enforce 300-line max per file (200-line warning threshold)
- Enforce 15 max cognitive complexity per function

Testing Requirements:
- Every function with a return value should have a corresponding unit test, unless it has been indirectly tested
- Test files should follow pytest convention: test_*.py
- Test functions should follow convention: test_*
- Use pytest-mock for external dependencies (APIs, file I/O)
- Run tests in pre-commit: pip install pre-commit && pre-commit install
- CI runs tests on every PR to master and every commit in open PRs

Module-specific rules are defined in `src/raven/*/AGENTS.md` files:
- @src/raven/ingestion/AGENTS.md: Handles ingestion of scientific publications.
- @src/raven/embeddings/AGENTS.md: Handles semantic embedding generation
- @src/raven/llm/AGENTS.md: Handles all LLM interactions via Groq
- @src/raven/storage/AGENTS.md: Manages SQLite database and vector storage
- @ANTIPATTERN.md: Describe anti-patterns to avoid, and the exception criteria
