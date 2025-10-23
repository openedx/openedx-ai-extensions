"""
Common settings for the openedx_ai_extensions application.
"""
import os


def plugin_settings(settings):  # pylint: disable=unused-argument
    """
    Add plugin settings to main settings object.

    Args:
        settings (dict): Django settings object
    """
    if not hasattr(settings, "OPENEDX_AI_EXTENSIONS"):
        settings.OPENEDX_AI_EXTENSIONS = os.getenv("OPENEDX_AI_EXTENSIONS", default={
            "default": {
                "API_KEY": "",
                "LITELLM_MODEL": "gpt-5-mini",
                "TEMPERATURE": 1,
            }
        })
