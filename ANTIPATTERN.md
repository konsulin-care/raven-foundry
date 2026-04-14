# Anti-Pattern Rules

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
