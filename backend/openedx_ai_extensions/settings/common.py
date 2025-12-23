"""
Common settings for the openedx_ai_extensions application.
"""

import logging
from pathlib import Path

from event_routing_backends.utils.settings import event_tracking_backends_config

from openedx_ai_extensions.xapi.constants import ALL_EVENTS

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

BASE_DIR = Path(__file__).resolve().parent.parent


def plugin_settings(settings):
    """
    Add plugin settings to main settings object.

    Args:
        settings (dict): Django settings object
    """

    if not hasattr(settings, "AI_EXTENSIONS_MCP_CONFIGS"):
        # Here we cannot update AI_EXTENSIONS_MCP_CONFIGS if we're already setting it with Tutor configs
        # because 'openedx-common-settings' will override it
        settings.AI_EXTENSIONS_MCP_CONFIGS = {}

    # -------------------------
    # Edxapp wrapper settings
    # -------------------------
    settings.CONTENT_LIBRARIES_MODULE_BACKEND = (
        "openedx_ai_extensions.edxapp_wrapper.backends.content_libraries_module_t_v1"
    )

    # -------------------------
    # Settings based config router
    # -------------------------

    if not hasattr(settings, "WORKFLOW_TEMPLATE_DIRS"):
        settings.WORKFLOW_TEMPLATE_DIRS = [
            BASE_DIR / "workflows" / "profiles",
        ]

    # -------------------------
    # ThreadedOrchestrator
    # -------------------------
    # This prevents context window from growing too large while maintaining conversation continuity
    if not hasattr(settings, "AI_EXTENSIONS_MAX_CONTEXT_MESSAGES"):
        settings.AI_EXTENSIONS_MAX_CONTEXT_MESSAGES = 3

    # -------------------------
    # Default field filters
    # -------------------------
    if not hasattr(settings, "AI_EXTENSIONS_FIELD_FILTERS"):
        settings.AI_EXTENSIONS_FIELD_FILTERS = DEFAULT_FIELD_FILTERS.copy()

    # -------------------------
    # xAPI Event Tracking
    # -------------------------
    # Whitelist AI workflow events for use with event routing backends xAPI backend.
    # If these settings don't already exist, it means event routing is not running.
    if not hasattr(settings, 'EVENT_TRACKING_BACKENDS_ALLOWED_XAPI_EVENTS'):
        settings.EVENT_TRACKING_BACKENDS_ALLOWED_XAPI_EVENTS = []
    if not hasattr(settings, 'EVENT_TRACKING_BACKENDS_ALLOWED_CALIPER_EVENTS'):
        settings.EVENT_TRACKING_BACKENDS_ALLOWED_CALIPER_EVENTS = []

    # Add all AI workflow events to the xAPI allowlist
    settings.EVENT_TRACKING_BACKENDS_ALLOWED_XAPI_EVENTS += ALL_EVENTS

    # Configure event tracking backends using the event routing backend utility
    # Only do this if EVENT_TRACKING_BACKENDS exists (i.e., we're in an Open edX environment, not tests)
    if hasattr(settings, 'EVENT_TRACKING_BACKENDS') and settings.EVENT_TRACKING_BACKENDS:
        settings.EVENT_TRACKING_BACKENDS.update(event_tracking_backends_config(
            settings,
            settings.EVENT_TRACKING_BACKENDS_ALLOWED_XAPI_EVENTS,
            settings.EVENT_TRACKING_BACKENDS_ALLOWED_CALIPER_EVENTS,
        ))
