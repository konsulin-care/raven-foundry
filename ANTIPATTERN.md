# Anti-Pattern Rules

This document provides an overview of anti-patterns to avoid in Raven Foundry.

All absolute rules in this section may be broken only when all of the following conditions are met:

1. A documented technical reason why the rule cannot be followed (e.g., legacy constraint, performance requirement, library limitation)
2. Exception must be documented in code comments with:
   - Technical reason for exception
   - Date of draft
3. Exceptions reviewed quarterly in project sync

This process applies to all rules in this section marked with *(Requires Exception Process)*.

## Overview

| Anti-Pattern | Category |
|--------------|----------|
| Mutable Default Arguments | Code Patterns |
| SQLite Connection Leaks | Resource Management |
| Embedding Dimensionality Mismatch | Database |
| Case-Sensitive DOI Matching | Database |
| Local Imports in Functions | Testing |
| Shadowing Built-in Names | Code Style |
| Duplicate Literals | Code Style |

## Exception Process

To break any rule marked *(Requires Exception Process)*:

1. Document technical reason in code comments
2. Include date of exception draft
3. Review quarterly in project sync

## Detailed Documentation

See @docs/agent/standards/anti-patterns.md for comprehensive details, code examples, and solutions for each anti-pattern.
