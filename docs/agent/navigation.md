<!-- Context: navigation | Priority: critical | Version: 1.1 | Updated: 2026-04-19 -->

# Agent Navigation

**Purpose**: Navigation guide for AI agents to find relevant context files.
**Updated**: 2026-04-19

## Directory Structure

| Directory | Purpose |
|----------|---------|
| `docs/agent/standards/` | Coding practice standards |
| `docs/agent/workflows/` | AI agent workflows (when to do/not do things) |
| `docs/agent/` (root) | Project-specific context |

## Quick Reference

### Standards (`docs/agent/standards/`)

| File | Description | Priority |
|------|-------------|----------|
| code-style.md | Type hints, naming conventions | critical |
| code-patterns.md | SQLite ctx mgr, parameterized queries | critical |
| validation.md | Input validation, assert rules | critical |
| imports.md | Import ordering | high |
| lazy-loading.md | Two-level lazy loading | high |
| anti-patterns.md | Anti-patterns to avoid | high |
| complexity.md | File size (200 max), cognitive complexity (15 max) | critical |
| coverage.md | Test coverage requirements | high |
| documentation.md | Docstring standards | high |

### Workflows (`docs/agent/workflows/`)

| File | Description | Priority |
|------|-------------|----------|
| code-review.md | Code review checklist | high |
| task-delegation.md | How to delegate tasks | high |

### Root (`docs/agent/`)

| File | Description | Priority |
|------|-------------|----------|
| technical-domain.md | Tech stack, architecture, patterns | critical |
| navigation.md | This file |

## Lazy Loading

Read files on-demand based on the specific task. Do NOT load all files at once.

## Quick Routes

| Task Type | Files to Load |
|----------|--------------|
| Code implementation | `standards/code-style.md` + `standards/code-patterns.md` |
| Testing | `standards/coverage.md` |
| Documentation | `standards/documentation.md` |
| Complex task | `workflows/task-delegation.md` |
| Code review | `workflows/code-review.md` |
| Performance | `standards/complexity.md` + `standards/lazy-loading.md` |
| Validation issues | `standards/validation.md` |

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
