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

        # Extract API configuration once during initialization
        self.api_key = settings.AI_EXTENSIONS[self.config_profile]["API_KEY"]
        self.model = settings.AI_EXTENSIONS[self.config_profile]["LITELLM_MODEL"]
        self.timeout = settings.AI_EXTENSIONS[self.config_profile]["TIMEOUT"]
        self.temperature = settings.AI_EXTENSIONS[self.config_profile]["TEMPERATURE"]
        self.max_tokens = settings.AI_EXTENSIONS[self.config_profile]["MAX_TOKENS"]

        if not self.api_key:
            logger.error("AI API key not configured")

    def process(self, *args, **kwargs):
        """Process based on configured function - must be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement process method")
