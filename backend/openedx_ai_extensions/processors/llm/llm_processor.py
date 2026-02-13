"""
Responses processor for threaded AI conversations using LiteLLM
"""

import json
import logging
from datetime import datetime, timezone

from litellm import completion, get_responses, list_input_items, responses

from openedx_ai_extensions.functions.decorators import AVAILABLE_TOOLS
from openedx_ai_extensions.processors.llm.litellm_base_processor import LitellmProcessor
from openedx_ai_extensions.processors.llm.providers import adapt_to_provider, after_tool_call_adaptations

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

        function_name = self.config.get("function", None)
        # jsonmerge still returns "function": null", so check for that too
        if not function_name:
            function_name = "call_with_custom_prompt"
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
            self.chat_history.append({"role": "user", "content": self.input_data})
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
            input_data=self.input_data
        )

        return params

    def _yield_threaded_stream(self, response, params=None):
        """
        Helper generator to handle streaming logic for threaded responses.
        Handles tool calls execution recursively during streaming.
        """
        total_tokens = None
        try:  # pylint: disable=R1702
            for chunk in response:
                # Track token usage from the response metadata
                chunk_response = getattr(chunk, "response", None)
                if chunk_response and hasattr(chunk_response, "usage") and chunk_response.usage:
                    total_tokens = chunk_response.usage.total_tokens
                elif hasattr(chunk, "usage") and chunk.usage:
                    total_tokens = chunk.usage.total_tokens

                # Persist thread ID for ongoing conversation context
                if chunk_response:
                    if chunk_response is not None and self.user_session:
                        response_id = getattr(chunk_response, "id", None)
                        if response_id:
                            self.user_session.remote_response_id = response_id
                            self.user_session.save()

                # Stream text deltas, filtering out empty JSON artifacts
                if hasattr(chunk, "delta"):
                    yield chunk.delta if chunk.delta != "{}" else ""

                # Check for completed tool call requests
                chunk_type = getattr(chunk, "type", None)
                if chunk_type == "response.output_item.done":
                    item = chunk.item
                    if getattr(item, "type", None) == "function_call":
                        logger.info(f"[LLM STREAM] Intercepted tool call: {item.name}")

                        function_name = item.name
                        call_id = item.call_id
                        arguments_str = item.arguments

                        # Add function call intent to history (required for API consistency)
                        if params is not None:
                            params["input"].append({
                                "type": "function_call",
                                "call_id": call_id,
                                "name": function_name,
                                "arguments": arguments_str
                            })

                        # Parse arguments and execute the local function
                        try:
                            function_args = json.loads(arguments_str)
                        except json.JSONDecodeError:
                            function_args = {}

                        if function_name in AVAILABLE_TOOLS:
                            func = AVAILABLE_TOOLS[function_name]
                            try:
                                tool_output = func(**function_args)
                            except Exception as e:  # pylint: disable=broad-exception-caught
                                tool_output = f"Error: {str(e)}"
                        else:
                            tool_output = "Error: Tool not found."

                        if params is None:
                            yield "\n[System Error: Missing params]".encode("utf-8")
                            return

                        # Add tool output to history and re-trigger LLM response
                        params["input"].append({
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": str(tool_output)
                        })

                        # Recursively stream the new response interpreting the tool output
                        new_response = responses(**params)
                        yield from self._yield_threaded_stream(new_response, params)
                        return

            if total_tokens is not None:
                logger.info(f"[LLM STREAM] Tokens used: {total_tokens}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error: {e}", exc_info=True)
            yield f"\n[AI Error: {e}]".encode("utf-8")

    def _call_responses_wrapper(self, params, initialize=False):
        """
        Wrapper around LiteLLM responses() call.
        """
        try:
            response = self._responses_with_tools(tool_calls=[], params=params)

            if params["stream"]:
                return self._yield_threaded_stream(response, params=params)

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
                system_msgs = [msg for msg in params.get("input", []) if "role" in msg and msg["role"] == "system"]
                result["system_messages"] = system_msgs
            return result

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.exception(f"Error calling LiteLLM: {e}")
            return {"error": f"AI processing failed: {str(e)}"}

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
            response = self._completion_with_tools(tool_calls=[], params=params)
            # 2. Handle streaming response (Generator)
            if self.stream:
                return self._handle_streaming_completion(response)  # Return the generator object
            else:
                return self._handle_non_streaming_completion(response)  # Return the dictionary

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Catch errors that occur during the INITIAL API call (before streaming starts)
            error_message = f"Error during initial AI completion call: {e}"
            logger.exception(error_message, exc_info=True)
            # Always return a dictionary error in this outer block
            return {"error": f"AI processing failed: {str(e)}"}

    def _completion_with_tools(self, tool_calls, params):
        """Handle tool calls recursively until no more tool calls are present."""
        for tool_call in tool_calls:
            function_name = tool_call.function.name

            # Ensure tool exists
            if function_name not in AVAILABLE_TOOLS:
                logger.error(f"Tool '{function_name}' requested by LLM but not available locally.")
                continue

            function_to_call = AVAILABLE_TOOLS[function_name]
            logger.info(f"[LLM] Tool call: {function_to_call}")

            try:
                function_args = json.loads(tool_call.function.arguments)
                function_response = function_to_call(**function_args)
                logger.info(f"[LLM] Response from tool call: {function_response}")
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

    def _handle_streaming_tool_calls(self, response, params):
        """
        Generator that handles streaming responses containing tool calls.
        It accumulates tool call chunks, executes them, and recursively calls completion.
        """
        tool_calls_buffer = {}  # index -> {id, function: {name, arguments}}
        accumulating_tools = False
        logger.info("[LLM STREAM] Streaming tool calls")

        for chunk in response:
            delta = chunk.choices[0].delta

            # If there is content, yield it immediately to the user
            if delta.content:
                yield chunk

            # If there are tool calls, buffer them
            if delta.tool_calls:
                if not accumulating_tools:
                    logger.info("[AI STREAM] Start: buffer function")
                accumulating_tools = True
                for tc_chunk in delta.tool_calls:
                    idx = tc_chunk.index

                    if idx not in tool_calls_buffer:
                        tool_calls_buffer[idx] = {
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""}
                        }

                    if tc_chunk.id:
                        tool_calls_buffer[idx]["id"] += tc_chunk.id

                    if tc_chunk.function:
                        if tc_chunk.function.name:
                            tool_calls_buffer[idx]["function"]["name"] += tc_chunk.function.name
                        if tc_chunk.function.arguments:
                            tool_calls_buffer[idx]["function"]["arguments"] += tc_chunk.function.arguments

        # If we accumulated tool calls, reconstruct them and recurse
        if accumulating_tools and tool_calls_buffer:

            # Helper classes to mimic the object structure LiteLLM expects in _completion_with_tools
            class FunctionMock:
                def __init__(self, name, arguments):
                    self.name = name
                    self.arguments = arguments

            class ToolCallMock:
                def __init__(self, t_id, name, arguments):
                    self.id = t_id
                    self.function = FunctionMock(name, arguments)
                    self.type = "function"

            # Prepare list for the recursive call
            reconstructed_tool_calls = []

            # Prepare message to append to history (as dict for JSON serialization)
            assistant_message_tool_calls = []

            for idx in sorted(tool_calls_buffer.keys()):
                data = tool_calls_buffer[idx]

                # Create object for internal logic
                tc_obj = ToolCallMock(
                    t_id=data['id'],
                    name=data['function']['name'],
                    arguments=data['function']['arguments']
                )
                reconstructed_tool_calls.append(tc_obj)

                # Create dict for history
                assistant_message_tool_calls.append({
                    "id": data['id'],
                    "type": "function",
                    "function": {
                        "name": data['function']['name'],
                        "arguments": data['function']['arguments']
                    }
                })

            # Append the Assistant's intent to call tools to the history
            params["messages"].append({
                "role": "assistant",
                "content": None,
                "tool_calls": assistant_message_tool_calls
            })

            # Recursively call completion with the reconstructed tools
            # yield from delegates the generation of the next stream (result of tool) to this generator
            yield from self._completion_with_tools(reconstructed_tool_calls, params)

    def _responses_with_tools(self, tool_calls, params):
        """Handle tool calls recursively until no more tool calls are present."""
        for tool_call in tool_calls:
            function_name = tool_call.name
            function_to_call = AVAILABLE_TOOLS[function_name]
            function_args = json.loads(tool_call.arguments)

            function_response = function_to_call(
                **function_args,
            )
            params["input"].append({
                "type": "function_call_output",
                "call_id": tool_call.call_id,
                "output": str(function_response)
            })

        # Call completion again with updated messages
        response = responses(**params)

        if params.get("stream"):
            return response

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

        return {"type": item_type, "role": role, "content": str(content)}

    @staticmethod
    def _extract_output_items(resp):
        """Convert provider output items to serializable dicts."""
        items = []
        for item in getattr(resp, "output", []) or []:
            item_type = getattr(item, "type", "unknown")
            if item_type == "message":
                for block in getattr(item, "content", []):
                    if getattr(block, "type", None) == "output_text":
                        items.append({"role": "assistant", "content": block.text})
            elif item_type == "function_call":
                items.append({
                    "role": "tool_call",
                    "content": f"{getattr(item, 'name', '?')}({getattr(item, 'arguments', '')})",
                })
        return items
