<!-- Context: core/standards/code-quality | Priority: critical | Version: 1.0 | Updated: 2026-04-14 -->

# Code Quality Standards

**Purpose**: Code style and quality rules for Raven Foundry
**Last Updated**: 2026-04-14

## Quick Reference
**Update Triggers**: Style changes | New patterns | Architecture decisions
**Audience**: Developers, AI agents

## Python Version

**Minimum**: Python 3.11+

Required for:
- Type union syntax (`str | None`)
- Structural pattern matching
- Modern typing features

## Type Hints

### Required everywhere
```python
def search_papers(db_path: Path, query: str) -> list[dict[str, Any]]:
    ...

def get_paper_id_by_doi(db_path: Path, doi: str | None) -> int | None:
    ...
```

### Union types (prefer | over Optional)
```python
# Preferred (Python 3.10+)
def func(arg: str | None) -> int | None:
    ...

# Avoid (legacy)
def func(arg: Optional[str]) -> Optional[int]:
    ...
```

### Module-level type ignores
```python
# Where needed, use inline ignores
return cursor.fetchone()[0]  # type: ignore[return-value]
```

## Code Patterns

### SQLite context managers (REQUIRED)
```python
# Good
with sqlite3.connect(db_path) as conn:
    cursor = conn.execute("SELECT ...", (args,))
    return [dict(row) for row in cursor.fetchall()]

# Avoid
conn = sqlite3.connect(db_path)
cursor = conn.execute("SELECT ...")
conn.close()  # Manual close - error-prone
```

### Parameterized queries (REQUIRED)
```python
# Good - prevents SQL injection
cursor.execute(
    "SELECT * FROM papers WHERE LOWER(title) LIKE LOWER(?)",
    (f"%{query}%",),
)

# Avoid - SQL injection risk
cursor.execute(f"SELECT * FROM papers WHERE title LIKE '%{query}%'")
```

### No mutable default arguments
```python
# Good
def func(arg: list[str] | None = None):
    items = arg if arg is not None else []

# Avoid
def func(arg: list[str] = []):  # Mutable default!
```

### DOI case-insensitive storage
```python
# Use COLLATE NOCASE + LOWER()
conn.execute(
    "SELECT id FROM papers WHERE LOWER(doi) = LOWER(?)",
    (doi,),
)

# Table schema
doi TEXT UNIQUE NOT NULL COLLATE NOCASE
```

## Input Validation

### Never use `assert` for runtime checks

**Problem**: `assert` statements are removed when Python runs with `-O` or `-OO` flags:

```python
# This check vanishes with python -O
assert conn is not None  # DANGEROUS in production
```

**Solution options**:

1. **Use `typing.cast()` for type narrowing** (preferred for static type checkers):
   ```python
   from typing import cast
   connection = cast(sqlite3.Connection, conn)
   ```

   **Warning**: `cast()` does **nothing at runtime** — it's purely for static type checkers. If `conn` is not actually a `sqlite3.Connection`, `cast()` will happily return the wrong value (e.g., `None`). Use `cast()` only when you are certain the value is of the target type.

2. **Use explicit exception for true runtime validation**:
   ```python
   if conn is None:
       raise ValueError("Connection must not be None")
   ```

3. **Use `typing.TYPE_CHECKING`** for type hints only:
   ```python
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from sqlite3 import Connection
   ```

### Exception types for validation

| Scenario | Exception | Example |
|----------|-----------|---------|
| Wrong type | `TypeError` | Passing `str` when `int` expected |
| Invalid value | `ValueError` | Number outside valid range |
| Missing required | `ValueError` | Required argument is None |
| Not implemented | `NotImplementedError` | Method not yet supported |

### Validation examples

```python
# Good - explicit validation with clear error
if not db_path:
    raise ValueError("db_path is required")

if not isinstance(paper_id, int):
    raise TypeError(f"paper_id must be int, got {type(paper_id).__name__}")

# Good - use cast for type narrowing (no runtime cost)
connection = cast(sqlite3.Connection, conn)

# Bad - will be stripped with python -O
assert conn is not None
```

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Files | snake_case | `config.py`, `ingestion/__init__.py` |
| Modules | snake_case | `raven.llm`, `raven.storage` |
| Functions | snake_case | `get_groq_api_key()`, `search_papers()` |
| Classes | PascalCase | `Groq`, `SentenceTransformer` |
| Constants | UPPER_SNAKE | `DEFAULT_GROQ_MODEL`, `SEMANTIC_FILTERS` |
| Database | snake_case | `papers`, `idx_papers_doi` |

### No built-in name shadowing
```python
# Good - use descriptive alternative names
def search_works(query: str, filter_str: str | None = None):
    ...

def process_items(items: list[int]) -> list[int]:
    ...

# Avoid - shadows Python built-ins
def search_works(query: str, filter: str | None = None):  # Shadows filter()!
    pass

# Avoid - shadows type built-ins
def get_items() -> list:  # Shadows list type!
    ...
```

## Error Handling

