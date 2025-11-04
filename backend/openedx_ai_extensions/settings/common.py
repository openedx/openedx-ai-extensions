"""
Common settings for the openedx_ai_extensions application.
"""
import logging

logger = logging.getLogger(__name__)


def plugin_settings(settings):  # pylint: disable=unused-argument
    """
    Add plugin settings to main settings object.

    Args:
        settings (dict): Django settings object
    """
