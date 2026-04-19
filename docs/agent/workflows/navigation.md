<!-- Context: workflows/navigation | Priority: critical | Version: 1.0 | Updated: 2026-04-19 -->

# Workflows Navigation

**Purpose**: AI agent workflows for Raven Foundry
**Updated**: 2026-04-19

## Files

| File | Description | Priority |
|------|-------------|----------|
| code-review.md | Code review checklist | high |
| task-delegation.md | How to delegate tasks | high |

## When to Use

### Code Review (`code-review.md`)
- When reviewing PRs or code changes
- When doing self-review before commit
- When reviewing others' code
- Check for: functionality, quality, naming, testing, security, performance

### Task Delegation (`task-delegation.md`)
- When task involves 4+ files
- When specialized knowledge needed
- When multi-component work
- When multi-step dependencies exist

## Delegation Triggers

| Condition | Action |
|-----------|--------|
| 4+ files in task | Delegate to CoderAgent |
| Specialized knowledge | Delegate to specialist |
| Multi-component review | Delegate to CodeReviewer |
| Multi-step dependencies | Delegate to TaskManager |
| Fresh perspective | Delegate to CodeReviewer |
| Edge case testing | Delegate to TestEngineer |

## Related Files

- `@AGENTS.md` - Root entry point
- `@docs/agent/navigation.md` - Agent context navigation
- `@docs/agent/standards/` - Coding practice standards
