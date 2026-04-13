Handles all LLM interactions via Groq.

Model:
- GPT OSS 120B

Use cases:
- Query refinement
- Hypothesis generation
- Summarization

Rules:
- Batch requests whenever possible
- Cache all responses
- Respect rate limits (1000 req/day, TPM constraints)
- Never use LLMs for parsing or embeddings
- Route long-running tasks through scheduler when needed

Implementation:
- Use raven.config.get_groq_api_key() to retrieve API key
- Configuration is loaded from .env file in project root
- Raises ValueError if GROQ_API_KEY is not set
