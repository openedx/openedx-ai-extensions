"""
Settings for live LLM provider integration tests.

Inherits from test_settings and overrides AI_EXTENSIONS with env-var-backed
credentials so tests can call real LLM APIs.

Usage:
    OPENAI_API_KEY=sk-... ANTHROPIC_API_KEY=sk-ant-... \
    DJANGO_SETTINGS_MODULE=integration_test_settings \
    pytest tests/integration/ -m live_llm -v
"""

import os

from test_settings import *  # noqa: F401, F403

AI_EXTENSIONS = {
    "test_openai": {
        "MODEL": "openai/gpt-4.1-mini",
        "API_KEY": os.environ.get("OPENAI_API_KEY", ""),
        "TIMEOUT": 30,
        "MAX_TOKENS": 2000,
        "TEMPERATURE": 0.3,
    },
    "test_anthropic": {
        "MODEL": "anthropic/claude-haiku-4-5",
        "API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
        "TIMEOUT": 30,
        "MAX_TOKENS": 2000,
        "TEMPERATURE": 0.3,
    },
}
