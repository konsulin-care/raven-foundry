<!-- Context: core/workflows/task-delegation | Priority: high | Version: 1.0 | Updated: 2026-04-14 -->

# Task Delegation Workflow

**Purpose**: How to delegate tasks effectively in Raven Foundry
**Last Updated**: 2026-04-14

## Quick Reference
**Update Triggers**: Delegation patterns change | New subagents added
**Audience**: AI agents, developers

## When to Delegate

| Condition | Action |
|-----------|--------|
| 4+ files in task | Delegate to CoderAgent |
| Specialized knowledge needed | Delegate to specialist |
| Multi-component review | Delegate to CodeReviewer |
| Multi-step dependencies | Delegate to TaskManager |
| Fresh perspective needed | Delegate to CodeReviewer |
| Edge case testing | Delegate to TestEngineer |

## Delegation Pattern

### Direct Delegation (Simple)
```python
task(
    subagent_type="TestEngineer",
    description="Write tests for auth module",
    prompt="""Context to load:
- .opencode/context/core/standards/test-coverage.md

Task: Write comprehensive tests for auth module

Requirements:
- Positive and negative test cases
- Mock external dependencies

Files to test:
- src/raven/storage/__init__.py - Database operations
"""
)
```

### Complex Delegation (TaskManager)
For features requiring 4+ files or multi-step dependencies:

```python
task(
    subagent_type="TaskManager",
    description="Create user auth feature",
    prompt="""Load context from .tmp/sessions/{id}/context.md
Break down into subtasks with dependencies.
Mark parallel tasks with parallel: true.
"""
)
```

## Context Passing

### Essential Context Files
Always pass relevant context to subagents:

| Task Type | Context to Load |
|-----------|-----------------|
| Code tasks | `.opencode/context/core/standards/code-quality.md` |
| Test tasks | `.opencode/context/core/standards/coverage.md` |
| Docs tasks | `.opencode/context/core/standards/documentation.md` |
| Review tasks | `.opencode/context/core/workflows/code-review.md` |
| Delegation | This file + relevant standards |

### Context Bundle (for complex delegation)
```python
# Create context bundle for subagent
context_bundle = """
# Task: Create feature X
# Requirements from project-intelligence:
- Python 3.11+ with type hints
- SQLite context managers
- Parameterized queries

# From code-quality.md:
- No mutable default args
- Use logging, not print

Files to modify:
- src/raven/storage/__init__.py
"""
# Save to .tmp/context/{session-id}/bundle.md
```

## Subagent Types

| Agent | Use For |
|-------|---------|
| CoderAgent | General code implementation |
| TestEngineer | Writing tests |
| CodeReviewer | Code review, security |
| DocWriter | Documentation |
| TaskManager | Complex feature breakdown |
| ContextScout | Discover project context |
| ExternalScout | Fetch external library docs |

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

## 📂 Codebase References
**Examples**: See `src/raven/` module structure for delegation patterns
**Tests**: `tests/test_unit.py` - Task delegation tested

## Related Files
- code-quality.md: Code standards
- coverage.md: Test standards
- code-review.md: Review workflow
