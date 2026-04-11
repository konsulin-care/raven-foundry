"""LLM module - Groq-based LLM interactions for Raven.

Model: GPT OSS 120B

Rules (from AGENTS.md):
- Batch requests whenever possible
- Cache all responses
- Respect rate limits (1000 req/day, TPM constraints)
- Never use LLMs for parsing or embeddings
- Route long-running tasks through scheduler when needed
"""

import json
from typing import Any, cast

# Groq configuration
GROQ_MODEL = "llama-3.1-70b-versatile"
RATE_LIMIT_PER_DAY = 1000
TPM_LIMIT = 10000  # tokens per minute (example)


# Simple in-memory cache (replace with persistent cache for production)
_response_cache: dict[str, Any] = {}


def query_llm(prompt: str, system_prompt: str | None = None) -> str:
    """Query the LLM with a prompt."""
    # Check cache first
    cache_key = json.dumps({"prompt": prompt, "system": system_prompt})
    if cache_key in _response_cache:
        return cast(str, _response_cache[cache_key])

    # TODO: Implement actual Groq API call
    # - Respect rate limits
    # - Batch requests when possible
    # - Cache responses
    raise NotImplementedError("LLM integration not yet implemented")


def query_llm_batch(prompts: list[str], system_prompt: str | None = None) -> list[str]:
    """Query the LLM with multiple prompts (batch processing)."""
    # Per AGENTS.md: Batch requests whenever possible
    # This should process multiple prompts in a single request
    raise NotImplementedError("Batch LLM not yet implemented")


def generate_summary(text: str) -> str:
    """Generate a summary of the given text."""
    # Use case: Summarization
    return query_llm(
        f"Summarize this academic text concisely:\n\n{text}",
        system_prompt="You are an academic summarizer. Provide concise, accurate summaries.",
    )


def refine_query(user_query: str) -> str:
    """Refine a user query for better search results."""
    # Use case: Query refinement
    return query_llm(
        f"Refine this search query for finding academic papers:\n\n{user_query}",
        system_prompt="You are helping refine search queries. Output only the refined query.",
    )


def generate_hypotheses(context: str, count: int = 3) -> list[str]:
    """Generate research hypotheses based on context."""
    # Use case: Hypothesis generation
    result = query_llm(
        f"Based on this research context, generate {count} testable hypotheses:\n\n{context}",
        system_prompt="You are a research assistant. Generate specific, testable hypotheses.",
    )
    # Parse and return as list
    return [h.strip() for h in result.split("\n") if h.strip()]
