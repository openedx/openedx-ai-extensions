"""
Common settings for the openedx_ai_extensions application.
"""

import logging

logger = logging.getLogger(__name__)


def plugin_settings(settings):
    """
    Add plugin settings to main settings object.

    Args:
        settings (dict): Django settings object
    """
    settings.CONTENT_LIBRARIES_MODULE_BACKEND = "openedx_ai_extensions.edxapp_wrapper.backends.content_libraries_module_t_v1"

    if not hasattr(settings, "AI_EXTENSIONS_MODEL_PROXY"):
        settings.AI_EXTENSIONS_MODEL_PROXY = [
            {"location_regex": ".*", "file": "configs/default.json"},
        ]

    # This prevents context window from growing too large while maintaining conversation continuity
    if not hasattr(settings, "AI_EXTENSIONS_MAX_CONTEXT_MESSAGES"):
        settings.AI_EXTENSIONS_MAX_CONTEXT_MESSAGES = 3
