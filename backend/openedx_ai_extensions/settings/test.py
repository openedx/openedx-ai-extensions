"""
Test settings for the openedx_ai_extensions application.
"""

from openedx_ai_extensions.settings.common import plugin_settings as common_settings


def plugin_settings(settings):
    """
    Set up test-specific settings.

    Args:
        settings (dict): Django settings object
    """

    # Apply common settings
    common_settings(settings)
