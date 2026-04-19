---
context: coverage
priority: high
version: 1.0
updated: 2026-04-14
title: Test Coverage Standards
purpose: Testing requirements and patterns for Raven Foundry
update_triggers: New modules | Testing framework changes | Coverage gaps
audience: Developers, AI agents
---

## Testing Framework

**Stack**: pytest + pytest-mock + requests-mock

**Run tests**:
```bash
pytest tests/ -v
```

## Unit Test Requirements

### Every function with a return value requires a unit test

```python
# Good - test covers return value
def test_search_papers_returns_list(tmp_path):
    db_path = tmp_path / "test.db"
    init_database(db_path)

    results = search_papers(db_path, "test")

    assert isinstance(results, list)

# Avoid - no assertion on return value
def test_search_papers():
    db_path = tmp_path / "test.db"
    init_database(db_path)
    search_papers(db_path, "test")  # No assertion
```

### Test File Naming

| Module | Test File |
|--------|---------|
| `raven.config` | `tests/test_unit.py` (mixed) |
| `raven.storage` | `tests/test_unit.py`, `tests/test_storage.py` |
| `raven.ingestion` | `tests/test_unit.py`, `tests/test_ingestion.py` |
| `raven.llm` | `tests/test_unit.py` |
| `raven.embeddings` | `tests/test_embeddings.py` |

### Test Function Naming

```python
def test_function_name_scenario():
    """Test description."""
    ...
```

## Test Patterns

### Database Tests

```python
def test_search_case_insensitive(tmp_path):
    db_path = tmp_path / "test.db"
    init_database(db_path)
    add_paper(db_path, "10.1234/test", "UPPERCASE Title", "article")

    results = search_papers(db_path, "uppercase")

    assert len(results) == 1
    assert results[0]["title"] == "UPPERCASE Title"
```

### CLI Tests (Click CliRunner)

```python
def test_search_command_with_results(tmp_path):
    runner = CliRunner()
    db_path = tmp_path / "test.db"
    init_database(db_path)
    add_paper(db_path, "10.1234/test", "Test Paper Title", "article")

    result = runner.invoke(
        raven.main.cli, ["search", "--db", str(db_path), "--local", "test"]
    )

    assert result.exit_code == 0
    assert "Test Paper Title" in result.output
```

### Mocking Environment Variables

```python
# Prefer monkeypatch over patch for env vars
def test_config_loads_api_key(monkeypatch):
    monkeypatch.setenv("OPENALEX_API_KEY", "test-key")

    key = get_openalex_api_key()

    assert key == "test-key"
```

## Coverage Requirements

| Module | Required Coverage |
|--------|-------------------|
| `raven.config` | 100% - All config functions |
| `raven.storage` | Core functions (init, add, search) |
| `raven.ingestion` | API calls, error handling |
| `raven.llm` | Cache, error handling |
| `raven.embeddings` | Model loading, encoding |

## Anti-Patterns to Avoid

1. **No assertions** - Every test must assert something
2. **Hardcoded values** - Use fixtures, not literals
3. **Skipping mocks** - Mock all external dependencies
4. **Testing implementation** - Test behavior, not internals

## Related Files

- Module AGENTS.md: `src/raven/*/AGENTS.md` (module-specific test rules)
- documentation.md: Documentation standards
