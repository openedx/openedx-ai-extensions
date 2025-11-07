"""
LLM Processing using LiteLLM for multiple providers
"""

import logging

from django.conf import settings
from litellm import responses
from openedx_ai_extensions.utils import _search_user_info_in_file, _update_file_with_user_info

logger = logging.getLogger(__name__)


class ResponsesProcessor:
    """Handles AI/LLM processing operations"""

    def __init__(self, config=None, user=None, unit_id=None):
        config = config or {}

        class_name = self.__class__.__name__
        self.config = config.get(class_name, {})
        self.user = user
        self.unit_id = unit_id

        self.config_profile = self.config.get("config", "default")

        # Extract API configuration once during initialization
        self.api_key = settings.AI_EXTENSIONS[self.config_profile]['API_KEY']
        self.model = settings.AI_EXTENSIONS[self.config_profile]['LITELLM_MODEL']
        self.timeout = settings.AI_EXTENSIONS[self.config_profile]['TIMEOUT']
        self.temperature = float(settings.AI_EXTENSIONS[self.config_profile]['TEMPERATURE'])
        self.max_tokens = settings.AI_EXTENSIONS[self.config_profile]['MAX_TOKENS']

        if not self.api_key:
            logger.error("AI API key not configured")

    def process(self, input_data):
        """Process based on configured function"""
        function_name = self.config.get("function", "explain_like_five")
        function = getattr(self, function_name)
        return function(input_data)

    def _extract_response_content(self, response):
        """Extract text content from LiteLLM response."""
        if not hasattr(response, "output") or not response.output:
            return ""

        for item in response.output:
            if getattr(item, "type", None) != "message":
                continue
            for content_item in item.content:
                if getattr(content_item, "type", None) == "output_text":
                    return content_item.text
        return ""

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
            }
            user_info = _search_user_info_in_file(self.user, self.unit_id)
            if user_info and "response_id" in user_info:
                completion_params["previous_response_id"] = user_info["response_id"]

            # Add optional parameters only if configured
            if self.temperature is not None:
                completion_params["temperature"] = self.temperature
            if self.max_tokens is not None:
                completion_params["max_tokens"] = self.max_tokens

            response = responses(**completion_params)

            response_id = getattr(response, "id", None)
            if response_id:
                _update_file_with_user_info(self.user, self.unit_id, {"response_id": response_id})

            content = self._extract_response_content(response)

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

            "Additionally, include at the end how many messages have been exchanged so far in this conversation."
        )

        result = self._call_responses_api(system_role, content_text)

        return result
