"""
Tests for the SubmissionProcessor module.
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from opaque_keys.edx.keys import CourseKey

# Mock the submissions module before any imports that depend on it
sys.modules["submissions"] = MagicMock()
sys.modules["submissions.api"] = MagicMock()

from openedx_ai_extensions.processors.openedx.submission_processor import (  # noqa: E402 pylint: disable=wrong-import-position
    SubmissionProcessor,
)
from openedx_ai_extensions.workflows.models import (  # noqa: E402 pylint: disable=wrong-import-position
    AIWorkflowProfile,
    AIWorkflowScope,
    AIWorkflowSession,
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
    Create and return a test AIWorkflowProfile.
    """
    profile = AIWorkflowProfile.objects.create(
        slug="test-submission",
        base_filepath="base/default.json",
        content_patch='{}'
    )
    return profile


@pytest.fixture
def workflow_scope(workflow_profile, course_key, db):  # pylint: disable=unused-argument,redefined-outer-name
    """
    Create and return a test AIWorkflowScope.
    """
    scope = AIWorkflowScope.objects.create(
        location_regex=".*",
        course_id=course_key,
        service_variant="lms",
        profile=workflow_profile,
        enabled=True
    )
    return scope


@pytest.fixture
def user_session(
    user, course_key, workflow_scope, workflow_profile, db
):  # pylint: disable=unused-argument,redefined-outer-name
    """
    Create and return a test AIWorkflowSession.
    """
    session = AIWorkflowSession.objects.create(
        user=user,
        scope=workflow_scope,
        profile=workflow_profile,
        course_id=course_key,
        local_submission_id="test-submission-uuid-123",
    )
    return session


@pytest.fixture
def user_session_no_submission(
    user, course_key, workflow_scope, workflow_profile, db
):  # pylint: disable=unused-argument,redefined-outer-name
    """
    Create and return a test AIWorkflowSession without a submission ID.
    """
    session = AIWorkflowSession.objects.create(
        user=user,
        scope=workflow_scope,
        profile=workflow_profile,
        course_id=course_key,
        local_submission_id=None,
    )
    return session


@pytest.fixture
def submission_processor(user_session):  # pylint: disable=redefined-outer-name
    """
    Create and return a SubmissionProcessor instance.
    """
    config = {
        "SubmissionProcessor": {
            "max_context_messages": 10,
        }
    }
    return SubmissionProcessor(config=config, user_session=user_session)


# ============================================================================
# SubmissionProcessor Initialization Tests
# ============================================================================


@pytest.mark.django_db
def test_submission_processor_initialization(user_session):  # pylint: disable=redefined-outer-name
    """
    Test SubmissionProcessor initialization with valid config.
    """
    config = {
        "SubmissionProcessor": {
            "max_context_messages": 15,
        }
    }
    processor = SubmissionProcessor(config=config, user_session=user_session)

    assert processor.user_session == user_session
    assert processor.max_context_messages == 15
    assert processor.student_item_dict["student_id"] == user_session.user.id
    assert processor.student_item_dict["course_id"] == str(user_session.course_id)
    assert processor.student_item_dict["item_id"] == str(user_session.id)
    assert processor.student_item_dict["item_type"] == "openedx_ai_extensions_chat"


@pytest.mark.django_db
def test_submission_processor_initialization_default_config(user_session):  # pylint: disable=redefined-outer-name
    """
    Test SubmissionProcessor initialization with default config.
    """
    processor = SubmissionProcessor(config={}, user_session=user_session)

    # Should use default value from settings or hardcoded default
    assert processor.max_context_messages == getattr(
        settings, "AI_EXTENSIONS_MAX_CONTEXT_MESSAGES", 10
    )


@pytest.mark.django_db
def test_submission_processor_initialization_no_config(user_session):  # pylint: disable=redefined-outer-name
    """
    Test SubmissionProcessor initialization with no config.
    """
    processor = SubmissionProcessor(config=None, user_session=user_session)

    assert processor.user_session == user_session
    assert processor.config == {}


