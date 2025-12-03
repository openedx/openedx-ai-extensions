"""
LLM Processing using LiteLLM for multiple providers
"""

import logging

from litellm import completion

from openedx_ai_extensions.processors.litellm_base_processor import LitellmProcessor

logger = logging.getLogger(__name__)


class LLMProcessor(LitellmProcessor):
    """Handles AI/LLM processing operations using completion API"""

    def process(self, *args, **kwargs):
        """Process based on configured function"""
        # Accept flexible arguments to match base class signature
        input_data = args[0] if len(args) > 0 else kwargs.get("input_data")

        function_name = self.config.get("function", "summarize_content")
        stream = self.config.get("stream", False)
        function = getattr(self, function_name)
        return function(input_data, stream=stream)

    def _handle_streaming_completion(self, response):
        """Handles the streaming logic, yielding byte strings."""
        try:
            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                if content:
                    yield content.encode('utf-8')
        except Exception as e:  # pylint: disable=broad-exception-caught
            error_message = f"Error during AI streaming: {e}"
            logger.error(error_message, exc_info=True)
            yield f"\n[AI Error: {e}]".encode('utf-8')

    def _handle_non_streaming_completion(self, response):
        """Handles the non-streaming logic, returning a response dict."""
        content = response.choices[0].message.content
        return {
            "response": content,
            "tokens_used": response.usage.total_tokens if response.usage else 0,
            "model_used": self.model,
            "status": "success",
        }

    def _call_completion_api(self, system_role, user_content, stream):
        """
        General method to call LiteLLM completion API.
        Returns either a generator (if stream=True) or a response dict.
        """
        if not self.api_key:
            # Return an error dictionary if the API key is not configured
            return {"error": "AI API key not configured"}

        # Build completion parameters
        completion_params = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_role},
                {"role": "user", "content": user_content},
            ],
            "api_key": self.api_key,
            "stream": stream,
        }
        # Add optional extra parameters
        completion_params.update(self.extra_params)

        try:
            # 1. Call the LiteLLM API
            response = completion(**completion_params)

            # 2. Handle streaming response (Generator)
            if stream:
                return self._handle_streaming_completion(response)  # Return the generator object
            else:
                return self._handle_non_streaming_completion(response)  # Return the dictionary

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Catch errors that occur during the INITIAL API call (before streaming starts)
            error_message = f"Error during initial AI completion call: {e}"
            logger.error(error_message, exc_info=True)
            # Always return a dictionary error in this outer block
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
