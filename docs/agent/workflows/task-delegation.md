---
context: task-delegation
priority: high
version: 1.0
updated: 2026-04-14
title: Task Delegation Workflow
purpose: How to delegate tasks effectively in Raven Foundry
---

## When to Delegate

| Condition | Action |
|-----------|--------|
| 4+ files in task | Delegate to coder agent |
| Specialized knowledge needed | Delegate to specialist |
| Multi-component review | Delegate to review agent |
| Multi-step dependencies | Delegate to TaskManager |
| Fresh perspective needed | Delegate to review agent |
| Edge case testing | Delegate to TestEngineer |

## Context Passing

### Essential Context Files

Always pass relevant context to subagents:

| Task Type | Context to Load |
|----------|---------------|
| Code tasks | `code-style.md`, `code-patterns.md` |
| Test tasks | `coverage.md` |
| Docs tasks | `documentation.md` |
| Complexity issues | `complexity.md` |
| Validation issues | `validation.md` |
| Review tasks | `code-review.md` |
| Delegation | This file + relevant standards |

### Context Bundle (for complex delegation)

```python
# Create context bundle for subagent
context_bundle = """
# Task: Create feature X
# Requirements:
- Python 3.11+ with type hints
- SQLite context managers
- Parameterized queries

# Code standards:
- No mutable default args
- Use logging, not print

Files to modify:
- src/raven/storage/__init__.py
"""
```

## Approval Workflow

Before executing delegated tasks:

1. **Analyze** - What needs to be done?
2. **Plan** - Steps to complete
3. **Approve** - Request user confirmation
4. **Execute** - Run the delegated task
5. **Validate** - Check results
6. **Summarize** - Report back

## Error Handling

### Report First (Never Auto-Fix)

When delegated task fails:
1. Report the error
2. Propose fix
3. Request approval
4. Apply fix after approval

### Never Skip Context

- Always load required context before delegation
- Pass relevant context to subagent
- Verify subagent loaded context

## Related Files

- code-style.md: Code standards
- coverage.md: Test standards
- code-review.md: Review workflow
