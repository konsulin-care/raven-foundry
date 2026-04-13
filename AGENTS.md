# Getting Started

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
- Implement unit tests for each new functionality, unless the unit tests would introduce redundancy to the current test suites
- Tests should pass in pre-commit hooks (.pre-commit-config.yaml)

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

# Anti-Pattern Rules (detected via Context7)

All absolute rules in this section may be broken only when all of the following conditions are met:

1. **Criteria for Exception**: A documented technical reason why the rule cannot be followed (e.g., legacy constraint, performance requirement, library limitation)
2. **Authorization**: Tech lead or project maintainer approval required before implementation
3. **Tracking**: Exception must be documented in code comments with:
   - Technical reason for exception
   - Authorized by (name/role)
   - Date approved
   - Review date (maximum 6 months from approval)
4. **Audit**: Exceptions reviewed quarterly in project sync

This process applies to all rules in this section marked with *(Requires Exception Process)*.

## 1. Mutable Default Arguments *(Requires Exception Process)*

Never use mutable objects (list, dict) as default arguments, unless required by the in-function process. Use `None` and initialize inside the function.
   ```python
   # WRONG (Without Reason)
   def foo(mydict={}): ...
   # CORRECT
   def foo(mydict=None):
       if mydict is None: mydict = {}
   ```

## 2. SQLite Connection Leaks *(Requires Exception Process)*

The `with` statement for sqlite3 connections only manages transactions (commit/rollback) and does NOT close the Connection object. Always explicitly close connections to prevent leaks.

   ```python
   # WRONG (Without Reason) - No explicit close
   with sqlite3.connect(db) as conn:
       # ... use conn ...
   # Connection still open!

   # CORRECT - Explicit close after with block
   with sqlite3.connect(db) as conn:
       # ... use conn ...
   conn.close()  # See: sqlite3.connect, conn.close()

   # CORRECT - Using contextlib.closing for guaranteed closure
   import contextlib
   with contextlib.closing(sqlite3.connect(db)) as conn:  # See: contextlib.closing()
       # ... use conn ...
   # Connection automatically closed when block exits
   ```

   Key references:
   - `sqlite3.connect()` - Creates a Connection object
   - `with` statement - Only handles commit/rollback (see: "with" statement)
   - `conn.close()` - Explicitly closes the Connection
   - `contextlib.closing()` - Context manager that guarantees closure

## 3. Embedding Dimensionality Mismatch *(Requires Exception Process)*

Embedding dimension must match the model (384 for multilingual-e5-small). Do not hardcode mismatched dimensions in schema.

## 4. Case-Sensitive DOI (Digital Object Identifier) Matching *(Requires Exception Process)*

Use `COLLATE NOCASE` for DOI columns and `LOWER()` in queries to ensure case-insensitive matching. DOI is case-insensitive.

## 5. Local Imports in Tests *(Requires Exception Process)*

Move all imports to module level. Local imports inside functions are harder to mock and hurt test readability.
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
