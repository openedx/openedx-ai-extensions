"""
Responses processor for threaded AI conversations using LiteLLM
"""

import json
import logging

from litellm import completion, responses

from openedx_ai_extensions.processors.litellm_base_processor import LitellmProcessor
from openedx_ai_extensions.processors.llm_providers import adapt_to_provider
from openedx_ai_extensions.processors.llm_functions import AVAILABLE_FUNCTIONS

logger = logging.getLogger(__name__)


class LLMProcessor(LitellmProcessor):
    """Handles AI processing using LiteLLM with support for threaded conversations."""

    def __init__(self, config=None, user_session=None, tools_context_vars=None):
        super().__init__(config, user_session)
        self.tools_context_vars = tools_context_vars or {}
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

            included_vars = self.config.get("extra_context", {}).get("vars_to_include_in_context", [])
            if included_vars:
                extra_context_parts = []
                for var_name in included_vars:
                    if var_name in self.tools_context_vars:
                        extra_context_parts.append(
                            f"{var_name}: {self.tools_context_vars[var_name]}"
                        )
                if extra_context_parts:
                    extra_context_str = "\n".join(extra_context_parts)
                    params["messages"].append(
                        {"role": "system", "content": f"Additional Context:\n{extra_context_str}"}
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

            response = completion(**params)

            tool_calls = response.choices[0].message.tool_calls
            if tool_calls:
                params["messages"].append(response.choices[0].message)
                response = self._recursive_tool_call_handler(tool_calls=tool_calls, params=params)
            else:
                response = {
                    "response": response.choices[0].message.content,
                    "usage": response.usage.total_tokens if response.usage else 0,
                }

            return {
                "response": response["response"],
                "tokens_used": response["usage"],
                "model_used": self.extra_params.get("model", "unknown"),
                "status": "success",
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error calling LiteLLM: {e}")
            return {"error": f"AI processing failed: {str(e)}"}

    def _recursive_tool_call_handler(self, tool_calls, params, usage=0):
        """Handle tool calls recursively until no more tool calls are present."""
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = AVAILABLE_FUNCTIONS[function_name]
            function_args = json.loads(tool_call.function.arguments)

            function_response = function_to_call(
                **function_args,
            )
            params["messages"].append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": str(function_response),
                }
            )

        # Call completion again with updated messages
        response = completion(**params)

        new_tool_calls = response.choices[0].message.tool_calls
        if new_tool_calls:
            params["messages"].append(response.choices[0].message)
            return self._recursive_tool_call_handler(
                new_tool_calls, params,
                usage=usage + (response.usage.total_tokens if response.usage else 0)
            )

        return {
            "response": response.choices[0].message.content,
            "usage": usage + (response.usage.total_tokens if response.usage else 0),
        }

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

    def answer_question(self):
        """Answer a specific question based on the provided content"""
        system_role = (
            "Roll a dice: if the result is 1, tell me a joke, if the result is 2 or more then"
            "Enumerate the location content and leave a brief explanation of each section."
            "In all cases present the results of the dice roll."
        )

        result = self._call_completion_wrapper(system_role=system_role)

        return result
