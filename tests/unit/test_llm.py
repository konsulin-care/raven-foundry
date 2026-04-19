"""Unit tests for Raven LLM module.

Run with: pytest tests/unit/test_llm.py -v
"""

from raven.llm import _make_cache_key

# LLM Module Tests


class TestLLMModule:
    """Tests for raven.llm module."""

    def test_make_cache_key_deterministic(self):
        """Cache key is deterministic - same inputs produce same key."""
        key1 = _make_cache_key("test prompt", "system prompt")
        key2 = _make_cache_key("test prompt", "system prompt")

        assert key1 == key2

    def test_make_cache_key_unique_inputs(self):
        """Different inputs produce different keys."""
        key1 = _make_cache_key("prompt one", "system one")
        key2 = _make_cache_key("prompt two", "system two")

        assert key1 != key2

    def test_make_cache_key_prevents_collision(self):
        """Cache key uses SHA256 to prevent hash() collisions."""
        # Python's hash() can collide for different strings
        # SHA256 should not collide for these test cases
        test_cases = [
            ("test", "system"),
            ("test", "system "),  # trailing space
            ("test ", "system"),  # leading space in prompt
            ("", ""),
            ("a" * 1000, "b" * 1000),
        ]

        keys = [_make_cache_key(p, s) for p, s in test_cases]

        # All keys should be unique (64 hex chars = 32 bytes)
        assert len(set(keys)) == len(test_cases)
        assert all(len(k) == 64 for k in keys)

    def test_make_cache_key_with_none_system_prompt(self):
        """Cache key handles None system_prompt."""
        key_with_none = _make_cache_key("prompt", None)
        key_with_empty = _make_cache_key("prompt", "")

        assert key_with_none == key_with_empty
