# Anti-Pattern Rules

This document provides an overview of anti-patterns to avoid in Raven Foundry.

All absolute rules in this section may be broken only when all of the following conditions are met:

1. **Criteria for Exception**: A documented technical reason why the rule cannot be followed (e.g., legacy constraint, performance requirement, library limitation)
2. **Tracking**: Exception must be documented in code comments with:
   - Technical reason for exception
   - Date of draft
3. **Audit**: Exceptions reviewed quarterly in project sync

This process applies to all rules in this section marked with *(Requires Exception Process)*.

## Overview

| # | Anti-Pattern | Category |
|---|--------------|----------|
| 1 | Mutable Default Arguments | Code Patterns |
| 2 | SQLite Connection Leaks | Resource Management |
| 3 | Embedding Dimensionality Mismatch | Database |
| 4 | Case-Sensitive DOI Matching | Database |
| 5 | Local Imports in Functions | Testing |
| 6 | Shadowing Built-in Names | Code Style |
| 7 | Duplicate Literals | Code Style |

## Exception Process

To break any rule marked *(Requires Exception Process)*:

1. Document technical reason in code comments
2. Include date of exception draft
3. Review quarterly in project sync

## Detailed Documentation

See @docs/agent/standards/anti-patterns.md for comprehensive details, code examples, and solutions for each anti-pattern.
