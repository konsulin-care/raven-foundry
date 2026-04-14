<!-- Context: core/workflows/code-review | Priority: high | Version: 1.0 | Updated: 2026-04-14 -->

# Code Review Workflow

**Purpose**: Code review process and checklist for Raven Foundry
**Last Updated**: 2026-04-14

## Quick Reference
**Update Triggers**: Review process changes | New quality gates | Team feedback
**Audience**: Developers, AI agents

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

## Review Process

### For New Code
1. Check against checklist above
2. Verify tests exist for return values
3. Check error handling
4. Verify security requirements met

### For Bug Fixes
1. Identify root cause, not symptom
2. Add test to prevent regression
3. Verify fix doesn't break other tests

### For Refactors
1. Ensure behavior preserved
2. Add tests for new patterns
3. Remove dead code

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
- Missing docstrings
- Magic numbers
- Unused imports
- Code duplication

## Review Tools

**Run tests**:
```bash
pytest tests/ -v
```

**Check imports**:
```bash
python -m py_compile src/raven/*.py src/raven/*/*.py
```

## 📂 Codebase References
**Implementation**: All code in `src/raven/` follows these patterns
**Tests**: `tests/test_unit.py` - Comprehensive coverage

## Related Files
- code-quality.md: Detailed quality rules
- coverage.md: Test requirements
- Module AGENTS.md: Module-specific standards
