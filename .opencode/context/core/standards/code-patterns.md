<!-- Context: core/standards/code-patterns | Priority: critical | Version: 1.0 | Updated: 2026-04-19 -->

# Code Patterns

**Purpose**: Required code patterns for Raven Foundry
**Updated**: 2026-04-19

## SQLite Context Managers (REQUIRED)

Use `with sqlite3.connect()` for automatic resource cleanup.

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

## Parameterized Queries (REQUIRED)

Use `?` placeholders to prevent SQL injection attacks.

```python
# Good - prevents SQL injection
cursor.execute(
    "SELECT * FROM papers WHERE LOWER(title) LIKE LOWER(?)",
    (f"%{query}%",),
)

# Avoid - SQL injection risk
cursor.execute(f"SELECT * FROM papers WHERE title LIKE '%{query}%'")
```

## No Mutable Default Arguments

Use `None` + initialization inside to avoid shared state bugs.

```python
# Good
def func(arg: list[str] | None = None):
    items = arg if arg is not None else []

# Avoid
def func(arg: list[str] = []):  # Mutable default!
```

## DOI Case-Insensitive Storage

```python
# Use COLLATE NOCASE + LOWER()
conn.execute(
    "SELECT id FROM papers WHERE LOWER(doi) = LOWER(?)",
    (doi,),
)

# Table schema
doi TEXT UNIQUE NOT NULL COLLATE NOCASE
```

## Related Files
- `code-style.md`: Type hints and naming
- `validation.md`: Input validation rules
