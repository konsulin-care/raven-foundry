Handles ingestion of scientific publications.

Responsibilities:
- Query OpenAlex API
- Download PDFs
- Convert PDF → Markdown (MarkItDown)
- Clean extracted text

Rules:
- Deduplicate using DOI before insertion
- Do not use LLMs in this module
- Keep processing CPU-efficient
- Ensure ingestion integrates cleanly with CLI workflow

Implementation:
- Use raven.config.get_openalex_api_key() to retrieve API key
- Use raven.config.get_openalex_api_url() to get API URL (with default)
- Configuration is loaded from .env file in project root
- Raises ValueError if OPENALEX_API_KEY is not set
- Pass Bearer token as a parameter when sending a request, e.g. `GET "https://api.openalex.org/works?api_key=YOUR_KEY"`
