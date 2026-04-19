<!-- Context: core/standards/imports | Priority: high | Version: 1.0 | Updated: 2026-04-19 -->

# Import Standards

**Purpose**: Import ordering rules for Raven Foundry
**Updated**: 2026-04-19

## Standard Ordering

Improves readability and identifies unused imports.

```python
# 1. Standard library
import logging
from pathlib import Path
from typing import Any

# 2. Third-party
import click
import requests

# 3. Project local
from raven.config import get_groq_api_key
from raven.storage import add_paper
```

## Related Files
- `lazy-loading.md`: Lazy loading patterns
- `code-patterns.md`: Code patterns
