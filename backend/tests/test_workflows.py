"""
Tests for the `openedx-ai-extensions` workflows module.
"""

import inspect
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.contrib.auth import get_user_model
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locator import BlockUsageLocator

from openedx_ai_extensions.workflows.models import AIWorkflowProfile, AIWorkflowScope, AIWorkflowSession
from openedx_ai_extensions.workflows.orchestrators import BaseOrchestrator
from openedx_ai_extensions.workflows.orchestrators.direct_orchestrator import DirectLLMResponse
from openedx_ai_extensions.workflows.orchestrators.mock_orchestrator import MockResponse, MockStreamResponse
from openedx_ai_extensions.workflows.orchestrators.threaded_orchestrator import ThreadedLLMResponse

User = get_user_model()

# Mock the submissions module before any imports that depend on it
sys.modules["submissions"] = MagicMock()
sys.modules["submissions.api"] = MagicMock()


@pytest.fixture
def user(db):  # pylint: disable=unused-argument
    """
    Create and return a test user.
    """
    return User.objects.create_user(
        username="testuser", email="testuser@example.com", password="password123"
    )


@pytest.fixture
def course_key():
    """
    Create and return a test course key.
    """
    return CourseKey.from_string("course-v1:edX+DemoX+Demo_Course")


@pytest.fixture
def workflow_profile(db):  # pylint: disable=unused-argument
    """
    Create a real AIWorkflowProfile instance.
    """
    profile = AIWorkflowProfile.objects.create(
        slug="test-summarize",
        description="Test summarization workflow",
        base_filepath="base/summary.json",
        content_patch='{}'
    )
    return profile


@pytest.fixture
def workflow_scope(workflow_profile, course_key):  # pylint: disable=redefined-outer-name
    """
    Create a real AIWorkflowScope instance.
    """
    scope = AIWorkflowScope.objects.create(
        location_regex=".*test_unit.*",
        course_id=course_key,
        service_variant="lms",
        profile=workflow_profile,
        enabled=True,
        ui_slot_selector_id="test-slot",
    )
    return scope


# ============================================================================
# AIWorkflowProfile Tests
# ============================================================================


@pytest.mark.django_db
def test_workflow_profile_str():
    """
    Test AIWorkflowProfile string representation.
    """
    profile = AIWorkflowProfile.objects.create(
        slug="test-profile",
        base_filepath="base/default.json"
    )
    assert "test-profile" in str(profile)
    assert "base/default.json" in str(profile)


@pytest.mark.django_db
def test_workflow_profile_content_patch_dict():
    """
    Test AIWorkflowProfile.content_patch_dict property.
    """
    profile = AIWorkflowProfile.objects.create(
        slug="test-profile",
        base_filepath="base/default.json",
        content_patch='{"key": "value"}'
    )
    assert profile.content_patch_dict == {"key": "value"}


@pytest.mark.django_db
def test_workflow_profile_content_patch_dict_empty():
    """
    Test AIWorkflowProfile.content_patch_dict with empty patch.
    """
    profile = AIWorkflowProfile.objects.create(
        slug="test-profile",
        base_filepath="base/default.json",
        content_patch=''
    )
    assert profile.content_patch_dict == {}


# ============================================================================
# AIWorkflowScope Tests
# ============================================================================


@pytest.mark.django_db
def test_workflow_scope_str(workflow_scope, course_key):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflowScope string representation.
    """
    result = str(workflow_scope)
    assert str(course_key) in result


@pytest.mark.django_db
def test_workflow_scope_get_profile(course_key):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflowScope.get_profile class method.
    """
    # Call get_profile with course_id and location_id
    result = AIWorkflowScope.get_profile(
        course_id=course_key,
        location_id="test_location"
    )

    # Should return None or a scope depending on configuration
    # Just verify no exception is raised
    assert result is None or isinstance(result, AIWorkflowScope)


