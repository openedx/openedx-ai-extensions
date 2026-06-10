"""
Tool-call round-trips.

Verifies that LLM-invoked tools are executed and their results reach the
final response, and that unknown tool names are handled without crashing.
"""

from unittest.mock import MagicMock, patch

import pytest

from .conftest import PROVIDERS, skip_if_no_key

DUMMY_CONTENT = (
    "Python is a high-level interpreted programming language. "
    "It uses indentation for code blocks and supports multiple paradigms."
)


def _make_processor_with_tools(provider_slug, tools=None):
    from openedx_ai_extensions.processors.llm.llm_processor import LLMProcessor  # pylint: disable=import-outside-toplevel

    config_entry = {
        "provider": provider_slug,
        "stream": False,
        "function": "summarize_content",
        "enabled_tools": tools or ["__all__"],
    }
    return LLMProcessor(
        config={"LLMProcessor": config_entry},
        user_session=MagicMock(remote_response_id=None),
    )


@pytest.mark.live_llm
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
def test_tool_call_pipeline_completes(provider_slug, env_var):
    """
    When tools are enabled, the call must complete without hanging or crashing.
    The final response must be non-empty and usage must be populated.
    Whether the LLM actually invokes a tool depends on prompt context; this
    test asserts the full round-trip completes correctly.
    """
    skip_if_no_key(env_var)

    processor = _make_processor_with_tools(provider_slug)
    result = processor.process(
        context=DUMMY_CONTENT,
        input_data="Summarize this content.",
    )

    assert result.get("status") == "success", f"Processor failed: {result}"
    assert result.get("response"), "Expected non-empty response with tools enabled"

    usage = processor.get_usage()
    assert usage is not None, "usage is None with tools enabled"
    assert getattr(usage, "total_tokens", 0) > 0, f"total_tokens not set. usage={usage}"


@pytest.mark.live_llm
def test_unknown_tool_name_returns_error_string():
    """
    ToolExecutor.execute_tool returns an error string (not raises) when the
    LLM requests a tool that is not in AVAILABLE_TOOLS.
    No LLM call is made; no API key required.
    """
    from openedx_ai_extensions.processors.llm.tool_executor import ToolExecutor  # pylint: disable=import-outside-toplevel

    result = ToolExecutor.execute_tool(
        function_name="nonexistent_tool_invented_by_llm_xyz",
        arguments_str='{"param": "value"}',
    )

    assert isinstance(result, str), f"Expected string error, got {type(result)}"
    assert "error" in result.lower() or "not found" in result.lower(), (
        f"Expected error message for unknown tool, got: {result}"
    )


@pytest.mark.live_llm
@pytest.mark.parametrize("provider_slug,env_var", PROVIDERS)
def test_empty_available_tools_does_not_crash(provider_slug, env_var):
    """
    When AVAILABLE_TOOLS is empty (simulating a tool name the LLM hallucinated),
    the processor must still complete and produce a text response.
    """
    from openedx_ai_extensions.processors.llm import llm_processor as _mod  # pylint: disable=import-outside-toplevel

    skip_if_no_key(env_var)

    processor = _make_processor_with_tools(provider_slug)

    with patch.object(_mod, "AVAILABLE_TOOLS", {}):
        result = processor.process(
            context=DUMMY_CONTENT,
            input_data="What is the main topic of this content?",
        )

    assert result.get("status") == "success", (
        f"Expected success when AVAILABLE_TOOLS is empty, got: {result}"
    )
    assert result.get("response"), "Expected non-empty response"
