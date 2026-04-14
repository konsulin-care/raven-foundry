<!-- Context: core/navigation | Priority: critical | Version: 1.0 | Updated: 2026-04-14 -->

# Context Navigation

| File | Description | Priority |
|------|-------------|----------|
| standards/documentation.md | Docstring and documentation style | high |
| standards/coverage.md | Test coverage requirements | high |
| standards/code-quality.md | Code style and quality rules | critical |
| workflows/code-review.md | Code review checklist | high |
| workflows/task-delegation.md | How to delegate tasks | high |

## Standards

### Code Quality (critical)
- Python 3.11+ type hints
- SQLite context managers
- Parameterized SQL queries
- No mutable default args
- Logging over print

### Documentation (high)
- Module docstrings with env variables
- Function docstrings with Args/Returns
- CLI command examples in docstrings

### Test Coverage (high)
- Tests for every function with return value
- Mock external dependencies
- pytest + requests-mock

## Workflows

### Code Review
- Functionality check
- Quality check (type hints, context managers)
- Security check (no API keys, parameterized queries)
- Testing check (coverage)

### Task Delegation
- Pass relevant context to subagents
- Use TaskManager for 4+ files
- Report-first on failures

## Quick Routes
- Project-specific: `project-intelligence/technical-domain.md`
- Module rules: `src/raven/*/AGENTS.md`

## Related Files
- Project Intelligence: `project-intelligence/`
