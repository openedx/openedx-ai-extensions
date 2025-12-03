"""
LLM Processing using LiteLLM for multiple providers
"""

import logging

from litellm import completion

from openedx_ai_extensions.processors.litellm_base_processor import LitellmProcessor

logger = logging.getLogger(__name__)


class CompletionProcessor(LitellmProcessor):
    """Handles AI/LLM processing operations using completion API"""

    def process(self, *args, **kwargs):
        """Process based on configured function"""
        # Accept flexible arguments to match base class signature
        input_data = args[0] if len(args) > 0 else kwargs.get("input_data")

        function_name = self.config.get("function", "summarize_content")
        function = getattr(self, function_name)
        return function(input_data)

    def _call_completion_api(self, system_role, user_content):
        """
        General method to call LiteLLM completion API
        Handles configuration and returns standardized response
        """
        try:
            # Build completion parameters
            completion_params = {
                "messages": [
                    {"role": "system", "content": system_role},
                    {"role": "user", "content": user_content},
                ],
            }

            # Add optional parameters only if configured
            completion_params.update(self.extra_params)

            response = completion(**completion_params)
            content = response.choices[0].message.content

            return {
                "response": content,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "model_used": self.extra_params.get("model", "unknown"),
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

    def greet_from_llm(self, content_text, user_query=""):  # pylint: disable=unused-argument
        """Simple test to greet from the LLM and mention which model is being used."""
        system_role = "Greet the user and say hello world outlining which Llm model is being used!"
        result = self._call_completion_api(system_role, content_text)

        return result
