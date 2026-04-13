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
- Implement unit tests for each new functionality, unless the user explicitly requests otherwise
- Tests should pass in pre-commit hooks (.pre-commit-config.yaml), unless explicitly requested to skip
- Tests should pass in GitHub workflow (.github/workflows/safeguard.yml), unless explicitly requested to skip

Testing Requirements:
- Every function with a return value should have a corresponding unit test, unless impractical
- Test files should follow pytest convention: test_*.py, unless explicitly requested otherwise
- Test functions should follow convention: test_*, unless explicitly requested otherwise
- Use pytest-mock for external dependencies (APIs, file I/O)
- Run tests in pre-commit: pip install pre-commit && pre-commit install
- CI runs tests on every PR to master and every commit in open PRs

Module-specific rules are defined in `src/raven/*/AGENTS.md` files:
- @src/raven/ingestion/AGENTS.md: Handles ingestion of scientific publications.
- @src/raven/embeddings/AGENTS.md: Handles semantic embedding generation
- @src/raven/llm/AGENTS.md: Handles all LLM interactions via Groq
- @src/raven/storage/AGENTS.md: Manages SQLite database and vector storage

Anti-Pattern Rules (detected via Context7):

1. **Mutable Default Arguments**: Never use mutable objects (list, dict) as default arguments, unless explicitly requested. Use `None` and initialize inside the function.
   ```python
   # WRONG (Without Reason)
   def foo(mydict={}): ...
   # CORRECT
   def foo(mydict=None):
       if mydict is None: mydict = {}
   ```

2. **SQLite Connection Leaks**: Always use context managers (`with` statement) for sqlite3 connections to ensure proper closure, unless explicitly requested.
   ```python
   # WRONG (Without Reason)
   conn = sqlite3.connect(db)
   # ... use conn ...
   conn.close()
   # CORRECT
   with sqlite3.connect(db) as conn:
       # ... use conn ...
   ```

3. **Embedding Dimensionality Mismatch**: Embedding dimension must match the model (384 for multilingual-e5-small), unless explicitly requested. Do not hardcode mismatched dimensions in schema.

4. **Case-Sensitive DOI Matching**: Use `COLLATE NOCASE` for DOI columns and `LOWER()` in queries to ensure case-insensitive matching. DOIs (Digital Object Identifiers) are case-insensitive.

5. **Local Imports in Tests**: Move all imports to module level. Local imports inside functions are harder to mock and hurt test readability.
   ```python
   # WRONG (Without Reason)
   def test_something(self):
       from module import function
       function()

   # CORRECT (At Module Top)
   from module import function

   def test_something(self):
       function()
   ```
