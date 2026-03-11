"""
Stateless helpers for executing LLM tool calls and accumulating
streaming tool-call deltas.

Extracted from LLMProcessor so they can be tested in isolation
and reused by any processor that needs function-calling support.
"""

import json
import logging
import types

from openedx_ai_extensions.functions.decorators import AVAILABLE_TOOLS

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Pure-logic helper for LLM tool / function-call handling.

    Every method is either a static method or a class method — the class
    carries **no instance state**.  Instantiate it (or call the methods
    directly via the class) from any processor that needs tool execution
    or streaming-delta accumulation.
    """

    # -----------------------------------------------------------------
    # Tool execution
    # -----------------------------------------------------------------

    @staticmethod
    def execute_tool(function_name: str, arguments_str: str) -> str:
        """
        Parse *arguments_str* as JSON, look up *function_name* in
        ``AVAILABLE_TOOLS``, call it, and return the result as a string.

        Returns a descriptive error string on any failure so the caller
        can forward it to the LLM without raising.
        """
        if function_name not in AVAILABLE_TOOLS:
            logger.error("Tool '%s' not found in AVAILABLE_TOOLS.", function_name)
            return "Error: Tool not found."
        try:
            function_args = json.loads(arguments_str)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON arguments for '%s'.", function_name)
            return "Error: Invalid JSON arguments provided."
        try:
            result = AVAILABLE_TOOLS[function_name](**function_args)
            return str(result)
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error executing tool: {e}"

    # -----------------------------------------------------------------
    # Streaming tool-call delta accumulation (Completion API)
    # -----------------------------------------------------------------

    @staticmethod
    def accumulate_tool_call_chunk(buffer: dict, tc_chunk) -> None:
        """Merge a single streaming tool-call delta into *buffer*."""
        idx = tc_chunk.index
        if idx not in buffer:
            buffer[idx] = {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
        if tc_chunk.id:
            buffer[idx]["id"] += tc_chunk.id
        if tc_chunk.function:
            buffer[idx]["function"]["name"] += tc_chunk.function.name or ""
            buffer[idx]["function"]["arguments"] += tc_chunk.function.arguments or ""

    @staticmethod
    def reconstruct_tool_calls(buffer: dict):
        """
        Convert the chunk-accumulation *buffer* into:

        * a list of ``SimpleNamespace`` objects (compatible with
          ``_completion_with_tools``)
        * a list of plain dicts suitable for the assistant history message
        """
        tool_call_objects = []
        assistant_tool_calls = []
        for idx in sorted(buffer):
            data = buffer[idx]
            fn = data["function"]
            tool_call_objects.append(
                types.SimpleNamespace(
                    id=data["id"],
                    type="function",
                    function=types.SimpleNamespace(name=fn["name"], arguments=fn["arguments"]),
                )
            )
            assistant_tool_calls.append({
                "id": data["id"],
                "type": "function",
                "function": {"name": fn["name"], "arguments": fn["arguments"]},
            })
        return tool_call_objects, assistant_tool_calls
