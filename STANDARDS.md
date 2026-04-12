# Raven Foundry Code Standards

This document defines the safeguard layers to ensure all code follows specifications defined in `AGENTS.md` files.

---

## Layer 1: Specification Contracts

### Module Rules (from AGENTS.md)

| Module | File | Rules |
|--------|------|-------|
| ingestion | `src/raven/ingestion/AGENTS.md` | No LLMs, dedupe by DOI, CPU-efficient |
| embeddings | `src/raven/embeddings/AGENTS.md` | 384-dim, CPU-only, cache aggressively |
| llm | `src/raven/llm/AGENTS.md` | Batch requests, cache all, respect rate limits |
| storage | `src/raven/storage/AGENTS.md` | DOI unique, WAL mode, indexes |

### Contract Checklist (Pre-Implementation)

Before writing any function, complete:

- [ ] Which module does this belong to?
- [ ] Which AGENTS.md rule applies?
- [ ] What are the inputs/outputs/types?
- [ ] What are edge cases and error conditions?
- [ ] Will this integrate with the CLI workflow?

---

## Layer 2: Code Standards Enforcement

### Tooling Configuration

Update `pyproject.toml` with comprehensive linting and formatting:

```toml
[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "YTT", "C4", "RSE", "RET", "SLF", "RUF"]
ignore = ["E501", "RET505"]  # Line length, implicit return

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]  # Unused imports ok in init

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

### Module-Specific Rules

Create `src/raven/<module>/__init__.py` with explicit type annotations:

```python
# Every function must have:
# 1. Type hints on all inputs/outputs
# 2. Docstring with Args, Returns, Raises
# 3. Contract reference to AGENTS.md rule
```

---

## Layer 3: Testing Requirements

### Test Structure

```text
tests/
├── unit/
│   ├── test_ingestion/
│   ├── test_embeddings/
│   ├── test_llm/
│   └── test_storage/
├── integration/
│   └── test_cli_workflow.py
└── contracts/
    └── test_module_rules.py
```

### Contract Tests (Required for Each Module)

```python
# tests/contracts/test_ingestion_rules.py
def test_no_llm_in_ingestion_module():
    """Ensure ingestion module does not call LLM APIs."""
    import raven.ingestion as module

    # Verify no groq imports
    assert "groq" not in dir(module)

    # Verify no LLM-related function calls in source
    source = inspect.getsource(module)
    assert "groq" not in source
    assert "ChatCompletion" not in source

def test_deduplication_by_doi():
    """Verify DOI uniqueness is enforced."""
    # Test that adding duplicate DOI raises ValueError
    with pytest.raises(ValueError, match="already exists"):
        add_paper(path, "10.1234/test", "Title", "article")
```

### Coverage Requirements

| Module | Minimum Coverage |
|--------|-----------------|
| storage | 90% |
| ingestion | 80% |
| embeddings | 80% |
| llm | 80% |

---

## CI/CD Pipeline for Safeguards

```yaml
# .github/workflows/ci.yml
name: Safeguard Checks
on: [push, pull_request]

jobs:
  layer1-spec:
    runs-on: ubuntu-latest
    steps:
      - run: python -c "
          import ast
          # Verify all functions have docstrings and type hints
          # Verify module rules are followed
        "

  layer2-lint:
    runs-on: ubuntu-latest
    steps:
      - run: ruff check src/
      - run: mypy src/
      - run: black --check src/

  layer3-test:
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/ --cov=src/ --cov-fail-under=80
      - run: pytest tests/contracts/ --enforce-rules
```

---

## Quick Start Commands

```bash
# Layer 2: Run linting/formatting
ruff check src/
black --check src/
mypy src/

# Layer 3: Run tests with coverage
pytest tests/ --cov=src/ --cov-report=term-missing

# Run contract tests specifically
pytest tests/contracts/ -v

# All checks
make safeguard  # ruff && mypy && black && pytest
```