@pytest.mark.django_db
def test_workflow_scope_execute(workflow_scope, user):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflowScope.execute method.
    """
    # Update profile to use MockResponse orchestrator via content_patch
    workflow_scope.profile.content_patch = '{"orchestrator_class": "MockResponse"}'
    workflow_scope.profile.save()

    if hasattr(workflow_scope.profile, '_config'):
        del workflow_scope.profile._config

    target = "openedx_ai_extensions.workflows.orchestrators.mock_orchestrator.MockResponse.run"
    with patch(target) as mock_run:
        mock_run.return_value = {"status": "completed", "response": "Test"}

        running_context = {"location_id": None, "course_id": workflow_scope.course_id}
        result = workflow_scope.execute("test input", "run", user, running_context)

        # Should return result or error
        assert "status" in result
        mock_run.assert_called_once()


# ============================================================================
# AIWorkflowSession Tests
# ============================================================================


@pytest.mark.django_db
def test_workflow_session_get_or_create(
    user, course_key, workflow_scope, workflow_profile
):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflowSession.objects.get_or_create with real Django ORM.
    """
    location = BlockUsageLocator(course_key, block_type="vertical", block_id="unit-123")

    session, created = AIWorkflowSession.objects.get_or_create(
        user=user,
        scope=workflow_scope,
        profile=workflow_profile,
        defaults={
            "course_id": course_key,
            "location_id": location,
        },
    )

    assert session.user == user
    assert session.course_id == course_key
    assert session.location_id == location
    assert session.scope == workflow_scope
    assert session.profile == workflow_profile
    assert created is True

    # Test retrieving existing session
    session2, created2 = AIWorkflowSession.objects.get_or_create(
        user=user,
        scope=workflow_scope,
        profile=workflow_profile,
        defaults={
            "course_id": course_key,
            "location_id": location,
        },
    )

    assert session.id == session2.id
    assert created2 is False


@pytest.mark.django_db
def test_workflow_session_save(
    user, course_key, workflow_scope, workflow_profile
):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflowSession.save method with real Django ORM.
    """
    location = BlockUsageLocator(course_key, block_type="vertical", block_id="unit-123")

    session = AIWorkflowSession(
        user=user,
        scope=workflow_scope,
        profile=workflow_profile,
        course_id=course_key,
        location_id=location,
        local_submission_id="submission-uuid",
    )

    session.save()

    # Verify session was saved to database
    assert session.id is not None
    retrieved_session = AIWorkflowSession.objects.get(id=session.id)
    assert retrieved_session.user == user
    assert retrieved_session.local_submission_id == "submission-uuid"


@pytest.mark.django_db
def test_workflow_session_delete(
    user, course_key, workflow_scope, workflow_profile
):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflowSession.delete method with real Django ORM.
    """
    location = BlockUsageLocator(course_key, block_type="vertical", block_id="unit-123")

    session = AIWorkflowSession(
        user=user,
        scope=workflow_scope,
        profile=workflow_profile,
        course_id=course_key,
        location_id=location,
    )
    session.save()
    session_id = session.id

    # Verify session exists
    assert AIWorkflowSession.objects.filter(id=session_id).exists()

    session.delete()

    # Verify session was deleted
    assert not AIWorkflowSession.objects.filter(id=session_id).exists()


# ============================================================================
# Orchestrators Tests
# ============================================================================


@pytest.mark.django_db
def test_base_orchestrator_initialization(workflow_scope, user):  # pylint: disable=redefined-outer-name
    """
    Test BaseOrchestrator initialization.
    """
    context = {"location_id": None, "course_id": workflow_scope.course_id}
    orchestrator = BaseOrchestrator(workflow=workflow_scope, user=user, context=context)

    assert orchestrator.workflow == workflow_scope


@pytest.mark.django_db
def test_base_orchestrator_run_not_implemented(workflow_scope, user):  # pylint: disable=redefined-outer-name
    """
    Test BaseOrchestrator.run raises NotImplementedError.
    """
    context = {"location_id": None, "course_id": workflow_scope.course_id}
    orchestrator = BaseOrchestrator(workflow=workflow_scope, user=user, context=context)

    with pytest.raises(NotImplementedError):
        orchestrator.run({})


@pytest.mark.django_db
def test_mock_response_orchestrator(workflow_scope, user):  # pylint: disable=redefined-outer-name
    """
    Test MockResponse orchestrator.
    """
    # Mock the workflow to have location_id and action attributes
    workflow_scope.location_id = None
    workflow_scope.action = "test_action"
    context = {"location_id": None, "course_id": workflow_scope.course_id}
    orchestrator = MockResponse(workflow=workflow_scope, user=user, context=context)
    result = orchestrator.run({})

    assert result["status"] == "completed"
    assert "Mock response" in result["response"]


