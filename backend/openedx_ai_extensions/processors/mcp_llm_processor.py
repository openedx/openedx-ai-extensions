"""
LLM Processing using LiteLLM for multiple providers
"""

import logging

from litellm import responses

logger = logging.getLogger(__name__)


class MCPLLMProcessor:
    """Handles AI/LLM processing operations"""

    def __init__(self, config=None):
        config = config or {}

        class_name = self.__class__.__name__
        self.config = config.get(class_name, {})

        # Extract API configuration once during initialization
        self.api_key = self.config.get("api_key")
        self.model = self.config.get("model")
        self.temperature = self.config.get("temperature")  # No default
        self.max_tokens = self.config.get("max_tokens")  # No default
        self.mcp_config = self.config.get("mcp_config", {})

        if not self.api_key:
            logger.error("AI API key not configured")

    def process(self, input_data):
        """Process based on configured function"""
        function_name = self.config.get("function", "summarize_content")
        function = getattr(self, function_name)
        return function(input_data)

    def _call_responses_api(self, system_role, context):
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
                "input": [
                    {"role": "system", "content": system_role},
                    {"role": "system", "content": context}
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

            response = responses(**completion_params)
            if hasattr(response, "output") and response.output:
                for item in response.output:
                    # Find the assistant message
                    if getattr(item, "type", None) == "message":
                        for c in item.content:
                            if getattr(c, "type", None) == "output_text":
                                content = c.text  # ✅ This is your clean text
            else:
                content = ""

            return {
                "response": content,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "model_used": self.model,
                "status": "success",
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error calling LiteLLM: {e}")
            return {"error": f"AI processing failed: {str(e)}"}

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

        result = self._call_responses_api(system_role, content_text)

        return result
