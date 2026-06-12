"""
Tool-call round-trips.

Verifies that LLM-invoked tools are executed and their results reach the
final response, and that unknown tool names are handled without crashing.
"""

from unittest.mock import MagicMock, patch

import pytest

from .conftest import PROVIDERS, skip_if_no_key
from .sample_content import DUMMY_CONTENT


def _make_processor_with_tools(provider_slug, tools=None):
    """Build an LLMProcessor configured with *provider_slug* and optional *tools*."""
    from openedx_ai_extensions.processors.llm.llm_processor import LLMProcessor  # pylint: disable=C0415

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
    A prompt that makes rolling dice an explicit requirement forces the LLM
    to call the roll_dice tool. roll_dice is replaced with a mock so the
    round-trip (LLM -> tool call -> tool result -> final response) is
    verified by call count, instead of depending on the LLM's wording.
    """
    from openedx_ai_extensions.processors.llm import llm_processor as _mod  # pylint: disable=C0415

    skip_if_no_key(env_var)

    mock_roll_dice = MagicMock(return_value=[4])
    processor = _make_processor_with_tools(provider_slug)

    with patch.object(_mod, "AVAILABLE_TOOLS", {"roll_dice": mock_roll_dice}):
        result = processor.process(
            context=DUMMY_CONTENT,
            input_data="You must roll one six-sided die right now and tell me the result.",
        )

    assert result.get("status") == "success", f"Processor failed: {result}"
    assert result.get("response"), "Expected non-empty response with tools enabled"
    mock_roll_dice.assert_called()

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
    from openedx_ai_extensions.processors.llm.tool_executor import ToolExecutor  # pylint: disable=C0415

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
    from openedx_ai_extensions.processors.llm import llm_processor as _mod  # pylint: disable=C0415

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
