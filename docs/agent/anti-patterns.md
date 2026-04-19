<!-- Context: anti-patterns | Priority: high | Version: 1.0 | Updated: 2026-04-19 -->

# Anti-Patterns to Avoid

**Purpose**: Common anti-patterns and their solutions
**Updated**: 2026-04-19

## Anti-Patterns Table

| Anti-Pattern | Solution |
|--------------|----------|
| Mutable default args | Use `None` default + init inside |
| Raw SQL strings | Use parameterized queries |
| Print statements | Use logging module |
| Bare except | Catch specific exceptions |
| No type hints | Add type annotations |
| Magic numbers | Use named constants |
| Duplicate literals | Use named constants |
| Lazy import inside frequently-called function | Move to top-level |

## Related Files
- `code-patterns.md`: Required code patterns
- `validation.md`: Input validation rules
