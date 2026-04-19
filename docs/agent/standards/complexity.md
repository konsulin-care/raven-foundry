---
context: complexity
priority: critical
version: 1.0
updated: 2026-04-19
title: Complexity Limits
purpose: File size and cognitive complexity limits
---

## File Size Limits

**Maximum**: 300 lines per file.

**Warning threshold**: 200 lines - consider refactoring.

### Tiered Approach

| Lines | Action |
|-------|-------|
| <200 | No action needed |
| 200-300 | Warning - evaluate if refactoring is beneficial |
| >300 | Must refactor before merging |

Files under 200 lines are easier to understand, test, debug, and review.

### Check Command

```bash
wc -l src/raven/**/*.py
```

### If Exceeded

- 200-300 lines: Trigger CodeReview agent for evaluation
- >300 lines: Delegate to plan agent using Context7 for refactoring

### Exception Criteria

- Very small utility modules (<50 lines)
- Highly cohesive module with many small functions
- Files that are intentionally monolithic by design

## Cognitive Complexity Limits

**Maximum per function**: 15 cognitive complexity.

High cognitive complexity indicates functions that are difficult to understand, test, and maintain.

### What Counts as Cognitive Complexity

| Construction | Complexity Added |
|-------------|---------------|
| `if`, `elif`, `else` | +1 (plus nested level) |
| `for`, `while` loops | +1 (plus nested level) |
| `try`, `except`, `finally` | +1 (plus nested level) |
| Sequential `and`/`or` | +1 |

### Refactoring Strategies

When a function exceeds 15 complexity:

1. **Extract helper functions** - Move complex logic to smaller functions
2. **Consolidate duplicate code** - DRY principle reduces nesting
3. **Use early returns** - Guard clauses reduce nesting depth
4. **Replace nested conditionals** - Use lookup tables or polymorphism

### Example: Reducing Complexity

```python
# High complexity (~18)
def process_order(order):
    if order:
        if order.status == "pending":
            if order.payment:
                if order.payment.status == "confirmed":
                    process_payment(order)

# Refactored (~8)
def process_order(order):
    if not order:
        return
    if not is_ready_for_processing(order):
        return
    process_payment(order)
```

## Related Files

- `code-style.md`: Code style standards
- `anti-patterns.md`: Anti-patterns to avoid
