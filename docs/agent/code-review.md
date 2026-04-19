<!-- Context: code-review | Priority: high | Version: 1.0 | Updated: 2026-04-14 -->

# Code Review Workflow

**Purpose**: Code review process and checklist for Raven Foundry
**Last Updated**: 2026-04-14

## Review Checklist

### 1. Functionality
- [ ] Code does what it's supposed to do
- [ ] Edge cases handled
- [ ] Error cases handled appropriately
- [ ] No silent failures

### 2. Code Quality
- [ ] Type hints on all functions
- [ ] No mutable default arguments
- [ ] Context managers for resources (SQLite, files)
- [ ] Parameterized SQL queries (no string interpolation)
- [ ] Logging instead of print statements

### 3. Naming & Style
- [ ] snake_case for functions/modules
- [ ] PascalCase for classes
- [ ] UPPER_SNAKE for constants
- [ ] Meaningful variable names
- [ ] No magic numbers (use constants)

### 4. Testing
- [ ] Tests cover return values
- [ ] Tests mock external dependencies
- [ ] No hardcoded test values
- [ ] Tests are deterministic

### 5. Security
- [ ] No API keys in code
- [ ] Input validation
- [ ] Parameterized queries
- [ ] DOI normalization

### 6. Performance
- [ ] Database indexes where needed
- [ ] Connection cleanup (context managers)
- [ ] No unnecessary iterations

## Common Issues to Flag

### Critical
- SQL injection vulnerabilities
- Hardcoded API keys
- Missing error handling
- No type hints on public functions

### Major
- Mutable default arguments
- Resource leaks (no context managers)
- Inconsistent naming
- Missing tests for new functions

### Minor
- Magic numbers
- Unused imports
- Code duplication

## Review Tools

**Run tests**:
```bash
pytest tests/ -v
```

## Related Files
- coverage.md: Test requirements
- Module AGENTS.md: Module-specific standards
