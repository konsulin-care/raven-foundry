# Raven Foundry Code Standards

This document defines the coding standards used in Raven Foundry.

## Code Style

### Type Hints

All functions must have type hints. Ensures type safety and better IDE support.
See @.opencode/context/core/standards/code-style.md

### SQLite Context Managers

Use `with sqlite3.connect()` for automatic resource cleanup.
See @.opencode/context/core/standards/code-patterns.md

### Parameterized Queries

Use `?` placeholders to prevent SQL injection attacks.
See @.opencode/context/core/standards/code-patterns.md

### No Mutable Default Arguments

Use `None` + initialization inside to avoid shared state bugs.
See @.opencode/context/core/standards/code-patterns.md

### Input Validation

Never use `assert` for runtime checks - removed with `python -O`.
See @.opencode/context/core/standards/validation.md

### Import Ordering

Standard library → third-party → project local. Improves readability.
See @.opencode/context/core/standards/imports.md

### Lazy Loading

Use `LazyGroup` in CLI and `__getattr__` in modules for performance.
See @.opencode/context/core/standards/lazy-loading.md

## File Limits

### File Size

Maximum 200 lines per file. Easier to understand, test, and debug.
See @.opencode/context/core/standards/complexity.md

### Cognitive Complexity

Maximum 15 per function. Complex functions are hard to test and maintain.
See @.opencode/context/core/standards/complexity.md

## Testing

### Coverage Requirements

| Module | Minimum |
|--------|---------|
| storage | 90% |
| ingestion | 80% |
| embeddings | 80% |
| llm | 80% |

See @.opencode/context/core/standards/coverage.md for test structure.

## Tooling

### Pre-commit Hooks

Run `ruff`, `mypy`, `black`, and `pytest` on every commit.
See `.pre-commit-config.yaml`

### Check Commands

```bash
ruff check src/
mypy src/
pytest tests/ --cov=src/ --cov-report=term-missing
```
