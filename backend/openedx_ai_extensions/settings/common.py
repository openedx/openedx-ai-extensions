"""
Common settings for the openedx_ai_extensions application.
"""

import logging

logger = logging.getLogger(__name__)


DEFAULT_FIELD_FILTERS = {
    "allowed_fields": [
        "name",
        "display_name",
        "tags",
        "title",
        "format",
        "text",
        "type",
        "due",
        "source_file",
        "data",
        "graded",
    ],
    "allowed_field_substrings": [
        "description",
        "name",
    ],
}


def plugin_settings(settings):
    """
    Add plugin settings to main settings object.

    Args:
        settings (dict): Django settings object
    """
    settings.CONTENT_LIBRARIES_MODULE_BACKEND = (
        "openedx_ai_extensions.edxapp_wrapper.backends.content_libraries_module_t_v1"
    )

    # This prevents context window from growing too large while maintaining conversation continuity
    if not hasattr(settings, "AI_EXTENSIONS_MAX_CONTEXT_MESSAGES"):
        settings.AI_EXTENSIONS_MAX_CONTEXT_MESSAGES = 3

    # -------------------------
    # Default field filters
    # -------------------------
    if not hasattr(settings, "AI_EXTENSIONS_FIELD_FILTERS"):
        settings.AI_EXTENSIONS_FIELD_FILTERS = DEFAULT_FIELD_FILTERS.copy()
