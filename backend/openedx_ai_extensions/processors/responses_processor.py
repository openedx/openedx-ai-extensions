"""
LLM Processing using LiteLLM for multiple providers
"""

import logging

from django.conf import settings
from litellm import responses

logger = logging.getLogger(__name__)


class ResponsesProcessor:
    """Handles AI/LLM processing operations"""

    def __init__(self, config=None, user_session=None):
        config = config or {}

        class_name = self.__class__.__name__
        self.config = config.get(class_name, {})
        self.user_session = user_session

        self.config_profile = self.config.get("config", "default")

        # Extract API configuration once during initialization
        self.api_key = settings.AI_EXTENSIONS[self.config_profile]['API_KEY']
        self.model = settings.AI_EXTENSIONS[self.config_profile]['LITELLM_MODEL']
        self.timeout = settings.AI_EXTENSIONS[self.config_profile]['TIMEOUT']
        self.temperature = float(settings.AI_EXTENSIONS[self.config_profile]['TEMPERATURE'])
        self.max_tokens = settings.AI_EXTENSIONS[self.config_profile]['MAX_TOKENS']

        if not self.api_key:
            logger.error("AI API key not configured")

    def process(self, context, input_data):
        """Process based on configured function"""
        function_name = self.config.get("function", "explain_like_five")
        function = getattr(self, function_name)
        return function(context, input_data)

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

    def _call_responses_api(self, system_role=None, context=None, user_query=None):
        """
        General method to call LiteLLM completion API
        Handles configuration and returns standardized response
        """
        try:
            if not self.api_key:
                return {"error": "AI API key not configured"}

            if self.user_session and self.user_session.last_response_id and not user_query:
                return {"error": "No user query provided for ongoing session"}

            if not self.user_session or not self.user_session.last_response_id and not system_role:
                return {"error": "No system role provided for new session"}

            # Build completion parameters
            completion_params = {
                "model": self.model,
                "api_key": self.api_key,
            }
            if self.user_session and self.user_session.last_response_id:
                completion_params["previous_response_id"] = self.user_session.last_response_id
                completion_params["input"] = [
                  {"role": "user", "content": user_query}
                ]
            else:
                completion_params["input"] = [
                  {"role": "system", "content": system_role},
                  {"role": "system", "content": context}
                ]

            # Add optional parameters only if configured
            if self.temperature is not None:
                completion_params["temperature"] = self.temperature
            if self.max_tokens is not None:
                completion_params["max_tokens"] = self.max_tokens

            response = responses(**completion_params)

            response_id = getattr(response, "id", None)
            if response_id:
                self.user_session.last_response_id = response_id
                self.user_session.save()

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

    def chat_with_context(self, context, user_query=None):  # pylint: disable=unused-argument
        """
        Chat with Context given from OpenEdx course content
        """

        system_role = (
            "Your're a helpful AI assistant integrated into an OpenEdX course platform. "
            "You're running as a chatbot to assist users with their questions based on the provided course content. "
        )

        if user_query:
            return self._call_responses_api(user_query=user_query)

        return self._call_responses_api(system_role, context)
