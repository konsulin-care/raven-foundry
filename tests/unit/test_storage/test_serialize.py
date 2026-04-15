"""Unit tests for serialize_f32 function."""

from raven.storage import serialize_f32


class TestSerializeF32:
    """Tests for serialize_f32 function."""

    def test_serialize_f32_384_dimensions(self):
        """serialize_f32 correctly serializes 384-dimensional vector."""
        vector = [0.1] * 384
        result = serialize_f32(vector)

        assert isinstance(result, bytes)

    def test_serialize_f32_output_length(self):
        """serialize_f32 outputs correct byte length for 384-dim vector."""
        vector = [0.1] * 384
        result = serialize_f32(vector)

        # Each float is 4 bytes (float32), so 384 * 4 = 1536 bytes
        expected_length = 384 * 4
        assert len(result) == expected_length

    def test_serialize_f32_custom_dimensions(self):
        """serialize_f32 handles different vector dimensions."""
        vector = [0.5, 0.3, 0.2, 0.1]
        result = serialize_f32(vector)

        expected_length = 4 * 4  # 4 floats * 4 bytes each
        assert len(result) == expected_length

    def test_serialize_f32_zero_values(self):
        """serialize_f32 correctly serializes zeros."""
        vector = [0.0] * 384
        result = serialize_f32(vector)

        assert isinstance(result, bytes)
        assert len(result) == 384 * 4

    def test_serialize_f32_negative_values(self):
        """serialize_f32 correctly serializes negative floats."""
        vector = [-0.5, -0.3, 0.0, 0.3]
        result = serialize_f32(vector)

        assert isinstance(result, bytes)
        assert len(result) == 16  # 4 floats * 4 bytes
