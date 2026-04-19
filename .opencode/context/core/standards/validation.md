<!-- Context: core/standards/validation | Priority: critical | Version: 1.0 | Updated: 2026-04-19 -->

# Input Validation Standards

**Purpose**: Input validation rules for Raven Foundry
**Updated**: 2026-04-19

## Never Use Assert for Runtime Checks

`assert` statements are removed when Python runs with `-O` or `-OO` flags.

```python
# This check vanishes with python -O
assert conn is not None  # DANGEROUS in production
```

### Solution Options

1. **Use `typing.cast()` for type narrowing** (preferred for static type checkers):

```python
from typing import cast
connection = cast(sqlite3.Connection, conn)
```

**Warning**: `cast()` does **nothing at runtime** — it's purely for static type checkers.

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

### Validation Examples

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

## Exception Types for Validation

| Scenario | Exception | Example |
|----------|-----------|---------|
| Wrong type | `TypeError` | Passing `str` when `int` expected |
| Invalid value | `ValueError` | Number outside valid range |
| Missing required | `ValueError` | Required argument is None |
| Not implemented | `NotImplementedError` | Method not yet supported |

## Related Files
- `code-patterns.md`: Code patterns
- `code-style.md`: Type hints
