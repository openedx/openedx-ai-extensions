"""
LLM Processing using LiteLLM for multiple providers
"""

import logging
import time
from types import GeneratorType

from litellm import completion

from openedx_ai_extensions.processors.litellm_base_processor import LitellmProcessor

logger = logging.getLogger(__name__)


def is_generator(result):
    """
    Check if the given object is a generator.

    Args:
        result (Any): The object to check.

    Returns:
        bool: True if the object is an instance of GeneratorType, False otherwise.
    """
    return isinstance(result, GeneratorType)


class LLMProcessor(LitellmProcessor):
    """Handles AI/LLM processing operations using completion API"""

    def process(self, *args, **kwargs):
        """Process based on configured function"""
        # Accept flexible arguments to match base class signature
        input_data = args[0] if len(args) > 0 else kwargs.get("input_data")

        function_name = self.config.get("function", "summarize_content")
        function = getattr(self, function_name)
        return function(input_data)

    def _handle_streaming_completion(self, response):
        """Stream with chunk buffering (more natural UI speed)."""
        total_tokens = None
        buffer = []
        last_flush = time.time()

        BUFFER_SIZE = 60  # min characters before flush
        FLUSH_INTERVAL = 0.05

        try:
            for chunk in response:
                if hasattr(chunk, "usage") and chunk.usage:
                    total_tokens = chunk.usage.total_tokens

                content = chunk.choices[0].delta.content or ""
                if content:
                    buffer.append(content)

                now = time.time()

                # Flush if large enough OR enough time has passed
                if len("".join(buffer)) >= BUFFER_SIZE or (now - last_flush) >= FLUSH_INTERVAL:
                    if buffer:
                        yield "".join(buffer).encode("utf-8")
                        buffer = []
                    last_flush = now

            # Flush any remaining buffered content at the end
            if buffer:
                yield "".join(buffer).encode("utf-8")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error during AI streaming: {e}", exc_info=True)
            yield f"\n[AI Error: {e}]".encode("utf-8")
            return

        # Log tokens at end
        if total_tokens is not None:
            logger.info(f"[LLM STREAM] Tokens used: {total_tokens}")
        else:
            logger.info("[LLM STREAM] Tokens used: unknown (model did not report)")

    def _handle_non_streaming_completion(self, response):
        """Handles the non-streaming logic, returning a response dict."""
        content = response.choices[0].message.content
        total_tokens = response.usage.total_tokens if response.usage else 0
        logger.info(f"[LLM NON-STREAM] Tokens used: {total_tokens}")

        return {
            "response": content,
            "tokens_used": total_tokens,
            "model_used": self.provider,
            "status": "success",
        }

    def _call_completion_api(self, system_role, user_content):
        """
        General method to call LiteLLM completion API.
        Returns either a generator (if stream=True) or a response dict.
        """
        # Build completion parameters
        stream = self.config.get("stream", False) or self.extra_params.get("stream", False)
        completion_params = {
            "messages": [
                {"role": "system", "content": system_role},
                {"role": "user", "content": user_content},
            ],
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
