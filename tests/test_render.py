"""Tests for render.py validation and schema."""

import pytest
from herold.render import validate_text, AnsageEntry, MAX_TEXT_LENGTH


class TestValidateText:
    """Tests for text length validation (DoS protection)."""

    def test_valid_text(self):
        """Normal text should pass validation."""
        text = "Hello, this is a normal announcement."
        assert validate_text(text) == text

    def test_empty_text(self):
        """Empty text should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_text("")

    def test_whitespace_only(self):
        """Whitespace-only text should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_text("   ")

    def test_text_too_long(self):
        """Text exceeding MAX_TEXT_LENGTH should raise ValueError."""
        long_text = "x" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError, match="too long"):
            validate_text(long_text)

    def test_text_at_max_length(self):
        """Text exactly at MAX_TEXT_LENGTH should pass."""
        text = "a" * MAX_TEXT_LENGTH
        assert validate_text(text) == text

    def test_text_not_string(self):
        """Non-string input should raise TypeError."""
        with pytest.raises(TypeError, match="Expected string"):
            validate_text(123)

    def test_text_none(self):
        """None input should raise TypeError."""
        with pytest.raises(TypeError, match="Expected string"):
            validate_text(None)


class TestAnsageEntry:
    """Tests for AnsageEntry dataclass and schema validation."""

    def test_valid_entry(self):
        """Valid entry should be created."""
        entry = AnsageEntry(
            id="welcome",
            text_de="Willkommen",
            text_en="Welcome"
        )
        assert entry.id == "welcome"
        assert entry.text_de == "Willkommen"
        assert entry.text_en == "Welcome"

    def test_missing_id(self):
        """Missing id should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid id"):
            AnsageEntry(id="", text_de="Hallo", text_en="Hello")

    def test_invalid_id_type(self):
        """Non-string id should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid id"):
            AnsageEntry(id=123, text_de="Hallo", text_en="Hello")

    def test_missing_text_de(self):
        """Missing text_de should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            AnsageEntry(id="test", text_de="", text_en="Hello")

    def test_missing_text_en(self):
        """Missing text_en should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            AnsageEntry(id="test", text_de="Hallo", text_en="")

    def test_text_too_long_de(self):
        """text_de exceeding MAX_TEXT_LENGTH should raise ValueError."""
        long_text = "x" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError, match="too long"):
            AnsageEntry(id="test", text_de=long_text, text_en="Hello")

    def test_text_too_long_en(self):
        """text_en exceeding MAX_TEXT_LENGTH should raise ValueError."""
        long_text = "x" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError, match="too long"):
            AnsageEntry(id="test", text_de="Hallo", text_en=long_text)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
