"""
Settings for live LLM provider integration tests.

Inherits from test_settings and overrides AI_EXTENSIONS with env-var-backed
credentials so tests can call real LLM APIs.

Usage:
    OPENAI_API_KEY=sk-... ANTHROPIC_API_KEY=sk-ant-... GEMINI_API_KEY=AIza... \
    DJANGO_SETTINGS_MODULE=integration_test_settings \
    pytest tests/integration/ -m live_llm -v
"""

import os

from openedx_ai_extensions.settings.common import (
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OPENAI_MODEL,
)
from test_settings import *  # noqa: F401, F403

AI_EXTENSIONS = {
    "test_openai": {
        "MODEL": DEFAULT_OPENAI_MODEL,
        "API_KEY": os.environ.get("OPENAI_API_KEY", ""),
        "TIMEOUT": 30,
        "MAX_TOKENS": 2000,
    },
    "test_anthropic": {
        "MODEL": DEFAULT_ANTHROPIC_MODEL,
        "API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
        "TIMEOUT": 30,
        "MAX_TOKENS": 2000,
    },
    "test_gemini": {
        "MODEL": DEFAULT_GEMINI_MODEL,
        "API_KEY": os.environ.get("GEMINI_API_KEY", ""),
        "TIMEOUT": 30,
        "MAX_TOKENS": 2000,
    },
}
