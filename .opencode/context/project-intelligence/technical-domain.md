<!-- Context: project-intelligence/technical | Priority: critical | Version: 1.0 | Updated: 2026-04-13 -->

# Technical Domain

**Purpose**: Tech stack, architecture, development patterns for Raven Foundry
**Last Updated**: 2026-04-13

## Quick Reference
**Update Triggers**: Tech stack changes | New modules | Architecture decisions
**Audience**: Developers, AI agents

## Primary Stack
| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| Language | Python | 3.11+ | Type hints, modern async support |
| CLI Framework | Click | 8.0+ | Simple command-line interface |
| Database | SQLite + sqlite-vector | 3.x | Local-first, vector similarity search |
| LLM | Groq API | - | Fast inference, rate-limited |
| HTTP Client | Requests | 2.x | Simple API integration |
| Testing | pytest | - | Unit tests with mocks |

## Code Patterns
### CLI Command (Python/Click)
```python
@cli.command()
@click.argument("query")
@click.option("--db", "-d", type=click.Path(path_type=Path), default=None)
def search(ctx: click.Context, query: str, db: Optional[Path]) -> None:
    """Search publications by query string."""
    db_path = _resolve_db_path(db)
    results = search_papers(db_path, query)
    for paper in results:
        click.echo(f"Title: {paper['title']}")
```

### Database Access (SQLite with context manager)
```python
def search_papers(db_path: Path, query: str) -> list[dict[str, Any]]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT doi, title, type FROM papers WHERE LOWER(title) LIKE LOWER(?)",
            (f"%{query}%",),
        )
        return [dict(row) for row in cursor.fetchall()]
```

### API Request with Retry
```python
def _create_session_with_retries() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    return session
```

## Naming Conventions
| Type | Convention | Example |
|------|-----------|---------|
| Files | snake_case | `config.py`, `ingestion/__init__.py` |
| Modules | snake_case | `raven.llm`, `raven.storage` |
| Functions | snake_case | `get_groq_api_key()`, `search_papers()` |
| Classes | PascalCase | `Groq` (from SDK) |
| Constants | UPPER_SNAKE | `DEFAULT_GROQ_MODEL` |
| Database | snake_case | `papers`, `idx_papers_doi` |

## Code Standards
- Python 3.11+ with type hints
- SQLite context managers (`with sqlite3.connect() as conn`)
- DOI case-insensitive: `COLLATE NOCASE` + `LOWER()` in queries
- No mutable default args: use `None` and init inside function
- All functions with return values require unit tests
- No LLM for deterministic tasks (parsing, embeddings)
- Cache LLM responses with SHA256 keys

## Security Requirements
- API keys in environment variables, never in code
- Input validation on all CLI arguments
- Parameterized SQL queries (no string interpolation)
- DOI normalization before storage
- Handle network errors gracefully with retries

## 📂 Codebase References
**Implementation**:
- `src/raven/main.py` - CLI entry point with Click commands
- `src/raven/config.py` - Environment config loading from .env
- `src/raven/storage/__init__.py` - SQLite with WAL mode, indexes
- `src/raven/ingestion/__init__.py` - OpenAlex API with retry logic
- `src/raven/llm/__init__.py` - Groq client with in-memory cache
- `src/raven/embeddings/__init__.py` - Placeholder for vector embeddings

**Config**: `pyproject.toml`, `.env` template

## Related Files
- Module AGENTS.md files: `src/raven/*/AGENTS.md` for module-specific rules
- Tests: `tests/test_unit.py` for all module tests
