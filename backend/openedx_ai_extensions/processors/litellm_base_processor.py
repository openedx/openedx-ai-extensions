"""
Base processor for LiteLLM-based processors
"""

import logging

from django.conf import settings

from openedx_ai_extensions.functions.decorators import TOOLS_SCHEMA

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

        self.stream = self.config.get("stream", False)

        enabled_tools = self.config.get("enabled_tools", [])
        if enabled_tools:
            functions_schema_filtered = [
                schema
                for name, schema in TOOLS_SCHEMA.items()
                if name in enabled_tools or "__all__" in enabled_tools
            ]
            if functions_schema_filtered:
                self.extra_params["tools"] = functions_schema_filtered

        if self.stream and "tools" in self.extra_params:
            logger.warning("Streaming responses with tools is not supported; disabling streaming.")
            self.stream = False

        self.mcp_configs = {}
        allowed_mcp_configs = self.config.get("mcp_configs", [])
        if allowed_mcp_configs:
            self.mcp_configs = {
                key: value
                for key, value in settings.AI_EXTENSIONS_MCP_CONFIGS.items()
                if key in allowed_mcp_configs
            }
            self.extra_params["tools"] = [
                {
                    "type": "mcp",
                    "server_label": key,
                    **value,
                }
                for key, value in self.mcp_configs.items()
            ]

    def process(self, *args, **kwargs):
        """Process based on configured function - must be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement process method")

    def get_provider(self):
        """Return the configured provider"""
        return self.provider
