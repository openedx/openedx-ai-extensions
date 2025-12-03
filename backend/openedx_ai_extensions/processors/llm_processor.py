"""
LLM Processing using LiteLLM for multiple providers
"""

import logging

from litellm import completion, responses

from openedx_ai_extensions.processors.litellm_base_processor import LitellmProcessor

logger = logging.getLogger(__name__)


class LLMProcessor(LitellmProcessor):
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
            }

            # Add optional parameters only if configured
            completion_params.update(self.extra_params)

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

    def _call_responses_api(self, system_role, user_content, previous_response_id=None):
        """
        General method to call LiteLLM responses API for threaded conversations
        Handles configuration and returns standardized response with thread tracking

        Args:
            system_role: System role message defining assistant behavior
            user_content: User message or initial context
            previous_response_id: Optional ID of previous response to continue thread

        Returns:
            dict: Standardized response with content, tokens_used, model_used, response_id, and status
        """
        try:
            if not self.api_key:
                return {"error": "AI API key not configured"}

            # Build completion parameters
            completion_params = {
                "model": self.model,
                "api_key": self.api_key,
            }

            # If continuing an existing thread
            if previous_response_id:
                completion_params["previous_response_id"] = previous_response_id
                completion_params["input"] = [{"role": "user", "content": user_content}]
            else:
                # Initialize new thread with system role and context
                completion_params["input"] = [
                    {"role": "system", "content": system_role},
                    {"role": "system", "content": user_content},
                ]

            # Add optional parameters only if configured
            completion_params.update(self.extra_params)

            response = responses(**completion_params)

            # Extract content from response
            content = self._extract_response_content(response)
            response_id = getattr(response, "id", None)

            return {
                "response": content,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "model_used": self.model,
                "response_id": response_id,
                "status": "success",
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error calling LiteLLM responses API: {e}")
            return {"error": f"AI processing failed: {str(e)}"}

    def _extract_response_content(self, response):
        """
        Extract text content from LiteLLM response object.

        Args:
            response: Response object from LiteLLM responses API

        Returns:
            str: Extracted text content
        """
        if not hasattr(response, "output") or not response.output:
            return ""

        for item in response.output:
            if getattr(item, "type", None) != "message":
                continue
            for content_item in item.content:
                if getattr(content_item, "type", None) == "output_text":
                    return content_item.text
        return ""

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

    def openai_hello(self, content_text, user_query=""):  # pylint: disable=unused-argument
        """Simple test function to call OpenAI API via LiteLLM"""
        system_role = "Greet the user and say hello world outlining which Llm model is being used!"
        result = self._call_completion_api(system_role, content_text)

        return result

    def anthropic_hello(self, content_text, user_query=""):  # pylint: disable=unused-argument
        """Simple test function to call Anthropic API via LiteLLM"""
        system_role = "Greet the user and say hello world outlining which Llm model is being used!"

        result = self._call_completion_api(system_role, content_text)

        return result

    def roll_me_dice(self, content_text, user_query=""):  # pylint: disable=unused-argument
        """
        Explain content in very simple terms, like explaining to a 5-year-old
        Short, simple language that anyone can understand
        """
        system_role = (
            "Give me a dice roll"
        )

        result = self._call_responses_api(system_role, content_text)

        return result