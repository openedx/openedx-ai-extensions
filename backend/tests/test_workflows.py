"""
Tests for the `openedx-ai-extensions` workflows module.
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locator import BlockUsageLocator

# Mock the submissions module before any imports that depend on it
sys.modules['submissions'] = MagicMock()
sys.modules['submissions.api'] = MagicMock()

from openedx_ai_extensions.workflows.models import (  # noqa: E402 pylint: disable=wrong-import-position
    AIWorkflow,
    AIWorkflowConfig,
    AIWorkflowSession,
)
from openedx_ai_extensions.workflows.orchestrators import (  # noqa: E402 pylint: disable=wrong-import-position
    BaseOrchestrator,
    DirectLLMResponse,
    MockResponse,
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
def workflow_config(db):  # pylint: disable=unused-argument
    """
    Create a mock workflow config with proper Django model attributes.
    """
    config = Mock(spec=AIWorkflowConfig)
    config.id = 1
    config.pk = 1
    config.action = "summarize"
    config.course_id = "course-v1:edX+DemoX+Demo_Course"
    config.location_id = None
    config.orchestrator_class = "MockResponse"
    config.processor_config = {"LLMProcessor": {"function": "summarize_content"}}
    config.actuator_config = {"UIComponents": {"request": {"component": "Button"}}}
    # Add Django model state to make it work with ForeignKey
    config._state = Mock()  # pylint: disable=protected-access
    config._state.db = 'default'  # pylint: disable=protected-access
    config._state.adding = False  # pylint: disable=protected-access
    return config


@pytest.fixture
def workflow_instance(user, workflow_config, course_key):  # pylint: disable=redefined-outer-name
    """
    Create a mock workflow instance.
    """
    location = BlockUsageLocator(
        course_key,
        block_type="vertical",
        block_id="test_unit"
    )
    workflow = AIWorkflow(
        user=user,
        action="summarize",
        course_id=str(course_key),
        location_id=location,
        config=workflow_config,
        extra_context={"unitId": str(location)},
        context_data={},
    )
    return workflow


# ============================================================================
# AIWorkflowConfig Tests
# ============================================================================


@pytest.mark.django_db
def test_workflow_config_str():
    """
    Test AIWorkflowConfig string representation.
    """
    config = AIWorkflowConfig(action="summarize", course_id="course-v1:test")
    assert "summarize" in str(config)
    assert "Course: course-v1:test" in str(config)


@pytest.mark.django_db
def test_workflow_config_str_global():
    """
    Test AIWorkflowConfig string representation for global config.
    """
    config = AIWorkflowConfig(action="summarize", course_id=None)
    assert "summarize" in str(config)
    assert "(Global)" in str(config)


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.models._fake_get_config_from_file")
def test_workflow_config_get_config(mock_get_config):
    """
    Test AIWorkflowConfig.get_config class method.
    """
    mock_config = Mock(spec=AIWorkflowConfig)
    mock_get_config.return_value = mock_config

    result = AIWorkflowConfig.get_config(
        action="summarize",
        course_id="course-v1:edX+DemoX+Demo_Course",
        location_id="unit-123",
    )

    assert result == mock_config
    mock_get_config.assert_called_once_with(
        AIWorkflowConfig,
        action="summarize",
        course_id="course-v1:edX+DemoX+Demo_Course",
        location_id="unit-123",
    )


# ============================================================================
# AIWorkflow Tests
# ============================================================================


@pytest.mark.django_db
def test_workflow_str(workflow_instance):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflow string representation.
    """
    result = str(workflow_instance)
    assert "testuser" in result
    assert "summarize" in result
    assert "active" in result


