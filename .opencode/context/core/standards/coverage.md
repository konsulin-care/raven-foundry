<!-- Context: core/standards/coverage | Priority: high | Version: 1.0 | Updated: 2026-04-14 -->

# Test Coverage Standards

**Purpose**: Testing requirements and patterns for Raven Foundry
**Last Updated**: 2026-04-14

## Quick Reference
**Update Triggers**: New modules | Testing framework changes | Coverage gaps
**Audience**: Developers, AI agents

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
|--------|-----------|
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

### API Mocking (requests-mock)
```python
def test_ingest_paper_success(tmp_path, requests_mock, monkeypatch):
    mock_response = {"title": "Sample Research Paper", "type": "article"}
    db_path = tmp_path / "test.db"
    init_database(db_path)

    requests_mock.get(
        "https://api.openalex.org/works/doi:10.1234/sample",
        json=mock_response,
    )

    monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
    monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

    result = ingest_paper(db_path, "10.1234/sample")

    assert result is not None
    assert result["title"] == "Sample Research Paper"
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

## Test Fixtures (conftest.py)

```python
@pytest.fixture
def tmp_db(tmp_path):
    """Create temporary database for tests."""
    db_path = tmp_path / "test.db"
    init_database(db_path)
    return db_path
```

## Anti-Patterns to Avoid

1. **No assertions** - Every test must assert something
2. **Hardcoded values** - Use fixtures, not literals
3. **Skipping mocks** - Mock all external dependencies
4. **Testing implementation** - Test behavior, not internals

## 📂 Codebase References
**Implementation**: `tests/` - All test files
**Config**: `tests/conftest.py` - Fixtures and configuration
**Module tests**: `tests/test_unit.py` - Comprehensive module tests

## Related Files
- Module AGENTS.md files: `src/raven/*/AGENTS.md` (module-specific test rules)
- documentation.md: Documentation standards
