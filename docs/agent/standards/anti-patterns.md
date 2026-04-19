<!-- Context: anti-patterns | Priority: high | Version: 1.0 | Updated: 2026-04-19 -->

# Anti-Patterns to Avoid

**Purpose**: Common anti-patterns and their solutions
**Updated**: 2026-04-19

All absolute rules in this section may be broken only when all of the following conditions are met:

1. **Criteria for Exception**: A documented technical reason why the rule cannot be followed (e.g., legacy constraint, performance requirement, library limitation)
2. **Tracking**: Exception must be documented in code comments with:
   - Technical reason for exception
   - Date of draft
3. **Audit**: Exceptions reviewed quarterly in project sync

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

The `with` statement for sqlite3 connections only manages transactions (commit/rollback) and does not close the Connection object. Always explicitly close connections to prevent leaks.

```python
# WRONG (Without Reason) - No explicit close
with sqlite3.connect(db) as conn:
    # ... use conn ...
# Connection still open!

# CORRECT - Try/finally guarantees closure even on exceptions
conn = sqlite3.connect(db)
try:
    # ... use conn ...
finally:
    conn.close()  # See: sqlite3.connect, conn.close(), try/finally

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

## 5. Local Imports in Functions *(Requires Exception Process)*

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

## 6. Shadowing Built-in Names *(Requires Exception Process)*

Never redefine Python built-in names (filter, map, sorted, list, set, dict, type, id, input, open, print, len, range, zip, int, str). These are core Python functions available in every scope. Shadowing them makes the original inaccessible and creates confusing bugs.
```python
# WRONG (Without Reason)
def search_works(query: str, filter: str | None = None):  # Shadows built-in!
    ...

# CORRECT (Use _str suffix or descriptive name)
def search_works(query: str, filter_str: str | None = None):
    ...

# Alternative: Use descriptive alternative names
def search_works(query: str, search_filter: str | None = None):
    ...
```

**Why this matters**: `filter` is one of Python's most used built-ins. A function parameter named `filter` shadows it globally, making the built-in unreadable within that function's scope and any nested scopes.

## 7. Duplicate Literals *(Requires Exception Process)*

Define a constant instead of duplicating a literal multiple times. Named constants make code more maintainable and prevent inconsistent values.
```python
# WRONG (Without Reason) - Duplicate literal
def search_works(sort: str = "relevance_score:desc"):
    ...
def search_works_keyword(sort: str = "relevance_score:desc"):
    ...
def search_works_semantic(params: dict = {"sort": "relevance_score:desc"}):
    ...

# CORRECT - Use named constant
DEFAULT_SORT_ORDER = "relevance_score:desc"

def search_works(sort: str = DEFAULT_SORT_ORDER):
    ...
def search_works_keyword(sort: str = DEFAULT_SORT_ORDER):
    ...
def search_works_semantic(params: Optional[dict] = None):
    if params is None:
        params = {"sort": DEFAULT_SORT_ORDER}
    ...
```

## Additional Anti-Patterns Table

| Anti-Pattern | Solution |
|--------------|----------|
| Mutable default args | Use `None` default + init inside |
| Raw SQL strings | Use parameterized queries |
| Print statements | Use logging module |
| Bare except | Catch specific exceptions |
| No type hints | Add type annotations |
| Magic numbers | Use named constants |
| Duplicate literals | Use named constants |
| Lazy import inside frequently-called function | Move to top-level |

## Related Files
- `@ANTIPATTERN.md` - Overview (root reference)
- `code-patterns.md`: Required code patterns
- `validation.md`: Input validation rules
