"""
Base processor for LiteLLM-based processors
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class LitellmProcessor:
    """Base class for processors that use LiteLLM for AI/LLM operations"""

    def __init__(self, config=None, user_session=None):
        config = config or {}

        class_name = self.__class__.__name__
        self.config = config.get(class_name, {})
        self.user_session = user_session

        self.config_profile = self.config.get("config", "default")

        if "MODEL" not in settings.AI_EXTENSIONS[self.config_profile]:
            raise ValueError(
                f"AI_EXTENSIONS config '{self.config_profile}' missing 'MODEL' setting."
            )
        try:
            self.provider = settings.AI_EXTENSIONS[self.config_profile].get("MODEL").split("/")[0]
        except Exception as exc:
            raise ValueError(
                "MODEL setting must be in the format 'provider/model_name'. e.g., 'openai/gpt-4'"
            ) from exc

        self.extra_params = {}
        for key, value in settings.AI_EXTENSIONS[self.config_profile].items():
            self.extra_params[key.lower()] = value

    def process(self, *args, **kwargs):
        """Process based on configured function - must be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement process method")

    def get_provider(self):
        """Return the configured provider"""
        return self.provider
