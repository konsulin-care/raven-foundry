<!-- Context: lazy-loading | Priority: high | Version: 1.0 | Updated: 2026-04-19 -->

# Lazy Loading Standards

**Purpose**: Two-level lazy loading mechanism for Raven Foundry
**Updated**: 2026-04-19

## Level 1: CLI-level Lazy Loading (Primary)

Makes `raven` command fast by loading only the needed subcommand.

Located in `src/raven/main.py` using Click's `LazyGroup`:

```python
from raven.cli.lazy_group import LazyGroup

_LAZY_SUBCOMMANDS = {
    "search": "raven.cli.search:search",
    "ingest": "raven.cli.ingest:ingest",
    "init": "raven.cli.init:init",
}

@click.group(cls=LazyGroup, lazy_subcommands=_LAZY_SUBCOMMANDS)
def cli(ctx):
    ...
```

**Effect**: When user runs `raven search`, only the search module loads.

## Level 2: Module-level Lazy Loading (Secondary)

For backward compatibility in module `__init__.py` files.

```python
# src/raven/storage/__init__.py
def __getattr__(name: str) -> object:
    if name == "add_embedding":
        from raven.storage.embedding import add_embedding
        return add_embedding
    raise AttributeError(...)
```

**Effect**: Delays importing submodules until first attribute access.

## When to Use Which Level

| Scenario | Solution |
|----------|----------|
| CLI subcommand not always used | Use `LazyGroup` in `main.py` |
| Avoid circular imports | Use function-level import |
| Backward compatibility API | Use `__getattr__` in `__init__.py` |
| Function called on every invocation | Use top-level import |

## Related Files
- `imports.md`: Import ordering
- `anti-patterns.md`: Anti-patterns to avoid
