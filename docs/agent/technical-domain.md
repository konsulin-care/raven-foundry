<!-- Context: technical-domain | Priority: critical | Version: 1.2 | Updated: 2026-04-13 -->

# Technical Domain

**Purpose**: Tech stack, architecture, development patterns for Raven Foundry
**Last Updated**: 2026-04-13

## Quick Reference
**Update Triggers**: Tech stack changes | New modules | Architecture decisions
**Audience**: Developers, AI agents

## Primary Stack
| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| Language | Python | 3.11+ | Type hints, modern async support |
| CLI Framework | Click | 8.0+ | Simple command-line interface |
| Database | SQLite + sqliteai-vector | 3.x | Local-first, vector similarity search |
| LLM | Groq API | - | Fast inference, rate-limited |
| HTTP Client | Requests | 2.x | Simple API integration |
| Testing | pytest | - | Unit tests with mocks |

## Naming Conventions
| Type | Convention | Example |
|------|-----------|---------|
| Files | snake_case | `config.py`, `ingestion/__init__.py` |
| Modules | snake_case | `raven.llm`, `raven.storage` |
| Functions | snake_case | `get_groq_api_key()`, `search_papers()` |
| Classes | PascalCase | `Groq` (from SDK) |
| Constants | UPPER_SNAKE | `DEFAULT_GROQ_MODEL` |
| Database | snake_case | `papers`, `idx_papers_doi` |

## Code Standards
- Python 3.11+ with type hints
- SQLite context managers (`with sqlite3.connect() as conn`)
- DOI case-insensitive: `COLLATE NOCASE` + `LOWER()` in queries
- No mutable default args: use `None` and init inside function
- All functions with return values require unit tests
- No LLM for deterministic tasks (parsing, embeddings)
- Cache LLM responses with SHA256 keys

## Security Requirements
- API keys in environment variables, never in code
- Input validation on all CLI arguments
- Parameterized SQL queries (no string interpolation)
- DOI normalization before storage
- Handle network errors gracefully with retries

## Codebase References
**Implementation**:
- `src/raven/main.py` - CLI entry point with Click commands
- `src/raven/config.py` - Environment config loading from .env
- `src/raven/storage/__init__.py` - SQLite with WAL mode, indexes
- `src/raven/ingestion/__init__.py` - OpenAlex API, abstract reconstruction
- `src/raven/llm/__init__.py` - Groq client with in-memory cache
- `src/raven/embeddings/__init__.py` - Placeholder for vector embeddings

## Related Files
- Module AGENTS.md: `src/raven/*/AGENTS.md` for module-specific rules
- navigation.md: Agent context navigation
