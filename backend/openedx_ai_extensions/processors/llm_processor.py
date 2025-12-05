"""
Responses processor for threaded AI conversations using LiteLLM
"""

import logging

from litellm import completion, responses

from openedx_ai_extensions.processors.litellm_base_processor import LitellmProcessor

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

        function_name = self.config.get("function", "chat_with_context")
        function = getattr(self, function_name)
        return function()

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

    def _build_params(self, system_role=None):
        """
        Build completion parameters for LiteLLM responses API.

        Args:
            system_role: System role message for initializing thread
            context: Context message for initializing thread
            input_data: User query for continuing existing thread

        Returns:
            dict: Completion parameters ready for responses() call
        """
        params = {}

        if self.chat_history:
            self.chat_history.append({"role": "user", "content": self.input_data})
            params["input"] = self.chat_history
        elif self.user_session.remote_response_id and self.provider == "openai":
            params["previous_response_id"] = self.user_session.remote_response_id
            params["input"] = [{"role": "user", "content": self.input_data}]
        else:
            # Initialize new thread with system role and context
            params["input"] = [
                {"role": "system", "content": system_role},
                {"role": "system", "content": self.context},
            ]

            # anthropic requires a user message
            if self.provider == "anthropic":
                params["input"] += [
                    {"role": "user", "content": "Please provide the requested information based on the context above."}
                ]

        # Add optional parameters only if configured
        params.update(self.extra_params)

        return params

    def _call_responses_wrapper(self, params, initialize=False):
        """
        Wrapper around LiteLLM responses() call that handles the API call and session updates.

        Args:
            completion_params: Parameters for the responses() call

        Returns:
            dict: Standardized response with content, tokens_used, model_used, and status
        """
        try:
            response = responses(**params)

            response_id = getattr(response, "id", None)
            content = self._extract_response_content(response=response)

            # Update session with response ID for threading
            if response_id:
                self.user_session.remote_response_id = response_id
                self.user_session.save()

            response = {
                "response": content,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "model_used": self.extra_params.get("model", "unknown"),
                "status": "success",
            }
            # Include system messages when initializing a new thread to add it to submissions for non-OpenAI providers
            if initialize:
                system_msgs = [msg for msg in params.get("input", []) if msg["role"] == "system"]
                response["system_messages"] = system_msgs
            return response

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error calling LiteLLM: {e}")
            return {"error": f"AI processing failed: {str(e)}"}

    def _call_completion_wrapper(self, system_role):
        """
        General method to call LiteLLM completion API
        Handles configuration and returns standardized response
        """
        try:
            params = {
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

            if not self.input_data and self.provider == "anthropic":
                # anthropic requires a user message
                params["messages"] += [
                    {"role": "user", "content": "Please provide the requested information based on the context above."}
                ]

            params.update(self.extra_params)

            response = completion(**params)
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
        params = self._build_params(system_role=system_role)
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
        system_role = "Greet the user and say hello world outlining which Llm model is being used!"
        result = self._call_completion_wrapper(system_role=system_role)

        return result
