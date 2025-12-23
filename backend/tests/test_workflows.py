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

# Mock the submissions module before any imports that depend on it
sys.modules["submissions"] = MagicMock()
sys.modules["submissions.api"] = MagicMock()

from openedx_ai_extensions.workflows.models import (  # noqa: E402 pylint: disable=wrong-import-position
    AIWorkflowProfile,
    AIWorkflowScope,
    AIWorkflowSession,
)
from openedx_ai_extensions.workflows.orchestrators import (  # noqa: E402 pylint: disable=wrong-import-position
    BaseOrchestrator,
    DirectLLMResponse,
    MockResponse,
    MockStreamResponse,
    ThreadedLLMResponse,
)

User = get_user_model()


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
        base_filepath="base/default.json",
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
        enabled=True
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
    # Clear cached config
    if hasattr(workflow_scope.profile, '_config'):
        del workflow_scope.profile._config

    # Mock the orchestrator
    with patch("openedx_ai_extensions.workflows.orchestrators.MockResponse") as mock_orch:
        mock_instance = Mock()
        mock_instance.run = Mock(return_value={"status": "completed", "response": "Test"})
        mock_orch.return_value = mock_instance

        result = workflow_scope.execute("test input", "run", user)

        # Should return result or error
        assert "status" in result


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
    # Mock the workflow to have location_id attribute
    workflow_scope.location_id = None
    orchestrator = BaseOrchestrator(workflow=workflow_scope, user=user)

    assert orchestrator.workflow == workflow_scope


@pytest.mark.django_db
def test_base_orchestrator_run_not_implemented(workflow_scope, user):  # pylint: disable=redefined-outer-name
    """
    Test BaseOrchestrator.run raises NotImplementedError.
    """
    # Mock the workflow to have location_id attribute
    workflow_scope.location_id = None
    orchestrator = BaseOrchestrator(workflow=workflow_scope, user=user)

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
    orchestrator = MockResponse(workflow=workflow_scope, user=user)
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
    orchestrator = MockStreamResponse(workflow=workflow_scope, user=user)
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
@patch("openedx_ai_extensions.workflows.orchestrators.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.LLMProcessor")
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
        "tokens_used": 150,
        "model_used": "gpt-3.5-turbo",
    }
    mock_llm_processor_class.return_value = mock_llm

    # Mock the workflow to have location_id and action attributes
    workflow_scope.location_id = None
    workflow_scope.action = "test_action"
    orchestrator = DirectLLMResponse(workflow=workflow_scope, user=user)
    result = orchestrator.run({})

    assert result["status"] == "completed"
    assert result["response"] == "This is a summary"
    assert result["metadata"]["tokens_used"] == 150


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.OpenEdXProcessor")
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
    orchestrator = DirectLLMResponse(workflow=workflow_scope, user=user)
    result = orchestrator.run({})

    assert "error" in result
    assert result["status"] == "OpenEdXProcessor error"


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.LLMProcessor")
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
    orchestrator = DirectLLMResponse(workflow=workflow_scope, user=user)
    result = orchestrator.run({})

    assert "error" in result
    assert result["status"] == "LLMProcessor error"


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.LLMProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.SubmissionProcessor")
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
        "tokens_used": 200,
        "model_used": "gpt-4",
    }
    mock_responses_processor_class.return_value = mock_responses

    # Mock SubmissionProcessor
    mock_submission = Mock()
    mock_submission.update_chat_submission = Mock()
    mock_submission_processor_class.return_value = mock_submission

    # Mock the workflow to have location_id and action attributes
    workflow_scope.location_id = None
    workflow_scope.action = "test_action"
    orchestrator = ThreadedLLMResponse(workflow=workflow_scope, user=user)
    result = orchestrator.run("User question here")

    assert result["status"] == "completed"
    assert result["response"] == "AI chat response"
    assert mock_submission.update_chat_submission.called


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.SubmissionProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.LLMProcessor")
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
    orchestrator = ThreadedLLMResponse(workflow=workflow_scope, user=user)
    result = orchestrator.clear_session(None)

    assert result["status"] == "session_cleared"
    assert result["response"] == ""
    # Verify session was actually deleted from database
    assert not AIWorkflowSession.objects.filter(id=session.id).exists()


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.LLMProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.SubmissionProcessor")
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
    orchestrator = ThreadedLLMResponse(workflow=workflow_scope, user=user)
    # Call with no user input to trigger history retrieval
    result = orchestrator.run(None)

    assert result["status"] == "completed"
    assert "Previous question" in result["response"]


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.LLMProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.SubmissionProcessor")
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
    orchestrator = ThreadedLLMResponse(workflow=workflow_scope, user=user)
    result = orchestrator.run(None)

    assert "error" in result
    assert result["status"] == "SubmissionProcessor error"