@pytest.mark.django_db
def test_workflow_get_natural_key(workflow_instance):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflow.get_natural_key method.
    """
    natural_key = workflow_instance.get_natural_key()

    assert str(workflow_instance.user.id) in natural_key
    assert workflow_instance.action in natural_key
    assert workflow_instance.course_id in natural_key
    assert str(workflow_instance.location_id) in natural_key


@pytest.mark.django_db
def test_workflow_get_natural_key_no_unit(user, workflow_config):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflow.get_natural_key without location_id.
    """
    workflow = AIWorkflow(
        user=user,
        action="summarize",
        course_id="course-v1:edX+DemoX+Demo_Course",
        location_id=None,
        config=workflow_config,
    )

    natural_key = workflow.get_natural_key()

    assert str(workflow.user.id) in natural_key
    assert workflow.action in natural_key
    assert workflow.course_id in natural_key


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.models.AIWorkflowConfig.get_config")
def test_workflow_find_workflow_for_context(
    mock_get_config, user, workflow_config
):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflow.find_workflow_for_context class method.
    """
    mock_get_config.return_value = workflow_config

    course_key_obj = CourseKey.from_string("course-v1:edX+DemoX+Demo_Course")
    location = BlockUsageLocator(
        course_key_obj,
        block_type="vertical",
        block_id="unit1"
    )
    context = {"unitId": str(location)}

    workflow, created = AIWorkflow.find_workflow_for_context(
        action="summarize",
        course_id="course-v1:edX+DemoX+Demo_Course",
        user=user,
        context=context,
    )

    assert workflow is not None
    assert created is True
    assert workflow.action == "summarize"
    assert workflow.course_id == "course-v1:edX+DemoX+Demo_Course"
    assert workflow.user == user


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.models.AIWorkflowConfig.get_config")
def test_workflow_find_workflow_for_context_no_config(mock_get_config, user):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflow.find_workflow_for_context raises error when no config found.
    """
    mock_get_config.return_value = None

    with pytest.raises(ValidationError) as exc_info:
        AIWorkflow.find_workflow_for_context(
            action="nonexistent",
            course_id="course-v1:edX+DemoX+Demo_Course",
            user=user,
            context={},
        )

    assert "No AIWorkflowConfiguration found" in str(exc_info.value)


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.MockResponse")
def test_workflow_execute_success(mock_orchestrator_class, workflow_instance):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflow.execute method with successful execution.
    """
    # Mock orchestrator instance
    mock_orchestrator = Mock()
    # Mock the action method directly (e.g., 'summarize')
    mock_action_method = Mock(return_value={
        "response": "Summary generated",
        "status": "completed",
    })
    setattr(mock_orchestrator, workflow_instance.action, mock_action_method)
    mock_orchestrator_class.return_value = mock_orchestrator

    # Execute the workflow - the orchestrator is already mocked by the decorator
    result = workflow_instance.execute("Test input")

    assert result["status"] == "completed"
    assert result["response"] == "Summary generated"
    assert "workflow_info" in result


@pytest.mark.django_db
def test_workflow_execute_error(workflow_instance):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflow.execute method with execution error.
    """
    # Patch orchestrator to raise an exception
    with patch("openedx_ai_extensions.workflows.orchestrators.MockResponse") as mock_orch_class:
        mock_orchestrator = Mock()
        # Mock the action method to raise exception
        mock_action_method = Mock(side_effect=Exception("Orchestrator error"))
        setattr(mock_orchestrator, workflow_instance.action, mock_action_method)
        mock_orch_class.return_value = mock_orchestrator

        result = workflow_instance.execute("Test input")

    assert result["status"] == "error"
    assert "error" in result
    assert "Workflow execution failed" in result["error"]
    assert workflow_instance.status == "failed"


@pytest.mark.django_db
def test_workflow_update_context(workflow_instance):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflow.update_context method.
    """
    workflow_instance.update_context(key1="value1", key2="value2")

    assert workflow_instance.context_data["key1"] == "value1"
    assert workflow_instance.context_data["key2"] == "value2"


@pytest.mark.django_db
def test_workflow_set_step(workflow_instance):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflow.set_step method.
    """
    workflow_instance.set_step("processing", status="active")

    assert workflow_instance.current_step == "processing"
    assert workflow_instance.status == "active"


@pytest.mark.django_db
def test_workflow_set_step_without_status(workflow_instance):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflow.set_step method without changing status.
    """
    original_status = workflow_instance.status
    workflow_instance.set_step("processing")

    assert workflow_instance.current_step == "processing"
    assert workflow_instance.status == original_status


@pytest.mark.django_db
def test_workflow_complete(workflow_instance):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflow.complete method.
    """
    workflow_instance.complete(final_result="Success", tokens_used=100)

    assert workflow_instance.status == "completed"
    assert workflow_instance.current_step == "completed"
    assert workflow_instance.completed_at is not None
    assert workflow_instance.context_data["final_result"] == "Success"
    assert workflow_instance.context_data["tokens_used"] == 100


