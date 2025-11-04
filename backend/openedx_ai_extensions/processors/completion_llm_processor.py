"""
LLM Processing using LiteLLM for multiple providers
"""

import logging

from django.conf import settings
from litellm import completion

logger = logging.getLogger(__name__)


class CompletionLLMProcessor:
    """Handles AI/LLM processing operations"""

    def __init__(self, config=None):
        config = config or {}

        class_name = self.__class__.__name__
        self.config = config.get(class_name, {})

        self.config_profile = self.config.get("config", "default")
        self.mcp_config = self.config.get("mcp_config", {})

        # Extract API configuration once during initialization
        self.api_key = settings.AI_EXTENSIONS[self.config_profile]['API_KEY']
        self.model = settings.AI_EXTENSIONS[self.config_profile]['LITELLM_MODEL']
        self.timeout = settings.AI_EXTENSIONS[self.config_profile]['TIMEOUT']
        self.temperature = settings.AI_EXTENSIONS[self.config_profile]['TEMPERATURE']
        self.max_tokens = settings.AI_EXTENSIONS[self.config_profile]['MAX_TOKENS']

        if not self.api_key:
            logger.error("AI API key not configured")

    def process(self, input_data):
        """Process based on configured function"""
        function_name = self.config.get("function", "summarize_content")
        function = getattr(self, function_name)
        return function(input_data)

    def _call_completion_api(self, system_role, user_content):
        """
        General method to call LiteLLM completion API
        Handles configuration and returns standardized response
        """
        try:
            if not self.api_key:
                return {"error": "AI API key not configured"}

            # Build completion parameters
            completion_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_role},
                    {"role": "user", "content": user_content},
                ],
                "api_key": self.api_key,
                "tools": [
                    {
                        "type": "mcp",
                        "server_label": self.mcp_config.get("server_label", "openedx_server"),
                        "server_url": self.mcp_config.get("server_url", ""),
                        "require_approval": self.mcp_config.get("require_approval", "never"),
                    },
                ],
            }

            # Add optional parameters only if configured
            if self.temperature is not None:
                completion_params["temperature"] = self.temperature
            if self.max_tokens is not None:
                completion_params["max_tokens"] = self.max_tokens
            if self.timeout is not None:
                completion_params["timeout"] = self.timeout

            response = completion(**completion_params)
            content = response.choices[0].message.content

            return {
                "response": content,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "model_used": self.model,
                "status": "success",
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error calling LiteLLM: {e}")
            return {"error": f"AI processing failed: {str(e)}"}

    def summarize_content(self, content_text, user_query=""):  # pylint: disable=unused-argument
        """Summarize content using LiteLLM"""
        system_role = (
            "You are an academic assistant which helps students briefly "
            "summarize a unit of content of an online course."
        )

        result = self._call_completion_api(system_role, content_text)

        return result

    def explain_like_five(self, content_text, user_query=""):  # pylint: disable=unused-argument
        """
        Explain content in very simple terms, like explaining to a 5-year-old
        Short, simple language that anyone can understand
        """
        system_role = (
            "You are a friendly teacher who explains things to young children. "
            "Explain the content in very simple words, like you're talking to a 5-year-old. "
            "Use short sentences, simple words, and make it fun and easy to understand. "
            "Keep your explanation very brief - no more than 3-4 simple sentences."
        )

        result = self._call_completion_api(system_role, content_text)

        return result
