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

    if hasattr(settings, "AI_EXTENSIONS"):
        first_key = next(iter(settings.AI_EXTENSIONS))

        # Make first profile also default
        settings.AI_EXTENSIONS = {
            "default": {**settings.AI_EXTENSIONS[first_key]},
            **settings.AI_EXTENSIONS,
        }
