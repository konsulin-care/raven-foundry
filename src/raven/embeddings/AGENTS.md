Handles semantic embedding generation.

Model:
- multilingual-e5-small (384 dimensions)

Targets:
- Article summaries
- Section summaries
- Text chunks
- Hypotheses

Rules:
- Do not change embedding dimensionality
- Keep inference CPU-only
- Cache embeddings aggressively
- Ensure compatibility with SQLite vector schema