@pytest.mark.django_db
def test_mock_stream_response_orchestrator(workflow_scope, user):  # pylint: disable=redefined-outer-name
    """
    Test MockStreamResponse orchestrator with streaming.
    """
    # Mock the workflow to have location_id and action attributes
    workflow_scope.location_id = None
    workflow_scope.action = "test_action"
    context = {"location_id": None, "course_id": workflow_scope.course_id}
    orchestrator = MockStreamResponse(workflow=workflow_scope, user=user, context=context)
    result = orchestrator.run({})

    # Verify it returns a generator
    assert inspect.isgenerator(result), "Expected a generator from MockStreamResponse"

    # Consume the generator and collect chunks
    chunks = []
    for chunk in result:
        assert isinstance(chunk, bytes), "Expected bytes from stream"
        chunks.append(chunk)

    # Decode and verify content
    full_response = b"".join(chunks).decode("utf-8")
    assert len(full_response) > 0, "Expected non-empty response"
    assert "streaming function" in full_response
    assert "incremental chunks" in full_response
    assert "real-time consumption" in full_response


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.LLMProcessor")
def test_direct_llm_response_orchestrator_success(
    mock_llm_processor_class,
    mock_openedx_processor_class,
    workflow_scope,  # pylint: disable=redefined-outer-name
    user,  # pylint: disable=redefined-outer-name
):
    """
    Test DirectLLMResponse orchestrator with successful execution.
    """
    # Mock OpenEdXProcessor
    mock_openedx = Mock()
    mock_openedx.process.return_value = {
        "location_id": "unit-123",
        "display_name": "Test Unit",
        "blocks": [],
    }
    mock_openedx_processor_class.return_value = mock_openedx

    # Mock LLMProcessor
    mock_llm = Mock()
    mock_llm.process.return_value = {
        "response": "This is a summary",
    }
    mock_llm.get_usage.return_value = None
    mock_llm_processor_class.return_value = mock_llm

    # Mock the workflow to have location_id and action attributes
    workflow_scope.location_id = None
    workflow_scope.action = "test_action"
    context = {"location_id": None, "course_id": workflow_scope.course_id}
    orchestrator = DirectLLMResponse(workflow=workflow_scope, user=user, context=context)
    result = orchestrator.run({})

    assert result["status"] == "completed"
    assert result["response"] == "This is a summary"


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
def test_direct_llm_response_orchestrator_openedx_error(
    mock_openedx_processor_class,
    workflow_scope,  # pylint: disable=redefined-outer-name
    user,  # pylint: disable=redefined-outer-name
):
    """
    Test DirectLLMResponse orchestrator with OpenEdXProcessor error.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"error": "Failed to load unit"}
    mock_openedx_processor_class.return_value = mock_openedx

    # Mock the workflow to have location_id attribute
    workflow_scope.location_id = None
    context = {"location_id": None, "course_id": workflow_scope.course_id}
    orchestrator = DirectLLMResponse(workflow=workflow_scope, user=user, context=context)
    result = orchestrator.run({})

    assert "error" in result
    assert result["status"] == "OpenEdXProcessor error"


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.LLMProcessor")
def test_direct_llm_response_orchestrator_llm_error(
    mock_llm_processor_class,
    mock_openedx_processor_class,
    workflow_scope,  # pylint: disable=redefined-outer-name
    user,  # pylint: disable=redefined-outer-name
):
    """
    Test DirectLLMResponse orchestrator with LLMProcessor error.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"location_id": "unit-123"}
    mock_openedx_processor_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.process.return_value = {"error": "AI API error"}
    mock_llm_processor_class.return_value = mock_llm

    # Mock the workflow to have location_id attribute
    workflow_scope.location_id = None
    context = {"location_id": None, "course_id": workflow_scope.course_id}
    orchestrator = DirectLLMResponse(workflow=workflow_scope, user=user, context=context)
    result = orchestrator.run({})

    assert "error" in result
    assert result["status"] == "LLMProcessor error"


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.logger")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.LLMProcessor")
def test_stream_and_emit_generator_exception(
    mock_llm_processor_class,
    mock_openedx_processor_class,
    mock_logger,
    workflow_scope,  # pylint: disable=redefined-outer-name
    user,  # pylint: disable=redefined-outer-name
):
    """
    Test that _stream_and_emit catches exceptions raised by the generator,
    yields an encoded error chunk, and still emits the workflow event.
    """
    def broken_generator():
        yield b"partial"
        raise RuntimeError("stream blew up")

    mock_openedx = Mock()
    mock_openedx.process.return_value = {"location_id": "unit-123"}
    mock_openedx_processor_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.process.return_value = broken_generator()
    mock_llm.get_usage.return_value = None
    mock_llm_processor_class.return_value = mock_llm

    workflow_scope.location_id = None
    workflow_scope.action = "test_action"
    context = {"location_id": None, "course_id": workflow_scope.course_id}
    orchestrator = DirectLLMResponse(workflow=workflow_scope, user=user, context=context)

    with patch.object(orchestrator, "_emit_workflow_event") as mock_emit:
        chunks = list(orchestrator.run({}))

    full = b"".join(chunks).decode("utf-8")
    assert "partial" in full
    assert "Error processing stream" in full
    assert "stream blew up" in full
    mock_logger.error.assert_called()
    mock_emit.assert_called_once()


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.logger")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.direct_orchestrator.LLMProcessor")
def test_stream_and_emit_emit_exception(
    mock_llm_processor_class,
    mock_openedx_processor_class,
    mock_logger,
    workflow_scope,  # pylint: disable=redefined-outer-name
    user,  # pylint: disable=redefined-outer-name
):
    """
    Test that _stream_and_emit swallows exceptions raised by _emit_workflow_event
    inside the finally block, while the stream chunks are still yielded normally.
    """
    def clean_generator():
        yield b"hello"
        yield b" world"

    mock_openedx = Mock()
    mock_openedx.process.return_value = {"location_id": "unit-123"}
    mock_openedx_processor_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.process.return_value = clean_generator()
    mock_llm.get_usage.return_value = None
    mock_llm_processor_class.return_value = mock_llm

    workflow_scope.location_id = None
    workflow_scope.action = "test_action"
    context = {"location_id": None, "course_id": workflow_scope.course_id}
    orchestrator = DirectLLMResponse(workflow=workflow_scope, user=user, context=context)

    with patch.object(orchestrator, "_emit_workflow_event", side_effect=Exception("event bus down")):
        chunks = list(orchestrator.run({}))

    full = b"".join(chunks).decode("utf-8")
    assert full == "hello world"
    mock_logger.error.assert_called()
    assert "event bus down" in str(mock_logger.error.call_args)


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.threaded_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.threaded_orchestrator.LLMProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.session_based_orchestrator.SubmissionProcessor")
def test_threaded_llm_response_orchestrator_new_session(
    mock_submission_processor_class,
    mock_responses_processor_class,
    mock_openedx_processor_class,
    workflow_scope,  # pylint: disable=redefined-outer-name
    user,  # pylint: disable=redefined-outer-name
):
    """
    Test ThreadedLLMResponse orchestrator with new session and user input.
    """
    # Mock OpenEdXProcessor
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"location_id": "unit-123"}
    mock_openedx_processor_class.return_value = mock_openedx

    # Mock LLMProcessor
    mock_responses = Mock()
    mock_responses.process.return_value = {
        "response": "AI chat response",
    }
    mock_responses.get_usage.return_value = None
    mock_responses_processor_class.return_value = mock_responses

    # Mock SubmissionProcessor
    mock_submission = Mock()
    mock_submission.update_chat_submission = Mock()
    mock_submission_processor_class.return_value = mock_submission

    # Mock the workflow to have location_id and action attributes
    workflow_scope.location_id = None
    workflow_scope.action = "test_action"
    context = {"location_id": None, "course_id": workflow_scope.course_id}
    orchestrator = ThreadedLLMResponse(workflow=workflow_scope, user=user, context=context)
    result = orchestrator.run("User question here")

    assert result["status"] == "completed"
    assert result["response"] == "AI chat response"
    assert mock_submission.update_chat_submission.called


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.session_based_orchestrator.SubmissionProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.threaded_orchestrator.LLMProcessor")
def test_threaded_llm_response_orchestrator_clear_session(
    mock_responses_processor_class,
    mock_submission_processor_class,
    workflow_scope,  # pylint: disable=redefined-outer-name
    user,  # pylint: disable=redefined-outer-name
):
    """
    Test ThreadedLLMResponse orchestrator with clear_session action.
    """
    # Create a real session first
    session = AIWorkflowSession.objects.create(
        user=user,
        scope=workflow_scope,
        profile=workflow_scope.profile,
        course_id=workflow_scope.course_id,
    )

    # Mock LLMProcessor and SubmissionProcessor to prevent initialization errors
    mock_responses = Mock()
    mock_responses_processor_class.return_value = mock_responses
    mock_submission = Mock()
    mock_submission_processor_class.return_value = mock_submission

    # Mock the workflow to have location_id attribute
    workflow_scope.location_id = None
    context = {"location_id": None, "course_id": workflow_scope.course_id}
    orchestrator = ThreadedLLMResponse(workflow=workflow_scope, user=user, context=context)
    result = orchestrator.clear_session(None)

    assert result["status"] == "session_cleared"
    assert result["response"] == ""
    # Verify session was actually deleted from database
    assert not AIWorkflowSession.objects.filter(id=session.id).exists()


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.threaded_orchestrator.LLMProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.session_based_orchestrator.SubmissionProcessor")
def test_threaded_llm_response_orchestrator_get_history(
    mock_submission_processor_class,
    mock_responses_processor_class,
    workflow_scope,  # pylint: disable=redefined-outer-name
    user,  # pylint: disable=redefined-outer-name
    course_key,  # pylint: disable=redefined-outer-name
):
    """
    Test ThreadedLLMResponse orchestrator retrieving chat history.
    """
    # Create a real session with existing submission
    AIWorkflowSession.objects.create(
        user=user,
        scope=workflow_scope,
        profile=workflow_scope.profile,
        course_id=course_key,
        local_submission_id="submission-uuid-123",
    )

    # Mock LLMProcessor
    mock_responses = Mock()
    mock_responses_processor_class.return_value = mock_responses

    # Mock SubmissionProcessor
    mock_submission = Mock()
    mock_submission.process.return_value = {
        "response": '[{"role": "user", "content": "Previous question"}]',
    }
    mock_submission_processor_class.return_value = mock_submission

    # Mock the workflow to have location_id attribute
    workflow_scope.location_id = None
    context = {"location_id": None, "course_id": workflow_scope.course_id}
    orchestrator = ThreadedLLMResponse(workflow=workflow_scope, user=user, context=context)
    # Call with no user input to trigger history retrieval
    result = orchestrator.run(None)

    assert result["status"] == "completed"
    assert "Previous question" in result["response"]


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.threaded_orchestrator.LLMProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.session_based_orchestrator.SubmissionProcessor")
def test_threaded_llm_response_orchestrator_history_error(
    mock_submission_processor_class,
    mock_responses_processor_class,
    workflow_scope,  # pylint: disable=redefined-outer-name
    user,  # pylint: disable=redefined-outer-name
    course_key,  # pylint: disable=redefined-outer-name
):
    """
    Test ThreadedLLMResponse orchestrator with error retrieving history.
    """
    # Create a real session with existing submission
    AIWorkflowSession.objects.create(
        user=user,
        scope=workflow_scope,
        profile=workflow_scope.profile,
        course_id=course_key,
        local_submission_id="submission-uuid-123",
    )

    # Mock LLMProcessor
    mock_responses = Mock()
    mock_responses_processor_class.return_value = mock_responses

    # Mock SubmissionProcessor
    mock_submission = Mock()
    mock_submission.process.return_value = {"error": "Submission not found"}
    mock_submission_processor_class.return_value = mock_submission

    # Mock the workflow to have location_id attribute
    workflow_scope.location_id = None
    context = {"location_id": None, "course_id": workflow_scope.course_id}
    orchestrator = ThreadedLLMResponse(workflow=workflow_scope, user=user, context=context)
    result = orchestrator.run(None)

    assert result["response"] == "No response available"
    assert result["status"] == "completed"


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.threaded_orchestrator.LLMProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.session_based_orchestrator.SubmissionProcessor")
def test_session_based_orchestrator_get_run_status(
    mock_submission_processor_class,
    mock_responses_processor_class,
    workflow_scope,  # pylint: disable=redefined-outer-name
    user,  # pylint: disable=redefined-outer-name
):
    """
    Test SessionBasedOrchestrator.get_run_status method with different task statuses.
    """
    # Mock LLMProcessor and SubmissionProcessor
    mock_responses = Mock()
    mock_responses_processor_class.return_value = mock_responses
    mock_submission = Mock()
    mock_submission_processor_class.return_value = mock_submission

    workflow_scope.location_id = None
    context = {"location_id": None, "course_id": workflow_scope.course_id}
    orchestrator = ThreadedLLMResponse(workflow=workflow_scope, user=user, context=context)

    # Test 1: Idle status (default — no task submitted yet)
    result = orchestrator.get_run_status({})
    assert result["status"] == "idle"

    # Test 1b: Processing status
    orchestrator.session.metadata = {
        "task_status": "processing",
        "task_status_message": "AI workflow is running",
    }
    orchestrator.session.save()
    result = orchestrator.get_run_status({})
    assert result["status"] == "processing"
    assert result["message"] == "AI workflow is running"

    # Test 2: Completed status with result
    orchestrator.session.metadata = {
        "task_status": "completed",
        "task_result": {"status": "done", "response": "Test response"}
    }
    orchestrator.session.save()
    result = orchestrator.get_run_status({})
    assert result["status"] == "done"
    assert result["response"] == "Test response"

    # Test 3: Error status
    orchestrator.session.metadata = {
        "task_status": "error",
        "task_error": "Something went wrong"
    }
    orchestrator.session.save()
    result = orchestrator.get_run_status({})
    assert result["status"] == "error"
    assert result["error"] == "Something went wrong"

    # Test 4: Timeout status
    orchestrator.session.metadata = {
        "task_status": "timeout",
        "task_error": "Task exceeded time limit"
    }
    orchestrator.session.save()
    result = orchestrator.get_run_status({})
    assert result["status"] == "timeout"
    assert result["error"] == "Task exceeded time limit"


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.threaded_orchestrator.LLMProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.session_based_orchestrator.SubmissionProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.threaded_orchestrator.OpenEdXProcessor")
def test_threaded_orchestrator_handles_error_marker(
    mock_openedx_processor_class,
    mock_submission_processor_class,
    mock_llm_processor_class,
    workflow_scope,  # pylint: disable=redefined-outer-name
    user,  # pylint: disable=redefined-outer-name
):
    """Test that ThreadedLLMResponse handles the error marker from a streaming response."""
    # Mock LLMProcessor to return a generator with an error marker
    mock_llm = Mock()

    def mock_generator(*args, **kwargs):
        yield b"Partial response"
        yield (
            b'||{"error_in_stream": true, "code": "streaming_failed", "message": "The AI service encountered '
            b'an error while generating the response. Please try again."}||'
        )
    mock_llm.process.return_value = mock_generator()
    mock_llm_processor_class.return_value = mock_llm

    # Mock other processors
    mock_submission = Mock()
    mock_submission.get_full_message_history.return_value = []
    mock_submission_processor_class.return_value = mock_submission

    mock_openedx = Mock()
    mock_openedx.process.return_value = {}
    mock_openedx_processor_class.return_value = mock_openedx

    context = {"course_id": workflow_scope.course_id}
    orchestrator = ThreadedLLMResponse(workflow=workflow_scope, user=user, context=context)

    # Execute orchestrator
    result = orchestrator.run(input_data={"user_input": "test"})

    # Consume generator to trigger history saving
    chunks = list(result)
    assert b"Partial response" in chunks

    # Verify history saving
    mock_submission.update_chat_submission.assert_called_once()
    messages = mock_submission.update_chat_submission.call_args[0][0]
    final_response = next(m["content"] for m in messages if m["role"] == "assistant")
    assert "The AI service encountered an error" in final_response


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.threaded_orchestrator.LLMProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.session_based_orchestrator.SubmissionProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.threaded_orchestrator.OpenEdXProcessor")
def test_threaded_orchestrator_handles_invalid_error_marker_fallback(
    mock_openedx_processor_class,
    mock_submission_processor_class,
    mock_llm_processor_class,
    workflow_scope,  # pylint: disable=redefined-outer-name
    user,  # pylint: disable=redefined-outer-name
):
    """Test that ThreadedLLMResponse handles invalid JSON in error marker correctly."""
    # Mock LLMProcessor to return a generator with an invalid error marker
    mock_llm = Mock()

    def mock_generator(*args, **kwargs):
        yield b"Partial response"
        yield b'||{"invalid_json": true||'
    mock_llm.process.return_value = mock_generator()
    mock_llm_processor_class.return_value = mock_llm

    # Mock other processors
    mock_submission = Mock()
    mock_submission.get_full_message_history.return_value = []
    mock_submission_processor_class.return_value = mock_submission

    mock_openedx = Mock()
    mock_openedx.process.return_value = {}
    mock_openedx_processor_class.return_value = mock_openedx

    context = {"course_id": workflow_scope.course_id}
    orchestrator = ThreadedLLMResponse(workflow=workflow_scope, user=user, context=context)

    # Execute orchestrator
    result = orchestrator.run(input_data={"user_input": "test"})

    # Consume generator
    chunks = list(result)
    assert b"Partial response" in chunks
    assert b'||{"invalid_json": true||' in chunks

    # Verify history saving - should include the invalid marker as is
    mock_submission.update_chat_submission.assert_called_once()
    messages = mock_submission.update_chat_submission.call_args[0][0]
    final_response = next(m["content"] for m in messages if m["role"] == "assistant")
    assert '||{"invalid_json": true||' in final_response
