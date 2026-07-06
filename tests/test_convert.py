"""Tests for convert.py validation and path safety."""

import pytest
import sys
from pathlib import Path

# Add work dir to path
sys.path.insert(0, str(Path(__file__).parent.parent / "work"))

from convert import validate_filename_stem


class TestValidateFilenameStem:
    """Tests for filename stem validation (Path Traversal protection)."""

    def test_valid_stem_alphanumeric(self):
        """Alphanumeric filename should pass."""
        assert validate_filename_stem("welcome_en") == "welcome_en"

    def test_valid_stem_with_underscore(self):
        """Filename with underscores should pass."""
        assert validate_filename_stem("my_audio_file_01") == "my_audio_file_01"

    def test_valid_stem_with_hyphen(self):
        """Filename with hyphens should pass."""
        assert validate_filename_stem("audio-file-01") == "audio-file-01"

    def test_valid_stem_mixed(self):
        """Mixed alphanumeric, underscore, hyphen should pass."""
        assert validate_filename_stem("file_name-02") == "file_name-02"

    def test_path_traversal_attempt(self):
        """Path traversal attempt should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid filename stem"):
            validate_filename_stem("../../../etc/passwd")

    def test_path_traversal_dots(self):
        """Dots in path should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid filename stem"):
            validate_filename_stem("file..wav")

    def test_absolute_path(self):
        """Absolute path should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid filename stem"):
            validate_filename_stem("/etc/passwd")

    def test_special_characters(self):
        """Special characters should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid filename stem"):
            validate_filename_stem("file@name")

    def test_spaces(self):
        """Spaces should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid filename stem"):
            validate_filename_stem("file name")

    def test_empty_string(self):
        """Empty string should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid filename stem"):
            validate_filename_stem("")

    def test_shell_command_injection(self):
        """Shell metacharacters should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid filename stem"):
            validate_filename_stem("file; rm -rf /")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
