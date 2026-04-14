<!-- Context: core/standards/documentation | Priority: high | Version: 1.0 | Updated: 2026-04-14 -->

# Documentation Standards

**Purpose**: Documentation style and format for Raven Foundry codebase
**Last Updated**: 2026-04-14

## Quick Reference
**Update Triggers**: New modules | API changes | Documentation improvements
**Audience**: Developers, AI agents

## Docstring Format

### Module Docstrings
```python
"""Module name - One-line description.

Environment (from .env):
- API_KEY: Required. Get from https://example.com/
- API_URL: Optional. Defaults to https://api.example.com

Responsibilities:
- What the module does
- What it provides

Rules:
- Rule 1
- Rule 2
"""
```

### Function Docstrings
```python
def function_name(arg1: str, arg2: int | None = None) -> dict[str, Any]:
    """Short description of what the function does.

    Args:
        arg1: Description of first argument.
        arg2: Description of optional argument (default: None).

    Returns:
        Description of return value.

    Raises:
        ValueError: When specific condition occurs.
    """
```

## Type Hints

**Required for all functions**:
```python
# Good
def search_papers(db_path: Path, query: str) -> list[dict[str, Any]]:
    ...

# Avoid
def search_papers(db_path, query):
    ...
```

**Union types**:
```python
# Use | syntax (Python 3.10+)
def func(arg: str | None) -> int | None:
    ...

# Avoid (legacy)
def func(arg: Optional[str]) -> Optional[int]:
    ...
```

## Naming Documentation

| Element | Convention | Example |
|---------|-----------|---------|
| Modules | snake_case | `raven.storage`, `raven.ingestion` |
| Functions | snake_case | `get_groq_api_key()`, `search_papers()` |
| Classes | PascalCase | `Groq` (SDK), `SentenceTransformer` |
| Constants | UPPER_SNAKE | `DEFAULT_GROQ_MODEL`, `SEMANTIC_FILTERS` |

## CLI Command Documentation

Use Click's docstring format:
```python
@cli.command()
@click.argument("query")
@click.option("--filter", "-f", default=None, help="Filter description")
def search(ctx: click.Context, query: str, filter: str | None) -> None:
    """Search publications by query string.

    Examples:
        raven search "machine learning"
        raven search "AI" --filter "publication_year:>2020"
    """
```

## Code Examples

**Good**:
```python
# Clear, runnable example
from raven.storage import search_papers

results = search_papers(Path("raven.db"), "machine learning")
for paper in results:
    print(paper["title"])
```

**Avoid**:
- Incomplete snippets
- Outdated APIs
- No error handling examples

## 📂 Codebase References
**Implementation**: `src/raven/` - All modules follow these standards
**Tests**: `tests/test_unit.py` - Tests document module behavior

## Related Files
- Module AGENTS.md files: `src/raven/*/AGENTS.md`
- technical-domain.md: Tech stack patterns
