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
        self.config = config.get(self.__class__.__name__, {})
        self.user_session = user_session

        provider_spec = self.config.get("provider", "default")
        self.config_profile = provider_spec
        if isinstance(provider_spec, str):
            providers = getattr(settings, "AI_EXTENSIONS", {})
            provider = providers.get(provider_spec)

            if provider is None and provider_spec != "default":
                raise ValueError(f"Unknown AI_EXTENSIONS profile '{provider_spec}'")

            provider = provider or {}
        else:
            raise TypeError("`provider` must be a string")

        options = self.config.get("options", {}) or {}

        base_params = {k.lower(): v for k, v in provider.items()}
        override_params = {k.lower(): v for k, v in options.items()}
        self.extra_params = {**base_params, **override_params}

        model = self.extra_params.get("model")
        if not isinstance(model, str) or "/" not in model:
            raise ValueError(
                "MODEL must be defined and have the format 'provider/model_name'. "
                "e.g., 'openai/gpt-4'"
            )

        self.provider = model.split("/")[0]
        self.custom_prompt = self._load_prompt()
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
                for key, value in getattr(settings, 'AI_EXTENSIONS_MCP_CONFIGS', {}).items()
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

    def _load_prompt(self):
        """
        Load prompt from PromptTemplate model or inline config.

        Priority:
        1. prompt_template: Load by slug or UUID (unified key)
        2. prompt: Use inline prompt (backwards compatibility)
        3. None: No custom prompt

        Returns:
            str or None: The prompt text
        """
        from openedx_ai_extensions.models import PromptTemplate  # pylint: disable=import-outside-toplevel

        # Try loading from PromptTemplate (handles both slug and UUID)
        template_id = self.config.get("prompt_template")
        if template_id:
            prompt = PromptTemplate.load_prompt(template_id)
            if prompt:
                return prompt
        # Fall back to inline prompt (backwards compatibility)
        return self.config.get("prompt")

    def process(self, *args, **kwargs):
        """Process based on configured function - must be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement process method")

    def get_provider(self):
        """Return the configured provider"""
        return self.provider
