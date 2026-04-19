<!-- Context: documentation | Priority: high | Version: 1.0 | Updated: 2026-04-14 -->

# Documentation Standards

**Purpose**: Documentation style and format for Raven Foundry codebase
**Last Updated**: 2026-04-14

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

## Related Files
- Module AGENTS.md: `src/raven/*/AGENTS.md`
- technical-domain.md: Tech stack patterns
