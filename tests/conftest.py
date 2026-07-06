"""Pytest configuration and fixtures. Mock heavy dependencies for testing."""

import sys
from unittest.mock import MagicMock

# Mock qwen_tts before any imports
sys.modules['qwen_tts'] = MagicMock()
