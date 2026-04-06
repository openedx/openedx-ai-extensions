"""
Responses processor for threaded AI conversations using LiteLLM
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from litellm import completion, get_responses, list_input_items, responses
from litellm.exceptions import BadRequestError

from openedx_ai_extensions.functions.decorators import AVAILABLE_TOOLS
from openedx_ai_extensions.processors.llm.litellm_base_processor import LitellmProcessor
from openedx_ai_extensions.processors.llm.providers import adapt_to_provider, after_tool_call_adaptations
from openedx_ai_extensions.processors.llm.tool_executor import ToolExecutor
from openedx_ai_extensions.utils import STREAMING_FAILED_MESSAGE, normalize_input_to_text

logger = logging.getLogger(__name__)


class LLMProcessor(LitellmProcessor):
    """
    Handles AI processing using LiteLLM with support for threaded conversations.

    This processor accepts an optional extra_params argument in its constructor,
    which is passed directly to the LitellmProcessor base class. This allows you to
    configure advanced LiteLLM parameters such as:

        - model: str (e.g., 'openai/gpt-4')
        - temperature: float (e.g., 0.7)
        - max_tokens: int (e.g., 150)
        - api_key: str
        - response_format: dict
        - and any other parameters supported by the underlying LiteLLM client
    """

    def __init__(self, config=None, user_session=None, extra_params=None):
        """
        Initialize LLMProcessor. extra_params is passed to LitellmProcessor for
        advanced configuration.
        """
        super().__init__(config, user_session, extra_params)
        self.chat_history = None
        self.input_data = None
        self.context = None

    def process(self, *args, **kwargs):
        """Process based on configured function"""
        self.context = kwargs.get("context", None)
        self.input_data = kwargs.get("input_data", None)
        self.chat_history = kwargs.get("chat_history", None)

        function_name = self.config.get("function", None)
        # jsonmerge still returns "function": null", so check for that too
        if not function_name:
            function_name = "call_with_custom_prompt"
        function = getattr(self, function_name)
        return function()

    def _handle_streaming_completion(self, response):
        """Stream with chunk buffering (more natural UI speed)."""
        try:
            for chunk in response:
                self._set_token_usage(chunk)
                content = chunk.choices[0].delta.content or ""
                if content:
                    yield content.encode('utf-8')

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Log exact error, but yield sanitized JSON marker to UI
            logger.error(f"Error during AI streaming: {e}", exc_info=True)
            error_marker = json.dumps({
                "error_in_stream": True,
                "code": "streaming_failed",
                "message": STREAMING_FAILED_MESSAGE
            })
            yield f"||{error_marker}||".encode("utf-8")

    def _handle_non_streaming_completion(self, response):
        """Handles the non-streaming logic, returning a response dict."""
        content = response.choices[0].message.content
        self._set_token_usage(response)

        return {
            "response": content,
            "usage": self.usage,
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

    def _extract_response_tool_calls(self, response):
        """Extract tool calls from LiteLLM response."""
        tool_calls = []
        if not hasattr(response, "output") or not response.output:
            return tool_calls

        for item in response.output:
            if getattr(item, "type", None) == "function_call":
                tool_calls.append(item)
        return tool_calls

    def _build_response_api_params(self, system_role=None):
        """
        Build completion parameters for LiteLLM responses API.
        """
        params = {}
        params["stream"] = self.stream

        if self.chat_history:
            user_text = normalize_input_to_text(self.input_data)
            if user_text:
                self.chat_history.append({"role": "user", "content": user_text})
            params["input"] = self.chat_history
        else:
            # Initialize new thread with system role and context
            params["input"] = [
                {"role": "system", "content": self.custom_prompt or system_role},
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
            input_data=self.input_data,
        )

        return params

    def _yield_threaded_stream(self, response, params=None):
        """
        Streaming generator for threaded conversations (Responses API).
        Parses event types, yields text deltas, logs token usage, updates the
        user session, and handles tool calls recursively.
        Parallel to _handle_streaming_completion for the Completion API.
        """
        yield from self._handle_streaming_tool_calls_responses(response, params or {})

    def _call_responses_wrapper(self, params, initialize=False, system_role=None):
        """
        Wrapper around LiteLLM responses() call.
        """
        try:
            if params["stream"]:
                if "messages" in params:
                    response = self._completion_with_tools([], params)
                    return self._handle_streaming_completion(response)

                raw_response = responses(**params)
                return self._yield_threaded_stream(raw_response, params)

            response = self._responses_with_tools(tool_calls=[], params=params)

            response_id = getattr(response, "id", None)
            content = self._extract_response_content(response=response)

            # Update session with response ID for threading
            if response_id:
                self.user_session.remote_response_id = response_id
                self.user_session.save()

            result = {
                "response": content,
                "usage": self.usage,
                "model_used": self.extra_params.get("model", "unknown"),
                "status": "success",
            }
            # Include system messages when initializing a new thread
            if initialize:
                system_msgs = [msg for msg in params.get("input", []) if "role" in msg and msg["role"] == "system"]
                result["system_messages"] = system_msgs
            return result
        except BadRequestError as e:
            error_code = getattr(e, "code", str(e))
            if "previous_response_not_found" in str(error_code):
                logger.warning(
                    "Previous response ID '%s' not found. Clearing and retrying with full history fallback.",
                    self.user_session.remote_response_id if self.user_session else "Unknown"
                )
                if self.user_session:
                    self.user_session.remote_response_id = None
                    self.user_session.save()

                # Re-build params without previous_response_id and with full history
                params = self._build_response_api_params(system_role=system_role)
                return self._call_responses_wrapper(params=params, initialize=True, system_role=system_role)
            raise

    def _call_completion_wrapper(self, system_role):
        """
        General method to call LiteLLM completion API.
        Returns either a generator (if stream=True) or a response dict.
        """
        # Build completion parameters
        params = {
            "stream": self.stream,
            "messages": [
                {"role": "system", "content": self.custom_prompt or system_role},
            ],
        }
        if self.caching_enabled:
            params["caching"] = True

        if self.stream:
            params["stream_options"] = {"include_usage": True}

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

        # 1. Call the LiteLLM API
        response = self._completion_with_tools(tool_calls=[], params=params)
        # 2. Handle streaming response (Generator)
        if self.stream:
            return self._handle_streaming_completion(response)  # Return the generator object
        else:
            return self._handle_non_streaming_completion(response)  # Return the dictionary

    def _completion_with_tools(self, tool_calls, params):
        """Handle tool calls recursively until no more tool calls are present."""
        for tool_call in tool_calls:
            function_name = tool_call.function.name

            # Ensure tool exists
            if function_name not in AVAILABLE_TOOLS:
                logger.error(f"Tool '{function_name}' requested by LLM but not available locally.")
                continue

            function_to_call = AVAILABLE_TOOLS[function_name]

            try:
                function_args = json.loads(tool_call.function.arguments)
                function_response = function_to_call(**function_args)
            except json.JSONDecodeError:
                function_response = "Error: Invalid JSON arguments provided."
                logger.error(f"Failed to parse JSON arguments for {function_name}")
            except Exception as e:  # pylint: disable=broad-exception-caught
                function_response = f"Error executing tool: {str(e)}"
                logger.error(f"Error executing tool {function_name}: {e}")

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

        # For streaming, we need to handle the stream to detect tool calls
        if params.get("stream"):
            return self._handle_streaming_tool_calls(response, params)

        # For non-streaming, check for tool calls and handle recursively
        new_tool_calls = response.choices[0].message.tool_calls
        if new_tool_calls:
            params["messages"].append(response.choices[0].message)
            return self._completion_with_tools(new_tool_calls, params)

        return response

    # -------------------------------------------------------------------------
    # Completion API streaming helpers
    # -------------------------------------------------------------------------

    def _handle_streaming_tool_calls(self, response, params):
        """
        Generator for Completion API streaming responses that may contain tool calls.
        Yields content chunks immediately; accumulates tool-call deltas and replays
        them after the stream ends via _completion_with_tools.
        """
        tool_calls_buffer = {}

        for chunk in response:
            self._set_token_usage(chunk)
            delta = chunk.choices[0].delta
            if delta.content:
                yield chunk
            for tc_chunk in (delta.tool_calls or []):
                ToolExecutor.accumulate_tool_call_chunk(tool_calls_buffer, tc_chunk)

        if not tool_calls_buffer:
            return

        tool_call_objects, assistant_tool_calls = ToolExecutor.reconstruct_tool_calls(tool_calls_buffer)
        params["messages"].append({
            "role": "assistant",
            "content": None,
            "tool_calls": assistant_tool_calls,
        })
        yield from self._completion_with_tools(tool_call_objects, params)

    # -------------------------------------------------------------------------
    # Responses API streaming helpers
    # -------------------------------------------------------------------------

    def _set_token_usage(self, response) -> "int | None":
        """Extract total token count from the response and save to self.usage for event emission."""

        usage = None
        chunk_response = getattr(response, "response", None)
        if chunk_response and getattr(chunk_response, "usage", None):
            usage = chunk_response.usage
        if getattr(response, "usage", None):
            usage = response.usage

        if usage is None:
            return

        try:
            if self.usage is not None:
                self.usage.total_tokens += usage.total_tokens
                self.usage.prompt_tokens += usage.prompt_tokens
                self.usage.completion_tokens += usage.completion_tokens
            else:
                self.usage = usage
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error updating token usage: {e}")
            self.usage = usage  # Fallback to latest usage if accumulation fails

    def _persist_response_id(self, chunk) -> None:
        """Save the response ID carried by *chunk* to the user session, if present."""
        if not self.user_session:
            return
        chunk_response = getattr(chunk, "response", None)
        response_id = chunk_response and getattr(chunk_response, "id", None)
        if response_id:
            self.user_session.remote_response_id = response_id
            self.user_session.save()

    def _handle_tool_call_item(self, item, params) -> None:
        """
        Execute a completed Responses API tool call and append both the call
        intent and its output to *params['input']* so the LLM can continue.
        """
        tool_output = ToolExecutor.execute_tool(item.name, item.arguments)
        params["input"].append({
            "type": "function_call",
            "call_id": item.call_id,
            "name": item.name,
            "arguments": item.arguments,
        })
        params["input"].append({
            "type": "function_call_output",
            "call_id": item.call_id,
            "output": tool_output,
        })

    def _handle_streaming_tool_calls_responses(self, response, params):
        """
        Generator for Responses API streaming responses.
        Yields text deltas, persists the thread ID, logs token usage, and handles
        completed tool calls by executing them and recursing via _responses_with_tools.
        Parallel to _handle_streaming_tool_calls for the Completion API.
        """
        try:
            for chunk in response:
                self._set_token_usage(chunk)
                self._persist_response_id(chunk)

                if hasattr(chunk, "delta") and chunk.delta and chunk.delta != "{}":
                    yield chunk.delta

                if getattr(chunk, "type", None) == "response.output_item.done":
                    item = chunk.item
                    if getattr(item, "type", None) == "function_call":
                        self._handle_tool_call_item(item, params)
                        yield from self._responses_with_tools([], params)
                        return

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error during streaming tool calls: %s", e, exc_info=True)
            # Clear the remote response ID if it was partially saved but the stream failed
            # This prevents subsequent calls from using an invalid/incomplete thread ID.
            if self.user_session and self.user_session.remote_response_id:
                self.user_session.remote_response_id = None
                self.user_session.save()

            error_marker = json.dumps({
                "error_in_stream": True,
                "code": "streaming_failed",
                "message": STREAMING_FAILED_MESSAGE
            })
            yield f"||{error_marker}||"
            return

    def _responses_with_tools(self, tool_calls, params):
        """Handle tool calls recursively until no more tool calls are present."""
        for tool_call in tool_calls:
            params["input"].append({
                "type": "function_call_output",
                "call_id": tool_call.call_id,
                "output": ToolExecutor.execute_tool(tool_call.name, tool_call.arguments),
            })

        # Call responses API with updated input
        response = responses(**params)

        if params.get("stream"):
            return self._handle_streaming_tool_calls_responses(response, params)

        new_tool_calls = self._extract_response_tool_calls(response=response)
        if new_tool_calls:
            params = after_tool_call_adaptations(self.provider, params, data=response)
            return self._responses_with_tools(new_tool_calls, params)

        return response

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
                  Default to concise responses (3–6 sentences maximum) unless
                  the learner explicitly asks for a detailed explanation.
                  Do not provide long summaries unless specifically requested.
                  Prefer guided questioning over full explanations.
                  Ask clarifying questions when the learner’s intent is ambiguous.
                  Encourage learners to articulate their thinking before providing full answers.
                  Expand only if the learner asks for more depth.

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
            return self._call_responses_wrapper(params=params, system_role=system_role)
        return self._call_responses_wrapper(params=params, initialize=True, system_role=system_role)

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
            "Roll a dice: if the result is 1, give me the current location complete link, "
            "if the result is 2 or more then Enumerate the location content and leave a "
            "brief explanation of each section. In all cases present the results of the dice roll."
        )

        result = self._call_completion_wrapper(system_role=system_role)

        return result

    def call_with_custom_prompt(self):
        """Call LLM with a completely custom prompt provided in custom_prompt config."""
        if not self.custom_prompt:
            raise ValueError("Custom prompt not provided in configuration.")

        result = self._call_completion_wrapper(system_role="")

        return result

    def fetch_remote_thread(self, response_id):
        """
        Fetch the full remote conversation thread by walking the
        previous_response_id chain via LiteLLM.

        Uses provider credentials from self.extra_params resolved during __init__.

        Args:
            response_id: The LiteLLM-wrapped response ID.

        Returns:
            list: Chronologically ordered list of response dicts, each containing
                  id, created_at, model, tokens, input messages, and output messages.
        """
        chain = []
        current_id = response_id

        while current_id:
            try:
                resp = get_responses(
                    response_id=current_id,
                    custom_llm_provider=self.provider,
                    **self.extra_params,
                )
                input_items_result = list_input_items(
                    response_id=current_id, order="asc", limit=100,
                    custom_llm_provider=self.provider,
                    **self.extra_params,
                )
                input_items = input_items_result.get("data", []) if isinstance(input_items_result, dict) else []
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Failed to retrieve remote response %s: %s", current_id, e)
                chain.append({"id": current_id, "error": str(e)})
                break

            created_at = getattr(resp, "created_at", None)
            if created_at:
                created_at = datetime.fromtimestamp(created_at, tz=timezone.utc).isoformat()

            response_data = {
                "id": getattr(resp, "id", current_id),
                "created_at": created_at,
                "model": getattr(resp, "model", "unknown"),
                "previous_response_id": getattr(resp, "previous_response_id", None),
                "tokens": resp.usage.total_tokens if getattr(resp, "usage", None) else None,
                "input": [self._extract_input_item(item) for item in input_items],
                "output": self._extract_output_items(resp),
            }
            chain.append(response_data)
            current_id = getattr(resp, "previous_response_id", None)

        chain.reverse()
        return chain

    @staticmethod
    def _extract_input_item(item):
        """Convert a provider input item to a serializable dict."""
        if isinstance(item, dict):
            role = item.get("role", item.get("type", "unknown"))
            content = item.get("content", item.get("text", ""))
            item_type = item.get("type", "unknown")
        else:
            item_type = getattr(item, "type", "unknown")
            role = getattr(item, "role", item_type)
            content = getattr(item, "content", None)

        if isinstance(content, list):
            parts = []
            for c in content:
                if isinstance(c, dict):
                    parts.append(c.get("text", str(c)))
                else:
                    parts.append(getattr(c, "text", str(c)))
            content = " ".join(parts)
        elif content is None:
            content = getattr(item, "text", "") if not isinstance(item, dict) else ""

        result = {"type": item_type, "role": role, "content": str(content)}

        # Preserve structured fields for tool-result items so they can be rendered.
        if item_type == "function_call_output":
            output = item.get("output", "") if isinstance(item, dict) else getattr(item, "output", "")
            call_id = item.get("call_id") if isinstance(item, dict) else getattr(item, "call_id", None)
            result["content"] = str(output) if output else result["content"]
            result["call_id"] = call_id

        return result

    @staticmethod
    def _extract_output_items(resp):
        """Convert provider output items to serializable dicts."""
        items = []
        for item in getattr(resp, "output", []) or []:
            item_type = getattr(item, "type", "unknown")
            if item_type == "message":
                for block in getattr(item, "content", []):
                    if getattr(block, "type", None) == "output_text":
                        items.append({"type": "message", "role": "assistant", "content": block.text})
            elif item_type == "function_call":
                name = getattr(item, "name", "?")
                arguments = getattr(item, "arguments", "")
                items.append({
                    "type": "function_call",
                    "role": "tool_call",
                    "name": name,
                    "arguments": arguments,
                    "call_id": getattr(item, "call_id", None),
                    "content": f"{name}({arguments})",
                })
            elif item_type == "reasoning":
                summary = getattr(item, "summary", []) or []
                summary_text = " ".join(
                    s.get("text", "") if isinstance(s, dict) else getattr(s, "text", "")
                    for s in summary
                )
                if summary_text:
                    items.append({"type": "reasoning", "role": "reasoning", "content": summary_text})
        return items

    def generate_flashcards(self):
        """Example method showing how to generate flashcards from content."""
        prompt_file_path = (
            Path(__file__).resolve().parent.parent.parent
            / "prompts"
            / "default_generate_flashcards.txt"
        )
        try:
            with open(prompt_file_path, "r") as f:
                prompt = f.read()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.exception(f"Error loading prompt template: {e}")
            return {"error": "Failed to load prompt template."}

        for key, value in self.input_data.items():
            placeholder = f"{{{{{key.upper()}}}}}"
            prompt = prompt.replace(placeholder, str(value))

        self.input_data = None

        try:
            result = self._call_completion_wrapper(prompt)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.exception(f"Error calling LiteLLM: {e}")
            return {"error": f"AI processing failed: {str(e)}"}

        if "error" in result:
            return result

        response = json.loads(result['response'])

        return {
            "response": response,
            "usage": self.usage,
            "model_used": self.extra_params.get("model", "unknown"),
            "status": "success",
        }