### Raise specific errors
```python
# Good
if not api_key:
    raise ValueError("GROQ_API_KEY is not set. Please add it to your .env file.")

# Avoid
if not api_key:
    raise Exception("Error")  # Too generic
```

### Handle API failures gracefully
```python
# Good
try:
    response = session.get(url, timeout=30)
except requests.exceptions.RequestException as e:
    logger.error("Network error: %s", e)
    return None

if response.status_code != 200:
    logger.error("API error: status %s", response.status_code)
    return None
```

### Idempotent database operations
```python
# Check before insert (required for DOI deduplication)
existing_id = get_paper_id_by_doi(db_path, doi)
if existing_id is not None:
    # Update or skip based on business logic
    ...
else:
    paper_id = add_paper(...)
```

## Logging

### Use module logger
```python
import logging

logger = logging.getLogger(__name__)

# Structured logging
logger.info("Adding new paper with DOI %s", doi)
logger.warning("Paper with DOI %s already exists", doi)
logger.error("Failed to fetch paper: %s", e)
```

### Avoid print statements
```python
# Good
logger.info("Database initialized at: %s", db_path)

# Avoid
print(f"Database initialized at: {db_path}")  # Use logging
```

## Security Requirements

1. **API keys in environment variables** - Never hardcode
2. **Input validation** - Validate all CLI arguments
3. **Parameterized SQL** - No string interpolation
4. **DOI normalization** - Before storage/queries

## Imports

### Standard ordering
```python
# 1. Standard library
import logging
from pathlib import Path
from typing import Any

# 2. Third-party
import click
import requests

# 3. Project local
from raven.config import get_groq_api_key
from raven.storage import add_paper
```

## Two-Level Lazy Loading Mechanism

Raven uses a two-level lazy loading pattern to optimize CLI startup performance:

### Level 1: CLI-level lazy loading (primary - makes `raven` command fast)

Located in `src/raven/main.py` using Click's `LazyGroup`:

```python
from raven.cli.lazy_group import LazyGroup

_LAZY_SUBCOMMANDS = {
    "search": "raven.cli.search:search",
    "ingest": "raven.cli.ingest:ingest",
    "init": "raven.cli.init:init",
}

@click.group(cls=LazyGroup, lazy_subcommands=_LAZY_SUBCOMMANDS)
def cli(ctx):
    ...
```

**Effect**: When user runs `raven search`, only the search module loads - not ingest, init, or other subcommands.

### Level 2: Module-level lazy loading (secondary - for backward compatibility)

Located in `__init__.py` files using `__getattr__`:

```python
# src/raven/storage/__init__.py
def __getattr__(name: str) -> object:
    if name == "add_embedding":
        from raven.storage.embedding import add_embedding
        return add_embedding
    raise AttributeError(...)
```

**Effect**: Delays importing submodules until first attribute access. Only matters if code explicitly imports from these modules.

### When to use which level

| Scenario | Solution |
|----------|----------|
| CLI subcommand not always used | Use `LazyGroup` in `main.py` |
| Avoid circular imports | Use function-level import (e.g., `config.py`) |
| Backward compatibility API | Use `__getattr__` in `__init__.py` |
| Function called on every invocation | Use top-level import (no lazy loading benefit) |

### Anti-Patterns to Avoid

| Anti-Pattern | Solution |
|--------------|----------|
| Mutable default args | Use `None` default + init inside |
| Raw SQL strings | Use parameterized queries |
| Print statements | Use logging module |
| Bare except | Catch specific exceptions |
| No type hints | Add type annotations |
| Magic numbers | Use named constants |
| Duplicate literals | Use named constants |
| Lazy import inside frequently-called function | Move to top-level - no benefit, adds overhead |

## 📂 Codebase References
**Implementation**:
- `src/raven/main.py` - CLI commands with Click
- `src/raven/storage/__init__.py` - SQLite with context managers
- `src/raven/ingestion/__init__.py` - API with retry logic
- `src/raven/config.py` - Env var handling

**Tests**: `tests/test_unit.py` - All modules tested

## File Size Management

**Rule**: No single Python file should exceed 200 lines.

**Rationale**:
- Files under 200 lines are easier to understand, test, debug, and review
- Large files indicate need for modularization (Single Responsibility Principle)
- Simplifies onboarding and reduces cognitive load

**Workflow after editing**:
1. Count lines: `wc -l <file>` or `wc -l src/raven/**/*.py`
2. If any file > 200 lines:
   - Call CodeReview subagent to review the code
   - Delegate to plan agent for refactoring strategy
   - Use Context7 MCP for refactoring best practices
3. Apply refactoring, verify tests pass

**Exception criteria** (see @ANTIPATTERN.md):
- Very small utility modules (<50 lines)
- Highly cohesive module with many small functions
- Files that are intentionally monolithic by design

**Context7 usage**: When planning refactoring, query Context7 for Python modularization best practices and module structure recommendations.

## Related Files
- Module AGENTS.md files: `src/raven/*/AGENTS.md`
- documentation.md: Docstring standards
- coverage.md: Test requirements
