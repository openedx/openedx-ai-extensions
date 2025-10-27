"""
Common settings for the openedx_ai_extensions application.
"""
import os
import logging
from copy import deepcopy

logger = logging.getLogger(__name__)


def plugin_settings(settings):  # pylint: disable=unused-argument
    """
    Add plugin settings to main settings object.

    Args:
        settings (dict): Django settings object
    """
    CONFIG_DEFAULTS = {
        "default": {
            "API_KEY": "put_your_api_key_here",
            "LITELLM_MODEL": "gpt-5-mini",
            "TEMPERATURE": 1,
        }
    }
    config = deepcopy(CONFIG_DEFAULTS)
    if hasattr(settings, "OPENEDX_AI_EXTENSIONS"):
        for section, values in settings.OPENEDX_AI_EXTENSIONS.items():
          if section in config:
              logger.warning(f"OpenedX AI Extensions settings: {settings.OPENEDX_AI_EXTENSIONS}")
              config[section].update(values)
          else:
              config[section] = values
    settings.OPENEDX_AI_EXTENSIONS = config
