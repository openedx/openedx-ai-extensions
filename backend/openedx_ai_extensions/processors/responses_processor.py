"""
Responses processor for threaded AI conversations using LiteLLM
"""

import logging

from litellm import responses

from openedx_ai_extensions.processors.litellm_base_processor import LitellmProcessor

logger = logging.getLogger(__name__)


class ResponsesProcessor(LitellmProcessor):
    """Handles threaded AI conversations using LiteLLM responses API"""

    def process(self, *args, **kwargs):
        """Process based on configured function"""
        # Accept flexible arguments to match base class signature
        context = args[0] if len(args) > 0 else kwargs.get("context")
        input_data = args[1] if len(args) > 1 else kwargs.get("input_data")
        chat_history = kwargs.get("chat_history", None)

        function_name = self.config.get("function", "chat_with_context")
        function = getattr(self, function_name)
        return function(context, input_data, chat_history)

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

    def _build_completion_params(self, system_role=None, context=None, user_query=None, chat_history=None):
        """
        Build completion parameters for LiteLLM responses API.

        Args:
            system_role: System role message for initializing thread
            context: Context message for initializing thread
            user_query: User query for continuing existing thread

        Returns:
            dict: Completion parameters ready for responses() call
        """
        completion_params = {}

        if chat_history:
            chat_history.append({"role": "user", "content": user_query})
            completion_params["input"] = chat_history
        elif self.user_session and self.user_session.remote_response_id and self.provider == "openai":
            completion_params["previous_response_id"] = self.user_session.remote_response_id
            completion_params["input"] = [{"role": "user", "content": user_query}]
        else:
            # Initialize new thread with system role and context
            completion_params["input"] = [
                {"role": "system", "content": system_role},
                {"role": "system", "content": context},
            ]

            # anthropic requires a user message
            if self.provider == "anthropic":
                completion_params["input"] += [
                    {"role": "user", "content": "Please provide the requested information based on the context above."}
                ]

        # Add optional parameters only if configured
        completion_params.update(self.extra_params)

        return completion_params

    def _call_responses_wrapper(self, completion_params, initialize=False):
        """
        Wrapper around LiteLLM responses() call that handles the API call and session updates.

        Args:
            completion_params: Parameters for the responses() call

        Returns:
            dict: Standardized response with content, tokens_used, model_used, and status
        """
        try:
            response = responses(**completion_params)

            response_id = getattr(response, "id", None)
            content = self._extract_response_content(response)

            # Update session with response ID for threading
            if response_id:
                self.user_session.remote_response_id = response_id
                self.user_session.save()

            if initialize:
                system_msgs = [msg for msg in completion_params.get("input", []) if msg["role"] == "system"]

            response = {
                "response": content,
                "params_used": completion_params,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "model_used": self.extra_params.get("model", "unknown"),
                "status": "success",
            }
            if initialize:
                response["system_messages"] = system_msgs
            return response

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
        return self._call_responses_wrapper(completion_params, initialize=True)

    def continue_thread(self, user_query, chat_history=None):
        """
        Continue an existing conversation thread with a user query.
        Requires user_session with remote_response_id.

        Args:
            user_query: User's question or message

        Returns:
            dict: Response from the API
        """
        completion_params = self._build_completion_params(user_query=user_query, chat_history=chat_history)
        return self._call_responses_wrapper(completion_params)

    def chat_with_context(self, context, user_query=None, chat_history=None):
        """
        Chat with context given from OpenEdx course content.
        Either initializes a new thread or continues an existing one.

        Args:
            context: Course content context
            user_query: Optional user query to continue conversation
            chat_history: Optional chat history for the conversation

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

        if self.user_session and self.user_session.remote_response_id:
            return self.continue_thread(user_query, chat_history=chat_history)

        return self.initialize_thread(system_role, context)
