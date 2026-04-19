# Raven Foundry Code Standards

This document defines the coding standards used in Raven Foundry.

## Code Style

### Type Hints

All functions must have type hints. Ensures type safety and better IDE support.
See @docs/agent/code-style.md

### SQLite Context Managers

Use `with sqlite3.connect()` for automatic resource cleanup.
See @docs/agent/code-patterns.md

### Parameterized Queries

Use `?` placeholders to prevent SQL injection attacks.
See @docs/agent/code-patterns.md

### No Mutable Default Arguments

Use `None` + initialization inside to avoid shared state bugs.
See @docs/agent/code-patterns.md

### Input Validation

Never use `assert` for runtime checks - removed with `python -O`.
See @docs/agent/validation.md

### Import Ordering

Standard library → third-party → project local. Improves readability.
See @docs/agent/imports.md

### Lazy Loading

Use `LazyGroup` in CLI and `__getattr__` in modules for performance.
See @docs/agent/lazy-loading.md

## File Limits

### File Size

Maximum 300 lines per file. 200 lines triggers a warning to consider refactoring.
See @docs/agent/complexity.md

### Cognitive Complexity

Maximum 15 per function. Complex functions are hard to test and maintain.
See @docs/agent/complexity.md

## Testing

### Coverage Requirements

| Module | Minimum |
|--------|---------|
| storage | 90% |
| ingestion | 80% |
| embeddings | 80% |
| llm | 80% |

See @docs/agent/coverage.md for test structure.

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
