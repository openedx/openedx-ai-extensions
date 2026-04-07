"""
Tests for the LLMProcessor module.
"""
# pylint: disable=redefined-outer-name,protected-access
import json
import types
import unittest
from unittest.mock import Mock, mock_open, patch

import pytest
from django.contrib.auth import get_user_model
from litellm.exceptions import BadRequestError
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locator import BlockUsageLocator

from openedx_ai_extensions.functions.decorators import AVAILABLE_TOOLS
from openedx_ai_extensions.processors.llm.llm_processor import LLMProcessor
from openedx_ai_extensions.workflows.models import AIWorkflowProfile, AIWorkflowScope, AIWorkflowSession

User = get_user_model()


@pytest.fixture
def user(db):  # pylint: disable=unused-argument
    """Create and return a test user."""
    return User.objects.create_user(username="testuser", email="test@example.com")


@pytest.fixture
def course_key():
    """Create and return a test course key."""
    return CourseKey.from_string("course-v1:edX+DemoX+Demo_Course")


@pytest.fixture
def workflow_profile(db):  # pylint: disable=unused-argument
    """Create and return a test workflow profile."""
    return AIWorkflowProfile.objects.create(
        slug="test-llm-processor",
        description="Test LLM processor workflow",
        base_filepath="base/default.json",
        content_patch='{}'
    )


@pytest.fixture
def workflow_scope(workflow_profile, course_key):  # pylint: disable=redefined-outer-name
    """Create and return a test workflow scope."""
    return AIWorkflowScope.objects.create(
        location_regex=".*unit-123.*",
        course_id=course_key,
        service_variant="lms",
        profile=workflow_profile,
        enabled=True,
        ui_slot_selector_id="test-slot",
    )


@pytest.fixture
def user_session(user, course_key, workflow_scope, db):  # pylint: disable=unused-argument
    """Create and return a test user session with a valid location."""
    location = BlockUsageLocator(course_key, block_type="vertical", block_id="unit-123")

    return AIWorkflowSession.objects.create(
        user=user,
        course_id=course_key,
        location_id=location,
        local_submission_id="sub-123",
        scope=workflow_scope,
        profile=workflow_scope.profile
    )


@pytest.fixture
def llm_processor(user_session, settings):  # pylint: disable=redefined-outer-name
    """Create and return an LLMProcessor instance with mocked settings."""
    # Mock AI_EXTENSIONS settings
    settings.AI_EXTENSIONS = {
        "default": {
            "MODEL": "openai/gpt-3.5-turbo",
            "API_KEY": "test-dummy-key"
        }
    }

    config = {
        "LLMProcessor": {
            "function": "chat_with_context",
            "model": "gpt-3.5-turbo",
        }
    }
    return LLMProcessor(config=config, user_session=user_session)


# --- Helper classes for Mocking LiteLLM responses ---

