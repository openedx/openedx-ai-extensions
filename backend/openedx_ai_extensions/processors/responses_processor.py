"""
Responses processor for threaded AI conversations using LiteLLM
"""

import logging

from litellm import responses

from openedx_ai_extensions.processors.litellm_base_processor import LitellmProcessor

logger = logging.getLogger(__name__)


class ResponsesProcessor(LitellmProcessor):
    """Handles threaded AI conversations using LiteLLM responses API"""

    def process(self, context, input_data):
        """Process based on configured function"""
        function_name = self.config.get("function", "chat_with_context")
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

    def _build_completion_params(self, system_role=None, context=None, user_query=None):
        """
        Build completion parameters for LiteLLM responses API.

        Args:
            system_role: System role message for initializing thread
            context: Context message for initializing thread
            user_query: User query for continuing existing thread

        Returns:
            dict: Completion parameters ready for responses() call
        """
        completion_params = {
            "model": self.model,
            "api_key": self.api_key,
        }

        # If we have an existing thread, continue it with user query
        if self.user_session and self.user_session.remote_response_id:
            completion_params["previous_response_id"] = (
                self.user_session.remote_response_id
            )
            completion_params["input"] = [{"role": "user", "content": user_query}]
        else:
            # Initialize new thread with system role and context
            completion_params["input"] = [
                {"role": "system", "content": system_role},
                {"role": "system", "content": context},
            ]

        # Add optional parameters only if configured
        if self.temperature is not None:
            completion_params["temperature"] = self.temperature
        if self.max_tokens is not None:
            completion_params["max_tokens"] = self.max_tokens

        return completion_params

    def _call_responses_wrapper(self, completion_params):
        """
        Wrapper around LiteLLM responses() call that handles the API call and session updates.

        Args:
            completion_params: Parameters for the responses() call

        Returns:
            dict: Standardized response with content, tokens_used, model_used, and status
        """
        try:
            if not self.api_key:
                return {"error": "AI API key not configured"}

            response = responses(**completion_params)

            response_id = getattr(response, "id", None)
            content = self._extract_response_content(response)

            # Update session with response ID for threading
            if response_id:
                self.user_session.remote_response_id = response_id
                self.user_session.save()

            return {
                "response": content,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "model_used": self.model,
                "status": "success",
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error calling LiteLLM: {e}")
            return {"error": f"AI processing failed: {str(e)}"}

    def initialize_thread(self, system_role, context):
        """
        Initialize a new conversation thread with system role and context.

        Args:
            system_role: System role message defining assistant behavior
            context: Initial context for the conversation

        Returns:
            dict: Response from the API
        """
        completion_params = self._build_completion_params(
            system_role=system_role, context=context
        )
        return self._call_responses_wrapper(completion_params)

    def continue_thread(self, user_query):
        """
        Continue an existing conversation thread with a user query.
        Requires user_session with remote_response_id.

        Args:
            user_query: User's question or message

        Returns:
            dict: Response from the API
        """
        completion_params = self._build_completion_params(user_query=user_query)
        return self._call_responses_wrapper(completion_params)

    def chat_with_context(self, context, user_query=None):
        """
        Chat with context given from OpenEdx course content.
        Either initializes a new thread or continues an existing one.

        Args:
            context: Course content context
            user_query: Optional user query to continue conversation

        Returns:
            dict: Response from the API
        """
        system_role = (
            "Your're a helpful AI assistant integrated into an OpenEdX course platform. "
            "You're running as a chatbot to assist users with their questions based on the provided course content. "
        )

        if self.user_session and self.user_session.remote_response_id:
            return self.continue_thread(user_query)

        return self.initialize_thread(system_role, context)