@pytest.mark.django_db
def test_workflow_complete_without_context(workflow_instance):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflow.complete method without additional context.
    """
    workflow_instance.complete()

    assert workflow_instance.status == "completed"
    assert workflow_instance.current_step == "completed"
    assert workflow_instance.completed_at is not None


# ============================================================================
# AIWorkflowSession Tests
# ============================================================================


@pytest.mark.django_db
def test_workflow_session_get_or_create(user, course_key):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflowSession.objects.get_or_create with real Django ORM.
    """
    location = BlockUsageLocator(
        course_key,
        block_type="vertical",
        block_id="unit-123"
    )

    session, created = AIWorkflowSession.objects.get_or_create(
        user=user,
        course_id=course_key,
        location_id=location,
        defaults={},
    )

    assert session.user == user
    assert session.course_id == course_key
    assert session.location_id == location
    assert created is True

    # Test retrieving existing session
    session2, created2 = AIWorkflowSession.objects.get_or_create(
        user=user,
        course_id=course_key,
        location_id=location,
        defaults={},
    )

    assert session.id == session2.id
    assert created2 is False


@pytest.mark.django_db
def test_workflow_session_save(user, course_key):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflowSession.save method with real Django ORM.
    """
    location = BlockUsageLocator(
        course_key,
        block_type="vertical",
        block_id="unit-123"
    )

    session = AIWorkflowSession(
        user=user,
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
def test_workflow_session_delete(user, course_key):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflowSession.delete method with real Django ORM.
    """
    location = BlockUsageLocator(
        course_key,
        block_type="vertical",
        block_id="unit-123"
    )

    session = AIWorkflowSession(
        user=user,
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
def test_base_orchestrator_initialization(workflow_instance):  # pylint: disable=redefined-outer-name
    """
    Test BaseOrchestrator initialization.
    """
    orchestrator = BaseOrchestrator(workflow=workflow_instance)

    assert orchestrator.workflow == workflow_instance
    assert orchestrator.config == workflow_instance.config


@pytest.mark.django_db
def test_base_orchestrator_run_not_implemented(workflow_instance):  # pylint: disable=redefined-outer-name
    """
    Test BaseOrchestrator.run raises NotImplementedError.
    """
    orchestrator = BaseOrchestrator(workflow=workflow_instance)

    with pytest.raises(NotImplementedError):
        orchestrator.run({})


@pytest.mark.django_db
def test_mock_response_orchestrator(workflow_instance):  # pylint: disable=redefined-outer-name
    """
    Test MockResponse orchestrator.
    """
    orchestrator = MockResponse(workflow=workflow_instance)
    result = orchestrator.run({})

    assert result["status"] == "completed"
    assert "Mock response" in result["response"]
    assert workflow_instance.action in result["response"]


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.LLMProcessor")
def test_direct_llm_response_orchestrator_success(
    mock_llm_processor_class, mock_openedx_processor_class, workflow_instance  # pylint: disable=redefined-outer-name
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

    orchestrator = DirectLLMResponse(workflow=workflow_instance)
    result = orchestrator.run({})

    assert result["status"] == "completed"
    assert result["response"] == "This is a summary"
    assert result["metadata"]["tokens_used"] == 150


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.OpenEdXProcessor")
def test_direct_llm_response_orchestrator_openedx_error(
    mock_openedx_processor_class, workflow_instance  # pylint: disable=redefined-outer-name
):
    """
    Test DirectLLMResponse orchestrator with OpenEdXProcessor error.
    """
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"error": "Failed to load unit"}
    mock_openedx_processor_class.return_value = mock_openedx

    orchestrator = DirectLLMResponse(workflow=workflow_instance)
    result = orchestrator.run({})

    assert "error" in result
    assert result["status"] == "OpenEdXProcessor error"


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.LLMProcessor")
def test_direct_llm_response_orchestrator_llm_error(
    mock_llm_processor_class, mock_openedx_processor_class, workflow_instance  # pylint: disable=redefined-outer-name
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

    orchestrator = DirectLLMResponse(workflow=workflow_instance)
    result = orchestrator.run({})

    assert "error" in result
    assert result["status"] == "LLMProcessor error"


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.ResponsesProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.SubmissionProcessor")
def test_threaded_llm_response_orchestrator_new_session(
    mock_submission_processor_class,
    mock_responses_processor_class,
    mock_openedx_processor_class,
    workflow_instance,  # pylint: disable=redefined-outer-name
):
    """
    Test ThreadedLLMResponse orchestrator with new session and user input.
    """
    # Session will be created automatically by Django ORM

    # Mock OpenEdXProcessor
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"location_id": "unit-123"}
    mock_openedx_processor_class.return_value = mock_openedx

    # Mock ResponsesProcessor
    mock_responses = Mock()
    mock_responses.process.return_value = {
        "response": "AI chat response",
        "tokens_used": 200,
        "model_used": "gpt-4",
    }
    mock_responses_processor_class.return_value = mock_responses

    # Mock SubmissionProcessor
    mock_submission = Mock()
    mock_submission.update_submission = Mock()
    mock_submission_processor_class.return_value = mock_submission

    orchestrator = ThreadedLLMResponse(workflow=workflow_instance)
    result = orchestrator.run("User question here")

    assert result["status"] == "completed"
    assert result["response"] == "AI chat response"
    assert mock_submission.update_submission.called


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.SubmissionProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.ResponsesProcessor")
def test_threaded_llm_response_orchestrator_clear_session(
    mock_responses_processor_class,
    mock_submission_processor_class,
    workflow_instance,  # pylint: disable=redefined-outer-name
):
    """
    Test ThreadedLLMResponse orchestrator with clear_session action.
    """
    # Create a real session first
    session = AIWorkflowSession.objects.create(
        user=workflow_instance.user,
        course_id=workflow_instance.course_id,
        location_id=workflow_instance.location_id,
    )

    # Change workflow action to clear_session
    workflow_instance.action = "clear_session"

    # Mock ResponsesProcessor and SubmissionProcessor to prevent initialization errors
    mock_responses = Mock()
    mock_responses_processor_class.return_value = mock_responses
    mock_submission = Mock()
    mock_submission_processor_class.return_value = mock_submission

    orchestrator = ThreadedLLMResponse(workflow=workflow_instance)
    result = orchestrator.clear_session(None)

    assert result["status"] == "session_cleared"
    assert result["response"] == ""
    # Verify session was actually deleted from database
    assert not AIWorkflowSession.objects.filter(id=session.id).exists()


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.ResponsesProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.SubmissionProcessor")
def test_threaded_llm_response_orchestrator_get_history(
    mock_submission_processor_class,
    mock_responses_processor_class,
    workflow_instance  # pylint: disable=redefined-outer-name
):
    """
    Test ThreadedLLMResponse orchestrator retrieving chat history.
    """
    # Create a real session with existing submission
    AIWorkflowSession.objects.create(
        user=workflow_instance.user,
        course_id=workflow_instance.course_id,
        location_id=workflow_instance.location_id,
        local_submission_id="submission-uuid-123",
    )

    # Mock ResponsesProcessor
    mock_responses = Mock()
    mock_responses_processor_class.return_value = mock_responses

    # Mock SubmissionProcessor
    mock_submission = Mock()
    mock_submission.process.return_value = {
        "response": '[{"role": "user", "content": "Previous question"}]',
    }
    mock_submission_processor_class.return_value = mock_submission

    orchestrator = ThreadedLLMResponse(workflow=workflow_instance)
    # Call with no user input to trigger history retrieval
    result = orchestrator.run(None)

    assert result["status"] == "completed"
    assert "Previous question" in result["response"]


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.ResponsesProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.SubmissionProcessor")
def test_threaded_llm_response_orchestrator_history_error(
    mock_submission_processor_class,
    mock_responses_processor_class,
    workflow_instance  # pylint: disable=redefined-outer-name
):
    """
    Test ThreadedLLMResponse orchestrator with error retrieving history.
    """
    # Create a real session with existing submission
    AIWorkflowSession.objects.create(
        user=workflow_instance.user,
        course_id=workflow_instance.course_id,
        location_id=workflow_instance.location_id,
        local_submission_id="submission-uuid-123",
    )

    # Mock ResponsesProcessor
    mock_responses = Mock()
    mock_responses_processor_class.return_value = mock_responses

    # Mock SubmissionProcessor
    mock_submission = Mock()
    mock_submission.process.return_value = {"error": "Submission not found"}
    mock_submission_processor_class.return_value = mock_submission

    orchestrator = ThreadedLLMResponse(workflow=workflow_instance)
    result = orchestrator.run(None)

    assert "error" in result
    assert result["status"] == "SubmissionProcessor error"
