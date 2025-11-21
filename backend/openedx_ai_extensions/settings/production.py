"""
Production settings for the openedx_ai_extensions application.
"""

from openedx_ai_extensions.settings.common import plugin_settings as common_settings


def plugin_settings(settings):
    """
    Set up production-specific settings.

    Args:
        settings (dict): Django settings object
    """
    # Apply common settings
    common_settings(settings)
    LITELLM_BASE = {
        "TIMEOUT": 600,  # Request timeout in seconds
        "MAX_TOKENS": 4096,  # Max tokens per request
        "TEMPERATURE": 0.7,  # Response randomness (0-1)
    }

    if hasattr(settings, "AI_EXTENSIONS"):
        first_key = next(iter(settings.AI_EXTENSIONS))

        # Merge base config into all profiles
        merged_extensions = {}
        for key, config in settings.AI_EXTENSIONS.items():
            merged_extensions[key] = {**LITELLM_BASE, **config}

        # Make first profile also default
        settings.AI_EXTENSIONS = {
            "default": {**LITELLM_BASE, **settings.AI_EXTENSIONS[first_key]},
            **merged_extensions,
        }
