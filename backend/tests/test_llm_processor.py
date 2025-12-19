"""
Tests for the LLMProcessor module.
"""

from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locator import BlockUsageLocator

from openedx_ai_extensions.processors.llm_processor import LLMProcessor
from openedx_ai_extensions.workflows.models import AIWorkflowSession

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
def user_session(user, course_key, db):  # pylint: disable=redefined-outer-name,unused-argument
    """Create and return a test user session with a valid location."""
    location = BlockUsageLocator(course_key, block_type="vertical", block_id="unit-123")

    return AIWorkflowSession.objects.create(
        user=user,
        course_id=course_key,
        location_id=location,
        local_submission_id="sub-123"
    )


@pytest.fixture
def llm_processor(user_session, settings):  # pylint: disable=redefined-outer-name
    """Create and return an LLMProcessor instance with mocked settings."""
    # Mock AI_EXTENSIONS settings
    settings.AI_EXTENSIONS = {
        "default": {
            "MODEL": "gpt-3.5-turbo",
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
    def __init__(self, content):
        self.content = content


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


# ============================================================================
# Non-Streaming Tests (Standard)
# ============================================================================

@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm_processor.responses")
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
@patch("openedx_ai_extensions.processors.llm_processor.responses")
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
@patch("openedx_ai_extensions.processors.llm_processor.completion")
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
@patch("openedx_ai_extensions.processors.llm_processor.responses")
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
@patch("openedx_ai_extensions.processors.llm_processor.completion")
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
@patch("openedx_ai_extensions.processors.llm_processor.responses")
def test_chat_error_handling(
    mock_responses, llm_processor  # pylint: disable=redefined-outer-name
):
    """
    Test API error handling in chat (non-streaming).
    """
    mock_responses.side_effect = Exception("API connection failed")

    result = llm_processor.process(context="Ctx", input_data="Hi", chat_history=[])

    assert "error" in result
    assert "AI processing failed" in result["error"]
    assert "API connection failed" in result["error"]


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.llm_processor.completion")
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
    assert b"[AI Error: Stream cut off]" in results[1]


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
            "MODEL": "gpt-3.5-turbo",
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
            "MODEL": "gpt-3.5-turbo",
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
            "MODEL": "gpt-3.5-turbo",
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
            "MODEL": "gpt-3.5-turbo",
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
