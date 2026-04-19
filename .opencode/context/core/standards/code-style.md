<!-- Context: core/standards/code-style | Priority: critical | Version: 1.0 | Updated: 2026-04-19 -->

# Code Style Standards

**Purpose**: Type hints and naming conventions for Raven Foundry
**Updated**: 2026-04-19

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

## Related Files
- `code-patterns.md`: Code patterns andanti-patterns
- `validation.md`: Input validation rules
