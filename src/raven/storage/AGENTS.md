Manages SQLite database and vector storage.

Stack:
- SQLite + sqlite-vector

Data:
- 384-dim embeddings
- Metadata (DOI, title, type, timestamps)

Rules:
- Enforce DOI uniqueness
- Use WAL mode for durability
- Maintain indexes on DOI, type, title
- Optimize for long-term scale (50GB+ datasets)
