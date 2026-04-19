---
context: navigation
priority: critical
version: 1.0
updated: 2026-04-19
title: Standards Navigation
purpose: Coding practice standards for Raven Foundry
---

## Files

| File | Description | Priority |
|------|-------------|----------|
| code-style.md | Type hints, naming conventions | critical |
| code-patterns.md | SQLite ctx mgr, parameterized queries, mutable defaults | critical |
| validation.md | Input validation, assert rules, exception types | critical |
| imports.md | Import ordering | high |
| lazy-loading.md | Two-level lazy loading | high |
| anti-patterns.md | Anti-patterns to avoid | high |
| complexity.md | File size (200 max), cognitive complexity (15 max) | critical |
| coverage.md | Test coverage requirements | high |
| documentation.md | Docstring standards | high |

## Quick Reference

| Task | Standard File |
|------|--------------|
| Type hints, naming | code-style.md |
| SQLite, SQL, defaults | code-patterns.md |
| Input validation | validation.md |
| Import organization | imports.md |
| Performance | lazy-loading.md |
| What to avoid | anti-patterns.md |
| Complexity limits | complexity.md |
| Testing | coverage.md |
| Docstrings | documentation.md |

## Related Files

- `@AGENTS.md` - Root entry point
- `@docs/agent/navigation.md` - Agent context navigation
- `@docs/agent/workflows/` - Agent workflows
