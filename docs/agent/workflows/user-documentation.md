---
context: user-documentation
priority: high
version: 1.0
updated: 2026-04-19
title: User Documentation Workflow
purpose: How to create user documentation in markdown format
---

## YAML Front Matter (Required)

Every documentation file must start with YAML front matter:

```yaml
---
context: <file-purpose>
priority: critical | high | medium | low
version: 1.0
updated: YYYY-MM-DD
title: Document Title
purpose: Brief description (max 50 chars)
---
```

**Keys**:

| Key | Required | Description |
|-----|----------|-------------|
| context | Yes | Unique identifier (kebab-case) |
| priority | Yes | critical, high, medium, low |
| version | Yes | Semantic version |
| updated | Yes | ISO date |
| title | Yes | Human-readable title |
| purpose | No | Brief description |

## Content Organization

### Heading Hierarchy

```markdown
# Top-level (one per file)
## Second-level
### Third-level
```

- Use single `#` for main title
- Avoid nesting beyond 3 levels
- Keep headings concise (< 50 chars)

### Tables (Preferred)

Use tables for quick reference over prose:

```markdown
| Column | Description |
|-------|-------------|
| Value | Brief info |
```

### Code Blocks

````markdown
```language
# Code here
```
````

- Specify language for syntax highlighting
- Use comments for explanations
- Keep examples minimal and runnable

## Line Limit Constraint

**Maximum**: 200 lines per documentation file

**Reason**: Minimum viable information - users scan, don't read fully

**Strategy**:
| Lines | Action |
|-------|-------|
| <100 | Preferred - concise |
| 100-200 | Acceptable - thorough |
| >200 | Split into multiple files |

## Quick Reference

### Good Patterns

| Pattern | Example |
|---------|---------|
| Tables over prose | Quick lookup |
| Code over explanation | Runnable examples |
| Headers over lists | Scannable structure |
| Links over copy | Single source of truth |

### Avoid Patterns

| Anti-Pattern | Solution |
|--------------|----------|
| Walls of text | Use tables or bullets |
| Duplicate info | Link to source |
| Outdated examples | Keep current or remove |
| Missing code language | Specify language |

## Related Files

- `documentation.md` (standards): Code documentation standards
- `navigation.md` (root): Agent context navigation
- `@AGENTS.md`: Root entry point
