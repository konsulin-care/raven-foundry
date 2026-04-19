<!-- Context: navigation | Priority: critical | Version: 1.0 | Updated: 2026-04-19 -->

# Agent Navigation

**Purpose**: Navigation guide for AI agents to find relevant context files.
**Updated**: 2026-04-19

## Quick Reference

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
| code-review.md | Code review checklist | high |
| task-delegation.md | How to delegate tasks | high |
| technical-domain.md | Tech stack, architecture, patterns | critical |

## Lazy Loading

Read files on-demand based on the specific task. Do NOT load all files at once.

## Quick Routes

| Task Type | Files to Load |
|----------|--------------|
| Code implementation | code-style.md + code-patterns.md |
| Testing | coverage.md |
| Documentation | documentation.md |
| Complex task | Delegation pattern: task-delegation.md |
| Code review | code-review.md |
| Performance | complexity.md + lazy-loading.md |
| Validation issues | validation.md |

## Module Rules

Module-specific rules are in `src/raven/*/AGENTS.md`:
- `src/raven/ingestion/AGENTS.md`
- `src/raven/embeddings/AGENTS.md`
- `src/raven/llm/AGENTS.md`
- `src/raven/storage/AGENTS.md`

## Related Files

- `@AGENTS.md` - Root entry point
- `@STANDARDS.md` - Code standards summary
- `@ANTIPATTERN.md` - Anti-pattern rules
