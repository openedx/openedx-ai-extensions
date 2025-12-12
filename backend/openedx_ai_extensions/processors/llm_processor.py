"""
Responses processor for threaded AI conversations using LiteLLM
"""

import logging

from litellm import completion, responses

from openedx_ai_extensions.processors.litellm_base_processor import LitellmProcessor
from openedx_ai_extensions.processors.llm_providers import adapt_to_provider

logger = logging.getLogger(__name__)


class LLMProcessor(LitellmProcessor):
    """Handles AI processing using LiteLLM with support for threaded conversations."""

    def __init__(self, config=None, user_session=None):
        super().__init__(config, user_session)
        self.chat_history = None
        self.input_data = None
        self.context = None

    def process(self, *args, **kwargs):
        """Process based on configured function"""
        self.context = kwargs.get("context", None)
        self.input_data = kwargs.get("input_data", None)
        self.chat_history = kwargs.get("chat_history", None)

        function_name = self.config.get("function")
        function = getattr(self, function_name)
        return function()

    def _handle_streaming_completion(self, response):
        """Stream with chunk buffering (more natural UI speed)."""
        total_tokens = None
        try:
            for chunk in response:
                if hasattr(chunk, "usage") and chunk.usage:
                    total_tokens = chunk.usage.total_tokens

                content = chunk.choices[0].delta.content or ""
                if content:
                    yield content.encode('utf-8')

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

    def _build_response_api_params(self, system_role=None):
        """
        Build completion parameters for LiteLLM responses API.
        """
        params = {}
        params["stream"] = self.config.get("stream", False) or self.extra_params.get("stream", False)

        if self.chat_history:
            self.chat_history.append({"role": "user", "content": self.input_data})
            params["input"] = self.chat_history
        else:
            # Initialize new thread with system role and context
            params["input"] = [
                {"role": "system", "content": system_role},
                {"role": "system", "content": self.context},
            ]

        # Add optional parameters only if configured
        params.update(self.extra_params)

        has_user_input = bool(self.input_data or self.chat_history)
        params = adapt_to_provider(
            self.provider,
            params,
            has_user_input=has_user_input,
            user_session=self.user_session,
            input_data=self.input_data
        )

        return params

    def _yield_threaded_stream(self, response):
        """
        Helper generator to handle streaming logic for threaded responses.
        """
        total_tokens = None
        try:
            for chunk in response:
                if hasattr(chunk, "usage") and chunk.usage:
                    total_tokens = chunk.usage.total_tokens

                if getattr(chunk, "response", None):
                    resp = getattr(chunk, "response", None)
                    if resp is not None:
                        response_id = getattr(resp, "id", None)
                        self.user_session.remote_response_id = response_id
                        self.user_session.save()
                if hasattr(chunk, "delta"):
                    yield chunk.delta

            if total_tokens is not None:
                logger.info(f"[LLM STREAM] Tokens used: {total_tokens}")
            else:
                logger.info("[LLM STREAM] Tokens used: unknown (model did not report)")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error during threaded AI streaming: {e}", exc_info=True)
            yield f"\n[AI Error: {e}]"

    def _call_responses_wrapper(self, params, initialize=False):
        """
        Wrapper around LiteLLM responses() call.
        """
        try:
            response = responses(**params)

            if params["stream"]:
                return self._yield_threaded_stream(response)

            response_id = getattr(response, "id", None)
            content = self._extract_response_content(response=response)

            # Update session with response ID for threading
            if response_id:
                self.user_session.remote_response_id = response_id
                self.user_session.save()
            total_tokens = response.usage.total_tokens if response.usage else 0
            logger.info(f"[LLM NON-STREAM] Tokens used: {total_tokens}")

            result = {
                "response": content,
                "tokens_used": total_tokens,
                "model_used": self.extra_params.get("model", "unknown"),
                "status": "success",
            }
            # Include system messages when initializing a new thread
            if initialize:
                system_msgs = [msg for msg in params.get("input", []) if msg["role"] == "system"]
                result["system_messages"] = system_msgs
            return result

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error calling LiteLLM: {e}")
            return {"error": f"AI processing failed: {str(e)}"}

    def _call_completion_wrapper(self, system_role):
        """
        General method to call LiteLLM completion API.
        Returns either a generator (if stream=True) or a response dict.
        """
        # Build completion parameters
        stream = self.config.get("stream", False) or self.extra_params.get("stream", False)
        params = {
            "stream": stream,
            "messages": [
                {"role": "system", "content": system_role},
            ],
        }

        if self.context:
            params["messages"].append(
                {"role": "system", "content": self.context}
            )

        if self.input_data:
            params["messages"].append(
                {"role": "user", "content": self.input_data}
            )

        params.update(self.extra_params)

        has_user_input = bool(self.input_data)
        params = adapt_to_provider(
            provider=self.provider,
            params=params,
            has_user_input=has_user_input,
            user_session=self.user_session,
            input_data=self.input_data,
        )

        try:
            # 1. Call the LiteLLM API
            response = completion(**params)

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

    def chat_with_context(self):
        """
        Chat with context given from OpenEdx course content.
        Either initializes a new thread or continues an existing one.

        Args:
            context: Course content context
            input_data: Optional input data to continue conversation

        Returns:
            dict: Response from the API
        """
        system_role = """
              - Role & Purpose
                  You are an AI assistant embedded into an Open edX learning environment.
                  Your purpose is to Provide helpful, accurate, and context-aware guidance
                  to students as they navigate course content.

              - Core Behaviors
                  Always prioritize the course‑provided context as your primary source of truth.
                  If the course does not contain enough information to answer accurately,
                  state the limitation and offer a helpful alternative.
                  Maintain clarity, accuracy, and educational value in every response.
                  Adapt depth and complexity of explanations to the learner’s level when interacting with students.
                  Avoid hallucinating facts or adding external content unless explicitly allowed.

              - Learner Assistance Mode
                  When interacting with learners:
                  Provide clear, supportive explanations.
                  Prioritize information available within the course materials provided to you.
                  When answering questions, reference the structure, explanations, and examples
                  from the course context.
                  Help learners navigate concepts without giving away answers during graded activities unless allowed.
                  Use examples and analogies that are consistent with the course content.
                  Encourage deeper understanding, critical thinking, and application.

              - Safety & Limits
                  Do not introduce contradictory or external authoritative information unless asked.
                  When unsure, express uncertainty clearly.
                  Avoid providing direct answers to graded assessment questions.
            """
        params = self._build_response_api_params(system_role=system_role)
        if self.user_session and self.user_session.remote_response_id:
            return self._call_responses_wrapper(params=params)
        return self._call_responses_wrapper(params=params, initialize=True)

    def summarize_content(self):
        """Summarize content using LiteLLM"""
        system_role = (
            "You are an academic assistant which helps students briefly "
            "summarize a unit of content of an online course."
        )

        result = self._call_completion_wrapper(system_role=system_role)
        return result

    def explain_like_five(self):
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

        result = self._call_completion_wrapper(system_role=system_role)

        return result

    def greet_from_llm(self):
        """Simple test to greet from the LLM and mention which model is being used."""
        system_role = (
            "You are a helpful assistant embedded in an online course."
            "Say hello to the user and explain what LLM model you are."
            "Don't pay attention to any extra context"
        )
        result = self._call_completion_wrapper(system_role=system_role)

        return result