class MockDelta:
    """Mock for the delta object in a streaming chunk."""
    def __init__(self, content, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class MockChoice:
    """Mock for a choice object in a response."""
    def __init__(self, content=None, delta=None):
        if delta:
            self.delta = delta
        else:
            self.message = Mock(content=content, tool_calls=None)


class MockChunk:
    """Mock for a response chunk (streaming or non-streaming)."""
    def __init__(self, content, is_stream=True):
        self.usage = Mock(total_tokens=10)

        if is_stream:
            # Streaming structure
            self.choices = [MockChoice(delta=MockDelta(content))]
            self.response = Mock(id="remote-stream-id")
            self.delta = MockDelta(content)
        else:
            self.id = "remote-resp-id"

            # 1. Standard Completion Structure (for summarize_content)
            self.choices = [MockChoice(content=content)]

            # 2. Threaded Response Structure (for chat_with_context)
            # This mocks the specific structure LiteLLM returns for 'responses' endpoints
            self.output = [
                Mock(
                    type="message",
                    content=[
                        Mock(type="output_text", text=content)
                    ]
                )
            ]


class MockUsage:
    """Mock for usage statistics."""
    def __init__(self, total_tokens=10):
        self.total_tokens = total_tokens


class MockStreamChunk:
    """Mock for a streaming chunk."""
    def __init__(self, content, is_delta=True):
        self.usage = MockUsage(total_tokens=5)
        self.delta = None
        self.choices = []

        if is_delta:
            mock_delta = MockDelta(content)
            self.choices = [MockChoice(delta=mock_delta)]
            self.delta = mock_delta
            self.response = Mock(id="stream-id-123")


# ============================================================================
# Non-Streaming Tests (Standard)
# ============================================================================

@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.responses")
def test_chat_with_context_initialization_non_stream(
    mock_responses, llm_processor, user_session  # pylint: disable=redefined-outer-name
):
    """
    Test initializing a new chat thread (no previous history).
    """
    # Setup Mock
    mock_resp_obj = MockChunk("Hello user", is_stream=False)
    mock_responses.return_value = mock_resp_obj

    # Call
    result = llm_processor.process(
        context="Course Context",
        input_data="User Question",
        chat_history=[]
    )

    # Assertions
    assert result["status"] == "success"
    assert result["response"] == "Hello user"
    assert "system_messages" in result

    user_session.refresh_from_db()
    assert user_session.remote_response_id == "remote-resp-id"

    mock_responses.assert_called_once()
    call_kwargs = mock_responses.call_args[1]
    assert call_kwargs["stream"] is False
    assert call_kwargs["input"][0]["role"] == "system"


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.responses")
def test_chat_with_context_continuation_non_stream(
    mock_responses, llm_processor, user_session  # pylint: disable=redefined-outer-name
):
    """
    Test continuing an existing thread.
    """
    user_session.remote_response_id = "existing-thread-id"
    user_session.save()

    mock_resp_obj = MockChunk("Follow up answer", is_stream=False)
    mock_responses.return_value = mock_resp_obj

    chat_history = [{"role": "assistant", "content": "Previous answer"}]

    # Call
    result = llm_processor.process(
        context="Ctx",
        input_data="New Question",
        chat_history=chat_history
    )

    assert result["response"] == "Follow up answer"

    call_kwargs = mock_responses.call_args[1]
    input_msgs = call_kwargs["input"]
    assert input_msgs[-1]["role"] == "user"
    assert input_msgs[-1]["content"] == "New Question"


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.completion")
def test_summarize_content_non_stream(
    mock_completion, llm_processor  # pylint: disable=redefined-outer-name
):
    """
    Test summarize_content (uses _call_completion_wrapper).
    """
    llm_processor.config["function"] = "summarize_content"

    mock_resp_obj = MockChunk("Summary text", is_stream=False)
    mock_completion.return_value = mock_resp_obj

    result = llm_processor.process(context="Long text")

    assert result["response"] == "Summary text"
    assert result["status"] == "success"
    mock_completion.assert_called_once()


# ============================================================================
# Streaming Tests
# ============================================================================

@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.responses")
def test_chat_with_context_streaming(
    mock_responses, llm_processor  # pylint: disable=redefined-outer-name
):
    """
    Test chat_with_context with stream=True.
    Should return a generator yielding deltas.
    """
    llm_processor.config["stream"] = True
    llm_processor.stream = True  # Also set instance variable
    llm_processor.config["enabled_tools"] = []  # Disable tools for streaming
    llm_processor.extra_params.pop("tools", None)  # Remove tools if present

    # Mock Generator
    chunks = [
        MockChunk("He", is_stream=True),
        MockChunk("llo", is_stream=True),
    ]
    mock_responses.return_value = iter(chunks)

    # Call
    generator = llm_processor.process(
        context="Ctx",
        input_data="Hi",
        chat_history=[]
    )

    # Consume generator
    results = list(generator)

    # Assertions
    assert len(results) == 2
    assert results[0].content == "He"
    assert results[1].content == "llo"


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.responses")
@patch("openedx_ai_extensions.processors.llm.llm_processor.completion")
def test_chat_with_context_streaming_non_openai_uses_completion(
    mock_completion, mock_responses, user_session, settings  # pylint: disable=redefined-outer-name
):
    """
    Test that chat_with_context for a non-OpenAI provider (e.g. Anthropic) calls
    completion() instead of responses() when streaming=True.

    LiteLLM's Responses API streaming translation does not surface tool-call
    events for non-native providers, so adapt_to_provider automatically converts
    the params to Completion API format (input → messages) and
    _call_responses_wrapper detects the 'messages' key to take the completion path.

    The result must be a generator of encoded bytes (same as summarize_content).
    """
    settings.AI_EXTENSIONS = {
        "default": {
            "MODEL": "anthropic/claude-3-5-sonnet",
            "API_KEY": "test-anthropic-key",
        }
    }

    config = {
        "LLMProcessor": {
            "function": "chat_with_context",
            "stream": True,
        }
    }
    processor = LLMProcessor(config=config, user_session=user_session)
    processor.stream = True
    processor.extra_params.pop("tools", None)

    chunks = [
        MockChunk("Hi", is_stream=True),
        MockChunk(" there", is_stream=True),
    ]
    mock_completion.return_value = iter(chunks)

    generator = processor.process(
        context="Course Context",
        input_data="Hello Anthropic",
        chat_history=[]
    )
    results = list(generator)

    # completion() must have been used — responses() must NOT be called
    mock_responses.assert_not_called()
    mock_completion.assert_called_once()

    # Params passed to completion() must use 'messages', not 'input'
    call_kwargs = mock_completion.call_args[1]
    assert "messages" in call_kwargs, "Expected Completion API format (messages key)"
    assert "input" not in call_kwargs, "Responses API key 'input' must not be present"

    # Output is encoded bytes (handled by _handle_streaming_completion)
    assert results[0] == b"Hi"
    assert results[1] == b" there"


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.completion")
def test_summarize_content_streaming(
    mock_completion, llm_processor  # pylint: disable=redefined-outer-name
):
    """
    Test summarize_content with stream=True.
    Should return a generator yielding encoded bytes.
    """
    llm_processor.config["function"] = "summarize_content"
    llm_processor.config["stream"] = True
    llm_processor.stream = True  # Also set instance variable
    llm_processor.config["enabled_tools"] = []  # Disable tools for streaming
    llm_processor.extra_params.pop("tools", None)  # Remove tools if present

    # Mock Generator
    chunks = [
        MockChunk("Sum", is_stream=True),
        MockChunk("mary", is_stream=True),
    ]
    mock_completion.return_value = iter(chunks)

    # Call
    generator = llm_processor.process(context="Text")

    # Consume generator
    results = list(generator)

    # Assertions
    assert results[0] == b"Sum"
    assert results[1] == b"mary"


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.responses")
def test_chat_error_handling(
    mock_responses, llm_processor  # pylint: disable=redefined-outer-name
):
    """
    Test API error handling in chat (non-streaming).
    """
    mock_responses.side_effect = Exception("API connection failed")
    with pytest.raises(Exception):
        llm_processor.process(context="Ctx", input_data="Hi", chat_history=[])


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.completion")
def test_completion_error_handling_stream(
    mock_completion, llm_processor  # pylint: disable=redefined-outer-name
):
    """
    Test API error handling during streaming completion.
    """
    llm_processor.config["function"] = "summarize_content"
    llm_processor.config["stream"] = True
    llm_processor.stream = True  # Also set instance variable
    llm_processor.config["enabled_tools"] = []  # Disable tools for streaming
    llm_processor.extra_params.pop("tools", None)  # Remove tools if present

    # Mock generator that raises error mid-stream
    def error_generator():
        yield MockChunk("Start", is_stream=True)
        raise Exception("Stream cut off")

    mock_completion.return_value = error_generator()

    generator = llm_processor.process(context="Text")
    results = list(generator)

    # Should yield content then the error message
    assert results[0] == b"Start"
    assert b'"error_in_stream": true' in results[1]


# ============================================================================
# MCP Configuration Tests
# ============================================================================

@pytest.mark.django_db
def test_mcp_configs_empty_when_not_specified(user_session, settings):  # pylint: disable=redefined-outer-name
    """
    Test that MCP configs are empty when not specified in config.
    """
    settings.AI_EXTENSIONS = {
        "default": {
            "MODEL": "openai/gpt-3.5-turbo",
            "API_KEY": "test-key"
        }
    }
    settings.AI_EXTENSIONS_MCP_CONFIGS = {}

    config = {
        "LLMProcessor": {
            "function": "chat_with_context",
            "model": "gpt-3.5-turbo",
        }
    }
    processor = LLMProcessor(config=config, user_session=user_session)

    assert processor.mcp_configs == {}
    assert "tools" not in processor.extra_params


@pytest.mark.django_db
def test_mcp_configs_filtering_from_allowed_list(user_session, settings):  # pylint: disable=redefined-outer-name
    """
    Test that MCP configs are filtered based on the allowed mcp_configs list.
    """
    settings.AI_EXTENSIONS = {
        "default": {
            "MODEL": "openai/gpt-3.5-turbo",
            "API_KEY": "test-key"
        }
    }
    settings.AI_EXTENSIONS_MCP_CONFIGS = {
        "server1": {
            "command": "python",
            "args": ["-m", "server1"],
        },
        "server2": {
            "command": "node",
            "args": ["server2.js"],
        },
        "server3": {
            "command": "python",
            "args": ["-m", "server3"],
        }
    }

    config = {
        "LLMProcessor": {
            "function": "chat_with_context",
            "model": "gpt-3.5-turbo",
            "mcp_configs": ["server1", "server3"]  # Only allow server1 and server3
        }
    }
    processor = LLMProcessor(config=config, user_session=user_session)

    # Should only include server1 and server3
    assert len(processor.mcp_configs) == 2
    assert "server1" in processor.mcp_configs
    assert "server3" in processor.mcp_configs
    assert "server2" not in processor.mcp_configs


@pytest.mark.django_db
def test_mcp_configs_tools_parameter_generation(user_session, settings):  # pylint: disable=redefined-outer-name
    """
    Test that MCP configs are properly converted to tools parameter format.
    """
    settings.AI_EXTENSIONS = {
        "default": {
            "MODEL": "openai/gpt-3.5-turbo",
            "API_KEY": "test-key"
        }
    }
    settings.AI_EXTENSIONS_MCP_CONFIGS = {
        "context7": {
            "command": "uvx",
            "args": ["context7"],
            "env": {"API_KEY": "secret"}
        }
    }

    config = {
        "LLMProcessor": {
            "function": "chat_with_context",
            "model": "gpt-3.5-turbo",
            "mcp_configs": ["context7"]
        }
    }
    processor = LLMProcessor(config=config, user_session=user_session)

    # Verify tools parameter is generated correctly
    assert "tools" in processor.extra_params
    tools = processor.extra_params["tools"]
    assert len(tools) == 1
    assert tools[0]["type"] == "mcp"
    assert tools[0]["server_label"] == "context7"
    assert tools[0]["command"] == "uvx"
    assert tools[0]["args"] == ["context7"]
    assert tools[0]["env"] == {"API_KEY": "secret"}


@pytest.mark.django_db
def test_mcp_configs_empty_allowed_list(user_session, settings):  # pylint: disable=redefined-outer-name
    """
    Test that MCP configs remain empty when allowed list is empty.
    """
    settings.AI_EXTENSIONS = {
        "default": {
            "MODEL": "openai/gpt-3.5-turbo",
            "API_KEY": "test-key"
        }
    }
    settings.AI_EXTENSIONS_MCP_CONFIGS = {
        "server1": {
            "command": "python",
            "args": ["-m", "server1"],
        }
    }

    config = {
        "LLMProcessor": {
            "function": "chat_with_context",
            "model": "gpt-3.5-turbo",
            "mcp_configs": []  # Empty list
        }
    }
    processor = LLMProcessor(config=config, user_session=user_session)

    assert processor.mcp_configs == {}
    assert "tools" not in processor.extra_params


# ============================================================================
# Custom Prompt Tests
# ============================================================================

@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.completion")
def test_call_with_custom_prompt_function(
    mock_completion, user_session, settings  # pylint: disable=redefined-outer-name
):
    """
    Test the call_with_custom_prompt function explicitly.
    """
    settings.AI_EXTENSIONS = {
        "default": {
            "MODEL": "openai/gpt-3.5-turbo",
            "API_KEY": "test-key"
        }
    }

    custom_prompt_text = "You are a helpful AI assistant."
    config = {
        "LLMProcessor": {
            "function": "call_with_custom_prompt",
            "model": "gpt-3.5-turbo",
            "prompt": custom_prompt_text,
        }
    }
    processor = LLMProcessor(config=config, user_session=user_session)

    mock_resp_obj = MockChunk("Custom response", is_stream=False)
    mock_completion.return_value = mock_resp_obj

    result = processor.process(input_data="User's custom input")

    assert result["status"] == "success"
    assert result["response"] == "Custom response"
    mock_completion.assert_called_once()

    # Verify the custom prompt is used in the system role
    call_kwargs = mock_completion.call_args[1]
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == custom_prompt_text


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.completion")
def test_call_with_custom_prompt_when_function_not_specified(
    mock_completion, user_session, settings  # pylint: disable=redefined-outer-name
):
    """
    Test that when no function is specified, it defaults to call_with_custom_prompt.
    """
    settings.AI_EXTENSIONS = {
        "default": {
            "MODEL": "openai/gpt-3.5-turbo",
            "API_KEY": "test-key"
        }
    }

    custom_prompt_text = "Default custom prompt for testing."
    config = {
        "LLMProcessor": {
            # No "function" key specified
            "model": "gpt-3.5-turbo",
            "prompt": custom_prompt_text,
        }
    }
    processor = LLMProcessor(config=config, user_session=user_session)

    mock_resp_obj = MockChunk("Default function response", is_stream=False)
    mock_completion.return_value = mock_resp_obj

    result = processor.process(input_data="Test input")

    assert result["status"] == "success"
    assert result["response"] == "Default function response"


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.completion")
def test_custom_prompt_overrides_system_role_in_completion(
    mock_completion, user_session, settings  # pylint: disable=redefined-outer-name
):
    """
    Test that custom_prompt from config overrides the default system role.
    """
    settings.AI_EXTENSIONS = {
        "default": {
            "MODEL": "openai/gpt-3.5-turbo",
            "API_KEY": "test-key"
        }
    }

    custom_prompt_text = "You are a specialized math tutor. Be concise and precise."
    config = {
        "LLMProcessor": {
            "function": "call_with_custom_prompt",
            "model": "gpt-3.5-turbo",
            "prompt": custom_prompt_text,  # This gets set as self.custom_prompt
        }
    }
    processor = LLMProcessor(config=config, user_session=user_session)

    mock_resp_obj = MockChunk("Math answer", is_stream=False)
    mock_completion.return_value = mock_resp_obj

    result = processor.process(input_data="What is 2+2?")

    assert result["status"] == "success"

    # Verify the custom prompt is used instead of default
    call_kwargs = mock_completion.call_args[1]
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == custom_prompt_text


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.responses")
def test_custom_prompt_in_chat_with_context(
    mock_responses, user_session, settings  # pylint: disable=redefined-outer-name
):
    """
    Test that custom_prompt is used in chat_with_context function.
    """
    settings.AI_EXTENSIONS = {
        "default": {
            "MODEL": "openai/gpt-3.5-turbo",
            "API_KEY": "test-key"
        }
    }

    custom_prompt_text = "You are a coding assistant specialized in Python."
    config = {
        "LLMProcessor": {
            "function": "chat_with_context",
            "model": "gpt-3.5-turbo",
            "prompt": custom_prompt_text,
        }
    }
    processor = LLMProcessor(config=config, user_session=user_session)

    mock_resp_obj = MockChunk("Here's a Python solution", is_stream=False)
    mock_responses.return_value = mock_resp_obj

    result = processor.process(
        context="Python course",
        input_data="How do I use list comprehensions?",
        chat_history=[]
    )

    assert result["status"] == "success"

    # Verify the custom prompt is used
    call_kwargs = mock_responses.call_args[1]
    input_msgs = call_kwargs["input"]
    assert input_msgs[0]["role"] == "system"
    assert input_msgs[0]["content"] == custom_prompt_text


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.completion")
def test_call_with_custom_prompt_streaming(
    mock_completion, user_session, settings  # pylint: disable=redefined-outer-name
):
    """
    Test call_with_custom_prompt with streaming enabled.
    """
    settings.AI_EXTENSIONS = {
        "default": {
            "MODEL": "openai/gpt-3.5-turbo",
            "API_KEY": "test-key"
        }
    }

    custom_prompt_text = "You are a streaming assistant."
    config = {
        "LLMProcessor": {
            "function": "call_with_custom_prompt",
            "model": "gpt-3.5-turbo",
            "stream": True,
            "prompt": custom_prompt_text,
        }
    }
    processor = LLMProcessor(config=config, user_session=user_session)

    # Mock streaming chunks
    chunks = [
        MockChunk("Streaming ", is_stream=True),
        MockChunk("response", is_stream=True),
    ]
    mock_completion.return_value = iter(chunks)

    generator = processor.process(input_data="Test streaming input")

    # Consume generator
    results = list(generator)

    # Assertions for streaming
    assert len(results) == 2
    assert results[0] == b"Streaming "
    assert results[1] == b"response"


@pytest.mark.django_db
def test_call_with_custom_prompt_missing_prompt_raises_error(
    user_session, settings  # pylint: disable=redefined-outer-name
):
    """
    Test that call_with_custom_prompt raises ValueError when prompt is not provided.
    """
    settings.AI_EXTENSIONS = {
        "default": {
            "MODEL": "openai/gpt-3.5-turbo",
            "API_KEY": "test-key"
        }
    }

    config = {
        "LLMProcessor": {
            "function": "call_with_custom_prompt",
            "model": "gpt-3.5-turbo",
            # No "prompt" key provided
        }
    }
    processor = LLMProcessor(config=config, user_session=user_session)

    with pytest.raises(ValueError, match="Custom prompt not provided in configuration"):
        processor.process(input_data="Test input")


# ============================================================================
# LLMProcessor.fetch_remote_thread Tests
# ============================================================================


@pytest.mark.django_db
class TestFetchRemoteThread:
    """Tests for fetch_remote_thread, _extract_input_item, _extract_output_items."""

    def _make_processor(self, user_session, settings):
        """Create a processor for testing."""
        settings.AI_EXTENSIONS = {
            "default": {"MODEL": "openai/gpt-3.5-turbo", "API_KEY": "test-key"}
        }
        config = {
            "LLMProcessor": {"function": "chat_with_context", "model": "gpt-3.5-turbo"}
        }
        return LLMProcessor(config=config, user_session=user_session)

    @patch("openedx_ai_extensions.processors.llm.llm_processor.list_input_items")
    @patch("openedx_ai_extensions.processors.llm.llm_processor.get_responses")
    def test_fetch_single_response(self, mock_get, mock_list, user_session, settings):
        """Test fetching a single-response thread."""
        processor = self._make_processor(user_session, settings)

        mock_resp = Mock()
        mock_resp.id = "resp-1"
        mock_resp.created_at = 1700000000
        mock_resp.model = "gpt-4"
        mock_resp.previous_response_id = None
        mock_usage = Mock()
        mock_usage.total_tokens = 42
        mock_resp.usage = mock_usage
        mock_resp.output = []

        mock_get.return_value = mock_resp
        mock_list.return_value = {"data": []}

        result = processor.fetch_remote_thread("resp-1")

        assert len(result) == 1
        assert result[0]["id"] == "resp-1"
        assert result[0]["model"] == "gpt-4"
        assert result[0]["tokens"] == 42

    @patch("openedx_ai_extensions.processors.llm.llm_processor.list_input_items")
    @patch("openedx_ai_extensions.processors.llm.llm_processor.get_responses")
    def test_fetch_chained_responses(self, mock_get, mock_list, user_session, settings):
        """Test fetching a multi-response chain (follows previous_response_id)."""
        processor = self._make_processor(user_session, settings)

        resp2 = Mock(id="resp-2", created_at=1700000002, model="gpt-4",
                     previous_response_id="resp-1", usage=None, output=[])
        resp1 = Mock(id="resp-1", created_at=1700000001, model="gpt-4",
                     previous_response_id=None, usage=None, output=[])

        mock_get.side_effect = [resp2, resp1]
        mock_list.return_value = {"data": []}

        result = processor.fetch_remote_thread("resp-2")

        assert len(result) == 2
        # Should be chronological (reversed)
        assert result[0]["id"] == "resp-1"
        assert result[1]["id"] == "resp-2"

    @patch("openedx_ai_extensions.processors.llm.llm_processor.list_input_items")
    @patch("openedx_ai_extensions.processors.llm.llm_processor.get_responses")
    def test_fetch_handles_api_error(  # pylint: disable=unused-argument
        self, mock_get, mock_list, user_session, settings,
    ):
        """Test graceful handling of API errors."""
        processor = self._make_processor(user_session, settings)
        mock_get.side_effect = Exception("API timeout")

        result = processor.fetch_remote_thread("resp-1")

        assert len(result) == 1
        assert "error" in result[0]
        assert "API timeout" in result[0]["error"]

    @patch("openedx_ai_extensions.processors.llm.llm_processor.list_input_items")
    @patch("openedx_ai_extensions.processors.llm.llm_processor.get_responses")
    def test_fetch_no_created_at(self, mock_get, mock_list, user_session, settings):
        """Test response without created_at timestamp."""
        processor = self._make_processor(user_session, settings)

        mock_resp = Mock(id="resp-1", created_at=None, model="gpt-4",
                         previous_response_id=None, usage=None, output=[])
        mock_get.return_value = mock_resp
        mock_list.return_value = {"data": []}

        result = processor.fetch_remote_thread("resp-1")
        assert result[0]["created_at"] is None

    @patch("openedx_ai_extensions.processors.llm.llm_processor.list_input_items")
    @patch("openedx_ai_extensions.processors.llm.llm_processor.get_responses")
    def test_fetch_with_input_items(self, mock_get, mock_list, user_session, settings):
        """Test that input items are extracted."""
        processor = self._make_processor(user_session, settings)

        mock_resp = Mock(id="resp-1", created_at=None, model="gpt-4",
                         previous_response_id=None, usage=None, output=[])
        mock_get.return_value = mock_resp
        mock_list.return_value = {
            "data": [{"role": "user", "content": "Hello", "type": "message"}]
        }

        result = processor.fetch_remote_thread("resp-1")
        assert len(result[0]["input"]) == 1
        assert result[0]["input"][0]["role"] == "user"

    @patch("openedx_ai_extensions.processors.llm.llm_processor.list_input_items")
    @patch("openedx_ai_extensions.processors.llm.llm_processor.get_responses")
    def test_fetch_list_input_items_non_dict(self, mock_get, mock_list, user_session, settings):
        """Test handling when list_input_items returns non-dict."""
        processor = self._make_processor(user_session, settings)

        mock_resp = Mock(id="resp-1", created_at=None, model="gpt-4",
                         previous_response_id=None, usage=None, output=[])
        mock_get.return_value = mock_resp
        mock_list.return_value = "not-a-dict"

        result = processor.fetch_remote_thread("resp-1")
        assert result[0]["input"] == []


class TestExtractInputItem:
    """Tests for _extract_input_item static method."""

    def test_dict_input(self):
        """Test extracting from a dict item."""
        item = {"role": "user", "content": "Hello", "type": "message"}
        result = LLMProcessor._extract_input_item(item)
        assert result == {"type": "message", "role": "user", "content": "Hello"}

    def test_object_input(self):
        """Test extracting from an object item."""
        item = Mock(type="message", role="user", content="Hello")
        result = LLMProcessor._extract_input_item(item)
        assert result["role"] == "user"
        assert result["content"] == "Hello"

    def test_list_content(self):
        """Test extracting when content is a list."""
        item = {"role": "user", "content": [{"text": "Part 1"}, {"text": "Part 2"}], "type": "message"}
        result = LLMProcessor._extract_input_item(item)
        assert result["content"] == "Part 1 Part 2"

    def test_list_content_with_objects(self):
        """Test extracting when content list contains objects."""
        part = Mock(text="Object text")
        item = {"role": "user", "content": [part], "type": "message"}
        result = LLMProcessor._extract_input_item(item)
        assert "Object text" in result["content"]

    def test_none_content_object(self):
        """Test extracting when content is None on an object."""
        item = Mock(type="message", role="user", content=None, text="fallback text")
        result = LLMProcessor._extract_input_item(item)
        assert result["content"] == "fallback text"

    def test_none_content_dict(self):
        """Test extracting when content is None in a dict."""
        item = {"role": "user", "type": "message"}
        result = LLMProcessor._extract_input_item(item)
        assert result["content"] == ""

    def test_function_call_output_uses_output_field(self):
        """function_call_output items use the 'output' field as content (not the missing 'content' field)."""
        item = {
            "type": "function_call_output",
            "call_id": "call_xyz789",
            "output": '{"temperature": 18, "unit": "celsius"}',
        }
        result = LLMProcessor._extract_input_item(item)
        assert "18" in result["content"]
        assert result["type"] == "function_call_output"

    def test_function_call_output_preserves_call_id(self):
        """function_call_output items preserve call_id for correlation with the original function_call."""
        item = {
            "type": "function_call_output",
            "call_id": "call_xyz789",
            "output": "done",
        }
        result = LLMProcessor._extract_input_item(item)
        assert result["call_id"] == "call_xyz789"

    def test_function_call_output_as_object(self):
        """function_call_output also works when the item is an object, not a dict."""
        item = Mock(type="function_call_output", call_id="call_abc", output="result text", content=None)
        result = LLMProcessor._extract_input_item(item)
        assert result["content"] == "result text"
        assert result["call_id"] == "call_abc"


class TestExtractOutputItems:
    """Tests for _extract_output_items static method."""

    def test_message_output(self):
        """Test extracting message output items."""
        block = Mock(type="output_text", text="Hello world")
        output_item = Mock(type="message", content=[block])
        resp = Mock(output=[output_item])

        result = LLMProcessor._extract_output_items(resp)
        assert result == [{"type": "message", "role": "assistant", "content": "Hello world"}]

    def test_function_call_output(self):
        """Test extracting function call output items."""
        output_item = Mock(type="function_call", arguments='{"q":"test"}')
        output_item.name = "search"  # 'name' is special on Mock; set as attribute
        resp = Mock(output=[output_item])

        result = LLMProcessor._extract_output_items(resp)
        assert len(result) == 1
        assert result[0]["role"] == "tool_call"
        assert "search" in result[0]["content"]

    def test_function_call_has_type_field(self):
        """function_call output items carry type='function_call', not 'message'."""
        output_item = Mock(type="function_call", arguments='{"location":"Paris"}', call_id="call_xyz")
        output_item.name = "get_weather"  # 'name' is special on Mock; set as attribute
        resp = Mock(output=[output_item])

        result = LLMProcessor._extract_output_items(resp)
        assert result[0]["type"] == "function_call"

    def test_function_call_preserves_structured_fields(self):
        """function_call output items expose name, arguments, and call_id as separate fields."""
        output_item = Mock(type="function_call", arguments='{"location": "Paris"}', call_id="call_xyz789")
        output_item.name = "get_weather"  # 'name' is special on Mock; set as attribute
        resp = Mock(output=[output_item])

        result = LLMProcessor._extract_output_items(resp)
        item = result[0]
        assert item["name"] == "get_weather"
        assert item["arguments"] == '{"location": "Paris"}'
        assert item["call_id"] == "call_xyz789"
        # Content is still a human-readable fallback string for renderers that don't know about tool calls.
        assert "get_weather" in item["content"]
        assert "Paris" in item["content"]

    def test_reasoning_item_included_with_summary(self):
        """reasoning output items are included using their summary text as content."""
        summary = Mock(text="I need to check the weather in Paris.")
        output_item = Mock(type="reasoning", summary=[summary])
        resp = Mock(output=[output_item])

        result = LLMProcessor._extract_output_items(resp)
        assert len(result) == 1
        assert result[0]["type"] == "reasoning"
        assert result[0]["role"] == "reasoning"
        assert "Paris" in result[0]["content"]

    def test_reasoning_item_with_dict_summary(self):
        """reasoning items whose summary entries are plain dicts (as returned by some providers) work."""
        output_item = Mock(type="reasoning", summary=[{"type": "summary_text", "text": "Thinking..."}])
        resp = Mock(output=[output_item])

        result = LLMProcessor._extract_output_items(resp)
        assert len(result) == 1
        assert result[0]["content"] == "Thinking..."

    def test_reasoning_item_without_summary_skipped(self):
        """reasoning items with no summary text produce no output entry."""
        output_item = Mock(type="reasoning", summary=[])
        resp = Mock(output=[output_item])

        result = LLMProcessor._extract_output_items(resp)
        assert not result

    def test_unknown_type_silently_dropped(self):
        """Output items of unknown types (file_search_call, web_search_call, etc.) are silently dropped."""
        output_item = Mock(type="file_search_call")
        resp = Mock(output=[output_item])

        result = LLMProcessor._extract_output_items(resp)
        assert not result

    def test_empty_output(self):
        """Test with no output items."""
        resp = Mock(output=[])
        result = LLMProcessor._extract_output_items(resp)
        assert not result

    def test_none_output(self):
        """Test with None output."""
        resp = Mock(output=None)
        result = LLMProcessor._extract_output_items(resp)
        assert not result

    def test_skips_non_output_text_blocks(self):
        """Test that non-output_text blocks in message items are skipped."""
        block = Mock(type="image", text="ignored")
        output_item = Mock(type="message", content=[block])
        resp = Mock(output=[output_item])

        result = LLMProcessor._extract_output_items(resp)
        assert not result


# --- LLMProcessor __init__ kwargs pass-through test ---
class TestLLMProcessorInit(unittest.TestCase):
    """
    Test that LLMProcessor.__init__ correctly passes kwargs to LitellmProcessor.__init__.
    """
    @patch('openedx_ai_extensions.processors.llm.llm_processor.LitellmProcessor.__init__', return_value=None)
    def test_llmprocessor_init_passes_kwargs(self, mock_litellm_init):
        """
        Test that LLMProcessor.__init__ passes all kwargs to LitellmProcessor.__init__.
        """
        config = {'foo': 'bar'}
        user_session = object()
        extra_params = {
            'temperature': 0.7,
            'model': 'gpt-4',
            'max_tokens': 150,
            'api_key': 'test-key',
            'response_format': {'type': 'json'}
        }
        processor = LLMProcessor(config, user_session, extra_params=extra_params)    # pylint: disable=unused-variable
        mock_litellm_init.assert_called_once_with(config, user_session, extra_params)

# ============================================================================
# Streaming Tool Call Tests
# ============================================================================


class MockToolStreamChunk:
    """
    Helper for simulating tool call chunks in a stream.
    Structure follows: chunk.choices[0].delta.tool_calls[...]
    """

    def __init__(self, index, tool_id=None, name=None, arguments=None):
        self.usage = MockUsage(total_tokens=5)

        # 1. Create the function mock
        func_mock = Mock()
        func_mock.name = name
        func_mock.arguments = arguments

        # 2. Create the tool_call mock
        tool_call_mock = Mock()
        tool_call_mock.index = index
        tool_call_mock.id = tool_id
        tool_call_mock.function = func_mock

        # Construct the delta
        delta = MockDelta(content=None, tool_calls=[tool_call_mock])

        # Construct the choice
        self.choices = [MockChoice(delta=delta)]


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.completion")
@patch("openedx_ai_extensions.processors.llm.llm_processor.adapt_to_provider")
def test_streaming_tool_execution_recursion(
    mock_adapt, mock_completion, llm_processor  # pylint: disable=redefined-outer-name
):
    """
    Test that streaming correctly handles tool calls:
    1. Buffers tool call chunks.
    2. Executes the tool.
    3. Recursively calls completion with tool output.
    4. Yields the final content chunks.
    """
    # 1. Setup
    mock_adapt.side_effect = lambda provider, params, **kwargs: params

    # Configure processor for streaming + custom function calling
    llm_processor.config["function"] = "summarize_content"  # Uses _call_completion_wrapper
    llm_processor.config["stream"] = True
    llm_processor.stream = True
    llm_processor.extra_params["tools"] = ["mock_tool"]  # Needs to pass check in init if strict, but mainly for logic

    # 2. Define a Mock Tool
    mock_tool_func = Mock(return_value="tool_result_value")

    # Patch the global AVAILABLE_TOOLS to include our mock
    with patch.dict(AVAILABLE_TOOLS, {"mock_tool": mock_tool_func}):
        # 3. Define Stream Sequences

        # Sequence 1: The Model decides to call "mock_tool" with args {"arg": "val"}
        # Split into multiple chunks to test buffering logic
        tool_chunks = [
            # Chunk 1: ID and Name
            MockToolStreamChunk(index=0, tool_id="call_123", name="mock_tool"),
            # Chunk 2: Start of args
            MockToolStreamChunk(index=0, arguments='{"arg":'),
            # Chunk 3: End of args
            MockToolStreamChunk(index=0, arguments=' "val"}'),
        ]

        # Sequence 2: The Model sees the tool result and generates final text
        content_chunks = [
            MockStreamChunk("Result "),
            MockStreamChunk("is "),
            MockStreamChunk("tool_result_value"),
        ]

        # Configure completion to return the first sequence, then the second
        mock_completion.side_effect = [iter(tool_chunks), iter(content_chunks)]

        # 4. Execute
        generator = llm_processor.process(context="Ctx")
        results = list(generator)

        # 5. Assertions

        # Check final output (byte encoded by _handle_streaming_completion)
        assert b"Result " in results
        assert b"is " in results
        assert b"tool_result_value" in results

        # Check Tool Execution
        mock_tool_func.assert_called_once_with(arg="val")

        # Check Recursion (completion called twice)
        assert mock_completion.call_count == 2

        # Verify second call included the tool output
        second_call_kwargs = mock_completion.call_args_list[1][1]
        messages = second_call_kwargs["messages"]

        # Should have: System, (Context/User), Assistant(ToolCall), Tool(Result)
        # Finding the tool message
        tool_msg = next((m for m in messages if m.get("role") == "tool"), None)
        assert tool_msg is not None
        assert tool_msg["tool_call_id"] == "call_123"
        assert tool_msg["content"] == "tool_result_value"
        assert tool_msg["name"] == "mock_tool"


# ============================================================================
# _completion_with_tools Error Path Tests
# ============================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.completion")
def test_completion_with_tools_unknown_tool_is_skipped(
    mock_completion, llm_processor  # pylint: disable=redefined-outer-name
):
    """
    When a tool call references a function not in AVAILABLE_TOOLS the call is
    silently skipped (logged) and completion proceeds without a tool message.
    """
    mock_completion.return_value = Mock(
        choices=[Mock(message=Mock(content="done", tool_calls=None))],
        usage=Mock(total_tokens=5),
    )
    unknown_call = types.SimpleNamespace(
        id="call_x",
        function=types.SimpleNamespace(name="unknown_tool", arguments='{}'),
    )
    params = {
        "stream": False,
        "messages": [{"role": "system", "content": "sys"}],
        "model": "openai/gpt-4",
    }
    # pylint: disable=protected-access
    response = llm_processor._completion_with_tools([unknown_call], params)

    # No tool message should have been appended
    assert all(m.get("role") != "tool" for m in params["messages"])
    mock_completion.assert_called_once()
    assert response.choices[0].message.content == "done"


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.completion")
def test_completion_with_tools_json_decode_error(
    mock_completion, llm_processor  # pylint: disable=redefined-outer-name
):
    """
    When a tool call carries malformed JSON arguments, json.JSONDecodeError is
    caught, an error string is passed as the tool result, and completion
    continues normally.
    """
    mock_tool = Mock(return_value="ok")
    mock_completion.return_value = Mock(
        choices=[Mock(message=Mock(content="done", tool_calls=None))],
        usage=Mock(total_tokens=5),
    )
    bad_json_call = types.SimpleNamespace(
        id="call_bad",
        function=types.SimpleNamespace(name="mock_tool", arguments="{INVALID JSON}"),
    )
    params = {
        "stream": False,
        "messages": [{"role": "system", "content": "sys"}],
        "model": "openai/gpt-4",
    }
    with patch.dict(AVAILABLE_TOOLS, {"mock_tool": mock_tool}):
        # pylint: disable=protected-access
        llm_processor._completion_with_tools([bad_json_call], params)

    tool_msg = next((m for m in params["messages"] if m.get("role") == "tool"), None)
    assert tool_msg is not None
    assert "Error" in tool_msg["content"]
    mock_tool.assert_not_called()

# ============================================================================
# Threaded Streaming & Tool Call Tests (Responses API)
# ============================================================================


class MockResponseUsage:
    """Helper to mock usage in Responses API."""

    def __init__(self, total):
        self.total_tokens = total


class MockResponsesChunk:
    """Helper to mock chunks specifically for the Responses API stream."""

    def __init__(self, chunk_type, **kwargs):
        self.type = chunk_type
        self.delta = kwargs.get("delta")
        self.item = kwargs.get("item")
        self.response = None
        usage_total = kwargs.get("usage_total")
        response_id = kwargs.get("response_id")
        if usage_total or response_id:
            self.response = Mock(
                usage=MockResponseUsage(usage_total) if usage_total else None,
                id=response_id
            )
        if usage_total:
            self.usage = MockResponseUsage(usage_total)


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.responses")
def test_yield_threaded_stream_text_and_tokens(
    mock_responses, llm_processor, user_session  # pylint: disable=W0621,W0613
):
    """
    Test verifies text yielding and token usage tracking.
    """
    chunks = [
        MockResponsesChunk("response.created", response_id="resp_123"),
        MockResponsesChunk("response.delta", delta="Hello"),
        MockResponsesChunk("response.delta", delta="{}"),
        MockResponsesChunk("response.delta", delta=" world"),
        MockResponsesChunk("response.completed", usage_total=42)
    ]
    # pylint: disable=protected-access
    generator = llm_processor._yield_threaded_stream(iter(chunks))
    results = list(generator)

    assert "Hello" in results
    assert " world" in results
    assert "{}" not in results

    user_session.refresh_from_db()
    assert user_session.remote_response_id == "resp_123"


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.responses")
def test_yield_threaded_stream_recursive_tool_call(
    mock_responses, llm_processor   # pylint: disable=W0621
):
    """
    Test recursive tool execution in threaded stream.
    """
    mock_dice_roll = Mock(return_value="[6]")

    with patch.dict("openedx_ai_extensions.functions.decorators.AVAILABLE_TOOLS",
                    {"roll_dice": mock_dice_roll}):
        item_mock = Mock(
            type="function_call",
            call_id="call_abc",
            arguments='{"n_dice": 1}'
        )
        item_mock.name = "roll_dice"

        stream_a = [
            MockResponsesChunk("response.output_item.done", item=item_mock)
        ]

        stream_b = [
            MockResponsesChunk("response.delta", delta="You rolled a 6")
        ]

        mock_responses.return_value = iter(stream_b)

        params = {"input": [{"role": "user", "content": "Roll dice"}], "stream": True}
        # pylint: disable=protected-access
        generator = llm_processor._yield_threaded_stream(iter(stream_a), params=params)
        results = list(generator)

        assert "Error: Tool not found." not in str(results)

        assert "You rolled a 6" in results

        mock_dice_roll.assert_called_once_with(n_dice=1)

        history = params["input"]
        assert history[1]["type"] == "function_call"
        assert history[1]["name"] == "roll_dice"

        mock_responses.assert_called_once()


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.completion")
def test_llm_processor_streaming_error_marker(mock_completion, workflow_scope, user):
    """Test that LLMProcessor yields an error marker when an exception occurs during streaming."""
    processor_config = {
        "LLMProcessor": {
            "provider": "default",
            "stream": True,
            "prompt": "Test prompt",
        }
    }

    session = AIWorkflowSession.objects.create(
        user=user,
        scope=workflow_scope,
        profile=workflow_scope.profile,
        course_id=workflow_scope.course_id,
    )

    processor = LLMProcessor(processor_config, session)

    # Mock completion to return a generator that raises an exception
    class MockStreamResponse:
        """Mock stream response."""
        def __iter__(self):
            chunk = Mock()
            chunk.choices = [Mock(delta=Mock(content="Partial response"))]
            yield chunk
            raise RuntimeError("Streaming failed midway")

    mock_completion.return_value = MockStreamResponse()

    # Execute streaming
    result = processor.process(input_data="test input")

    chunks = list(result)
    assert b"Partial response" in chunks

    # Check for error marker in the last chunks
    error_marker_found = False
    for chunk in chunks:
        if b"error_in_stream" in chunk:
            error_marker_found = True
            marker_str = chunk.decode("utf-8").strip("|")
            data = json.loads(marker_str)
            assert data["error_in_stream"] is True
            assert data["code"] == "streaming_failed"

    assert error_marker_found


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.responses")
def test_llm_processor_lost_thread_retry(mock_responses, workflow_scope, user):
    """Test that LLMProcessor retries with full history if previous response ID is not found."""
    processor_config = {
        "LLMProcessor": {
            "provider": "default",
            "stream": False,
            "prompt": "Test prompt",
            "function": "chat_with_context",
        }
    }

    session = AIWorkflowSession.objects.create(
        user=user,
        scope=workflow_scope,
        profile=workflow_scope.profile,
        course_id=workflow_scope.course_id,
        remote_response_id="lost-id",
    )

    processor = LLMProcessor(processor_config, session)

    # Mock responses to fail first time and succeed second time
    mock_error = BadRequestError("Previous response not found", model="gpt-4", llm_provider="openai")
    mock_error.code = "previous_response_not_found"

    mock_success = Mock()
    mock_success.id = "new-id"
    item = Mock()
    item.type = "message"
    content_item = Mock()
    content_item.type = "output_text"
    content_item.text = "Success response"
    item.content = [content_item]
    mock_success.output = [item]
    mock_success.usage = Mock(total_tokens=10)

    mock_responses.side_effect = [mock_error, mock_success]

    result = processor.process(input_data="test input")

    assert result["response"] == "Success response"
    assert session.remote_response_id == "new-id"  # Should have been updated with new ID
    assert mock_responses.call_count == 2

    # Verify first call had the lost ID
    args, kwargs = mock_responses.call_args_list[0]
    assert kwargs["previous_response_id"] == "lost-id"

    # Verify second call did NOT have the lost ID
    args, kwargs = mock_responses.call_args_list[1]
    assert "previous_response_id" not in kwargs or kwargs["previous_response_id"] is None


# ============================================================================
# generate_flashcards Tests
# ============================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.completion")
def test_generate_flashcards_success(
    mock_completion, user_session, settings  # pylint: disable=redefined-outer-name
):
    """
    Test that generate_flashcards loads the prompt template, replaces
    placeholders, calls LLM, and returns parsed JSON response.
    """
    settings.AI_EXTENSIONS = {
        "default": {
            "MODEL": "openai/gpt-3.5-turbo",
            "API_KEY": "test-key"
        }
    }

    config = {
        "LLMProcessor": {
            "function": "generate_flashcards",
            "model": "gpt-3.5-turbo",
        }
    }
    processor = LLMProcessor(config=config, user_session=user_session)

    flashcards_json = json.dumps({
        "cards": [
            {"id": "card-1", "question": "What is Python?", "answer": "A programming language."}
        ]
    })
    mock_resp_obj = MockChunk(flashcards_json, is_stream=False)
    mock_completion.return_value = mock_resp_obj

    prompt_template = "Generate {{NUM_CARDS}} flashcards about {{TOPIC}}."
    with patch("builtins.open", mock_open(read_data=prompt_template)):
        result = processor.process(
            input_data={"num_cards": "5", "topic": "Python"},
        )

    assert result["status"] == "success"
    assert isinstance(result["response"], dict)
    assert len(result["response"]["cards"]) == 1
    assert result["response"]["cards"][0]["question"] == "What is Python?"

    # Verify placeholder replacement was applied to the prompt
    call_kwargs = mock_completion.call_args[1]
    messages = call_kwargs["messages"]
    system_msg = messages[0]["content"]
    assert "5" in system_msg
    assert "Python" in system_msg
    assert "{{NUM_CARDS}}" not in system_msg
    assert "{{TOPIC}}" not in system_msg


@pytest.mark.django_db
def test_generate_flashcards_prompt_file_error(
    user_session, settings  # pylint: disable=redefined-outer-name
):
    """
    Test that generate_flashcards returns an error when the prompt file cannot be loaded.
    """
    settings.AI_EXTENSIONS = {
        "default": {
            "MODEL": "openai/gpt-3.5-turbo",
            "API_KEY": "test-key"
        }
    }

    config = {
        "LLMProcessor": {
            "function": "generate_flashcards",
            "model": "gpt-3.5-turbo",
        }
    }
    processor = LLMProcessor(config=config, user_session=user_session)

    with patch("builtins.open", side_effect=FileNotFoundError("prompt file not found")):
        result = processor.process(
            input_data={"num_cards": "5"},
        )

    assert "error" in result
    assert result["error"] == "Failed to load prompt template."


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.completion")
def test_generate_flashcards_llm_api_error(
    mock_completion, user_session, settings  # pylint: disable=redefined-outer-name
):
    """
    Test that generate_flashcards returns an error when the LLM API call fails.
    """
    settings.AI_EXTENSIONS = {
        "default": {
            "MODEL": "openai/gpt-3.5-turbo",
            "API_KEY": "test-key"
        }
    }

    config = {
        "LLMProcessor": {
            "function": "generate_flashcards",
            "model": "gpt-3.5-turbo",
        }
    }
    processor = LLMProcessor(config=config, user_session=user_session)

    mock_completion.side_effect = Exception("API connection refused")

    prompt_template = "Generate {{NUM_CARDS}} flashcards."
    with patch("builtins.open", mock_open(read_data=prompt_template)):
        result = processor.process(
            input_data={"num_cards": "3"},
        )

    assert "error" in result
    assert "API connection refused" in result["error"]


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm.llm_processor.completion")
def test_generate_flashcards_clears_input_data(
    mock_completion, user_session, settings  # pylint: disable=redefined-outer-name
):
    """
    Test that generate_flashcards clears self.input_data before calling the LLM
    (so it's not passed as a user message by _call_completion_wrapper).
    """
    settings.AI_EXTENSIONS = {
        "default": {
            "MODEL": "openai/gpt-3.5-turbo",
            "API_KEY": "test-key"
        }
    }

    config = {
        "LLMProcessor": {
            "function": "generate_flashcards",
            "model": "gpt-3.5-turbo",
        }
    }
    processor = LLMProcessor(config=config, user_session=user_session)

    flashcards_json = json.dumps({"cards": []})
    mock_resp_obj = MockChunk(flashcards_json, is_stream=False)
    mock_completion.return_value = mock_resp_obj

    prompt_template = "Generate {{NUM_CARDS}} flashcards."
    with patch("builtins.open", mock_open(read_data=prompt_template)):
        processor.process(input_data={"num_cards": "3"})

    # input_data should have been cleared before calling _call_completion_wrapper
    assert processor.input_data is None

    # Verify no user message was added (only system message + possibly context)
    call_kwargs = mock_completion.call_args[1]
    messages = call_kwargs["messages"]
    user_messages = [m for m in messages if m.get("role") == "user"]
    assert len(user_messages) == 0
