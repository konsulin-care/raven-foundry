"""LLM module - Groq-based LLM interactions for Raven.

Model: openai/gpt-oss-120b

Environment (from .env):
- GROQ_API_KEY: Required. Get from https://console.groq.com/
- GROQ_MODEL: Optional. Defaults to openai/gpt-oss-120b

Rules (from AGENTS.md):
- Batch requests whenever possible
- Cache all responses
- Respect rate limits (1000 req/day, TPM constraints)
- Never use LLMs for parsing or embeddings
- Route long-running tasks through scheduler when needed
"""

import json
from typing import Any, cast

import groq

# Import config for future Groq API integration
from raven.config import get_groq_api_key, get_groq_model  # noqa: F401

# Groq configuration
GROQ_MODEL = get_groq_model()
RATE_LIMIT_PER_DAY = 1000
TPM_LIMIT = 10000  # tokens per minute (example)


# Simple in-memory cache (replace with persistent cache for production)
_response_cache: dict[str, Any] = {}


def query_llm(prompt: str, system_prompt: str | None = None) -> str:
    """Query the LLM with a prompt."""
    # Validate API key - raises ValueError if falsy
    api_key = get_groq_api_key()

    # Check cache first
    cache_key = json.dumps({"prompt": prompt, "system": system_prompt})
    if cache_key in _response_cache:
        return cast(str, _response_cache[cache_key])

    # Build messages
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # Create Groq client and make request
    client = groq.Groq(api_key=api_key)
    chat_completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,  # type: ignore[arg-type]
    )

    # Extract response content
    message = chat_completion.choices[0].message
    if message.content is None:
        raise ValueError("Empty response from Groq API")
    content = cast(str, message.content)

    # Cache the response
    _response_cache[cache_key] = content

    return content


def query_llm_batch(prompts: list[str], system_prompt: str | None = None) -> list[str]:
    """Query the LLM with multiple prompts (batch processing).

    Processes each prompt via query_llm, which caches results per prompt.
    """
    # Validate API key - raises ValueError if falsy
    get_groq_api_key()

    # Map over prompts, allowing per-prompt caching
    return [query_llm(prompt, system_prompt) for prompt in prompts]


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