# ============================================================================
# SubmissionProcessor.process() Tests
# ============================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.submission_processor.submissions_api")
def test_process_calls_get_chat_history_by_default(
    mock_submissions_api, submission_processor  # pylint: disable=redefined-outer-name
):
    """
    Test that process() calls get_chat_history by default.
    """
    mock_submissions_api.get_submissions.return_value = []

    result = submission_processor.process(context={}, input_data=None)

    # Should call get_chat_history which returns a response with messages
    assert "response" in result or "error" in result


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.submission_processor.submissions_api")
def test_process_retrieves_existing_submissions_and_injects_timestamps(
    mock_submissions_api, submission_processor  # pylint: disable=redefined-outer-name
):
    """
    Test that process() properly retrieves submissions and injects the submission
    timestamp into the messages.
    """
    # Mock submission data
    mock_submissions = [
        {
            "uuid": "submission-1",
            "answer": json.dumps([{"role": "user", "content": "Hello"}]),
            "created_at": "2025-01-01T00:00:00Z",
        },
        {
            "uuid": "submission-2",
            "answer": json.dumps([{"role": "assistant", "content": "Hi there!"}]),
            "created_at": "2025-01-01T00:01:00Z",
        },
        {
            "uuid": "submission-1",
            "answer": json.dumps([{"role": "user", "content": "Hello"}]),
            "created_at": "2025-01-01T00:00:00Z",
        },
    ]
    mock_submissions_api.get_submissions.return_value = mock_submissions

    result = submission_processor.process(context={}, input_data=None)

    # Verify get_submissions was called with correct student_item_dict
    mock_submissions_api.get_submissions.assert_called_once()
    call_args = mock_submissions_api.get_submissions.call_args
    assert call_args[0][0] == submission_processor.student_item_dict
    assert "response" in result
    response_data = json.loads(result["response"])
    messages = response_data["messages"]
    # Should maintain chronological order (Oldest -> Newest) due to reversed() call
    assert len(messages) == 3

    # Check first message (Oldest)
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello"
    # Verify timestamp was injected from the submission object
    assert messages[0]["timestamp"] == "2025-01-01T00:00:00Z"

    # Check second message (Newest)
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hi there!"
    assert messages[1]["timestamp"] == "2025-01-01T00:01:00Z"


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.submission_processor.submissions_api")
def test_process_respects_max_context_messages_limit(
    mock_submissions_api, user_session  # pylint: disable=redefined-outer-name
):
    """
    Test that process() respects the max_context_messages configuration limit.
    """
    # Create processor with max_context_messages=2
    config = {
        "SubmissionProcessor": {
            "max_context_messages": 2,
        }
    }
    processor = SubmissionProcessor(config=config, user_session=user_session)

    # Mock multiple submissions (Newest First)
    mock_submissions = [
        {
            "uuid": "submission-4",
            "answer": json.dumps([{"role": "assistant", "content": "Response 2"}]),
            "created_at": "2025-01-01T00:03:00Z",
        },
        {
            "uuid": "submission-3",
            "answer": json.dumps([{"role": "user", "content": "Message 2"}]),
            "created_at": "2025-01-01T00:02:00Z",
        },
        {
            "uuid": "submission-2",
            "answer": json.dumps([{"role": "assistant", "content": "Response 1"}]),
            "created_at": "2025-01-01T00:01:00Z",
        },
        {
            "uuid": "submission-1",
            "answer": json.dumps([{"role": "user", "content": "Message 1"}]),
            "created_at": "2025-01-01T00:00:00Z",
        },
    ]
    mock_submissions_api.get_submissions.return_value = mock_submissions

    result = processor.process(context={}, input_data=None)

    assert "response" in result
    response_data = json.loads(result["response"])
    messages = response_data["messages"]

    # Should only return the last 2 messages
    assert len(messages) == 2
    assert messages[0]["content"] == "Message 2"
    assert messages[1]["content"] == "Response 2"


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.submission_processor.submissions_api")
def test_process_handles_empty_submissions(
    mock_submissions_api, submission_processor  # pylint: disable=redefined-outer-name
):
    """
    Test that process() handles cases where there are no existing submissions.
    """
    # Mock empty submissions list
    mock_submissions_api.get_submissions.return_value = []

    result = submission_processor.process(context={}, input_data=None)

    # Verify get_submissions was called
    mock_submissions_api.get_submissions.assert_called_once()
    call_args = mock_submissions_api.get_submissions.call_args
    assert call_args[0][0] == submission_processor.student_item_dict

    # Should return response even with no previous submissions
    assert "response" in result or "error" in result


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.submission_processor.submissions_api")
def test_process_handles_malformed_submission_data(
    mock_submissions_api, submission_processor  # pylint: disable=redefined-outer-name
):
    """
    Test that process() handles malformed submission data gracefully.
    """
    # Mock submissions with various malformed data structures
    mock_submissions = [
        {
            "uuid": "submission-1",
            "answer": json.dumps([{"role": "user", "content": "Valid message"}]),
            "created_at": "2025-01-01T00:00:00Z",
        },
        {
            "uuid": "submission-2",
            "answer": json.dumps({}),  # Missing messages key
            "created_at": "2025-01-01T00:01:00Z",
        },
        {
            "uuid": "submission-3",
            "answer": json.dumps({"messages": None}),  # None messages
            "created_at": "2025-01-01T00:02:00Z",
        },
        {
            "uuid": "submission-4",
            "answer": "null",  # JSON null
            "created_at": "2025-01-01T00:03:00Z",
        },
    ]
    mock_submissions_api.get_submissions.return_value = mock_submissions

    result = submission_processor.process(context={}, input_data=None)

    # Verify get_submissions was called
    mock_submissions_api.get_submissions.assert_called_once()

    # Should handle malformed data and still return a response
    assert "response" in result or "error" in result
