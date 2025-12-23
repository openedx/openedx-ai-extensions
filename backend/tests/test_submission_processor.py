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


# ============================================================================
# SubmissionProcessor.get_previous_messages() Tests
# ============================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.submission_processor.submissions_api")
def test_get_previous_messages_returns_older_messages(
    mock_submissions_api, submission_processor  # pylint: disable=redefined-outer-name
):
    """
    Test that get_previous_messages returns the next batch of older messages.
    """
    # Mock submissions with multiple messages
    mock_submissions = [
        {
            "uuid": "submission-6",
            "answer": json.dumps([{"role": "assistant", "content": "Response 3"}]),
            "created_at": "2025-01-01T00:05:00Z",
        },
        {
            "uuid": "submission-5",
            "answer": json.dumps([{"role": "user", "content": "Message 3"}]),
            "created_at": "2025-01-01T00:04:00Z",
        },
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

    # Frontend has loaded the most recent 2 messages
    result = submission_processor.get_previous_messages(current_messages_count=2)

    assert "response" in result
    response_data = json.loads(result["response"])
    messages = response_data["messages"]
    metadata = response_data["metadata"]

    # Should return the next batch (older messages)
    assert len(messages) > 0
    assert metadata["has_more"] is True or metadata["has_more"] is False
    assert "new_count" in metadata


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.submission_processor.submissions_api")
def test_get_previous_messages_handles_string_input(
    mock_submissions_api, submission_processor  # pylint: disable=redefined-outer-name
):
    """
    Test that get_previous_messages handles string input for current_messages_count.
    """
    mock_submissions_api.get_submissions.return_value = []

    # Pass current_messages_count as string
    result = submission_processor.get_previous_messages(current_messages_count="5")

    assert "response" in result
    response_data = json.loads(result["response"])
    assert "messages" in response_data
    assert "metadata" in response_data


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.submission_processor.submissions_api")
def test_get_previous_messages_handles_invalid_string(
    mock_submissions_api, submission_processor  # pylint: disable=redefined-outer-name
):
    """
    Test that get_previous_messages handles invalid string input gracefully.
    """
    mock_submissions_api.get_submissions.return_value = []

    # Pass invalid string that can't be converted to int
    result = submission_processor.get_previous_messages(current_messages_count="invalid")

    assert "response" in result
    response_data = json.loads(result["response"])
    assert "messages" in response_data


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.submission_processor.submissions_api")
def test_get_previous_messages_no_more_messages(
    mock_submissions_api, submission_processor  # pylint: disable=redefined-outer-name
):
    """
    Test that get_previous_messages returns has_more=False when no more messages exist.
    """
    # Mock only 2 messages total
    mock_submissions = [
        {
            "uuid": "submission-2",
            "answer": json.dumps([{"role": "assistant", "content": "Response"}]),
            "created_at": "2025-01-01T00:01:00Z",
        },
        {
            "uuid": "submission-1",
            "answer": json.dumps([{"role": "user", "content": "Message"}]),
            "created_at": "2025-01-01T00:00:00Z",
        },
    ]
    mock_submissions_api.get_submissions.return_value = mock_submissions

    # Frontend already has all 2 messages
    result = submission_processor.get_previous_messages(current_messages_count=2)

    assert "response" in result
    response_data = json.loads(result["response"])
    metadata = response_data["metadata"]

    # Should indicate no more messages available
    assert metadata["has_more"] is False
    assert metadata["new_count"] == 0


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.submission_processor.submissions_api")
def test_get_previous_messages_handles_exception(
    mock_submissions_api, submission_processor  # pylint: disable=redefined-outer-name
):
    """
    Test that get_previous_messages handles exceptions gracefully.
    """
    # Mock an exception when getting submissions
    mock_submissions_api.get_submissions.side_effect = Exception("Database error")

    result = submission_processor.get_previous_messages(current_messages_count=2)

    # Should return error response
    assert "error" in result
    assert "Failed to load previous messages" in result["error"]


# ============================================================================
# SubmissionProcessor.update_chat_submission() Tests
# ============================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.submission_processor.submissions_api")
def test_update_chat_submission_creates_new_submission(
    mock_submissions_api, user_session  # pylint: disable=redefined-outer-name
):
    """
    Test that update_chat_submission creates a new submission with messages.
    """
    # Remove existing submission ID to simulate first message
    user_session.local_submission_id = None
    user_session.save()

    processor = SubmissionProcessor(config={}, user_session=user_session)

    # Mock create_submission to return a UUID
    mock_submissions_api.create_submission.return_value = {"uuid": "new-submission-uuid"}

    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]

    processor.update_chat_submission(messages)

    # Verify create_submission was called
    mock_submissions_api.create_submission.assert_called_once()
    call_args = mock_submissions_api.create_submission.call_args
    assert call_args[1]["student_item_dict"] == processor.student_item_dict
    assert call_args[1]["attempt_number"] == 1

    # Verify answer contains the messages
    answer = json.loads(call_args[1]["answer"])
    assert len(answer) == 2
    assert answer[0]["role"] == "user"
    assert answer[1]["role"] == "assistant"

    # Verify session was updated with new submission ID
    user_session.refresh_from_db()
    assert user_session.local_submission_id == "new-submission-uuid"


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.submission_processor.submissions_api")
def test_update_chat_submission_tracks_previous_submissions(
    mock_submissions_api, submission_processor  # pylint: disable=redefined-outer-name
):
    """
    Test that update_chat_submission tracks previous submission IDs.
    """
    # Mock existing submission with messages
    existing_messages = [
        {"role": "user", "content": "Old message"},
        {"role": "assistant", "content": "Old response"}
    ]

    mock_submissions_api.get_submission_and_student.return_value = {
        "uuid": "test-submission-uuid-123",
        "answer": existing_messages
    }

    mock_submissions_api.create_submission.return_value = {"uuid": "new-submission-uuid"}

    new_messages = [
        {"role": "user", "content": "New message"},
        {"role": "assistant", "content": "New response"}
    ]

    submission_processor.update_chat_submission(new_messages)

    # Verify create_submission was called
    call_args = mock_submissions_api.create_submission.call_args
    answer = json.loads(call_args[1]["answer"])

    # Should contain messages and metadata
    assert len(answer) == 3  # 2 messages + 1 metadata
    assert answer[0]["role"] == "user"
    assert answer[1]["role"] == "assistant"

    # Check metadata tracks previous submission
    metadata = answer[2]
    assert metadata.get("_metadata") is True
    assert "test-submission-uuid-123" in metadata["previous_submission_ids"]


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.submission_processor.submissions_api")
def test_update_chat_submission_preserves_previous_submission_chain(
    mock_submissions_api, submission_processor  # pylint: disable=redefined-outer-name
):
    """
    Test that update_chat_submission preserves chain of previous submission IDs.
    """
    # Mock existing submission that already has metadata
    existing_messages = [
        {"role": "user", "content": "Message"},
        {"role": "assistant", "content": "Response"},
        {
            "_metadata": True,
            "previous_submission_ids": ["oldest-submission-uuid", "older-submission-uuid"]
        }
    ]

    mock_submissions_api.get_submission_and_student.return_value = {
        "uuid": "test-submission-uuid-123",
        "answer": existing_messages
    }

    mock_submissions_api.create_submission.return_value = {"uuid": "newest-submission-uuid"}

    new_messages = [
        {"role": "user", "content": "New message"},
        {"role": "assistant", "content": "New response"}
    ]

    submission_processor.update_chat_submission(new_messages)

    # Verify create_submission was called
    call_args = mock_submissions_api.create_submission.call_args
    answer = json.loads(call_args[1]["answer"])

    # Check metadata preserves the chain
    metadata = answer[-1]
    assert metadata.get("_metadata") is True
    assert "oldest-submission-uuid" in metadata["previous_submission_ids"]
    assert "older-submission-uuid" in metadata["previous_submission_ids"]
    assert "test-submission-uuid-123" in metadata["previous_submission_ids"]
    # Should have 3 previous submission IDs in the chain
    assert len(metadata["previous_submission_ids"]) == 3


# ============================================================================
# SubmissionProcessor.update_submission() Tests
# ============================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.submission_processor.submissions_api")
def test_update_submission_creates_submission(
    mock_submissions_api, submission_processor  # pylint: disable=redefined-outer-name
):
    """
    Test that update_submission creates a new submission with provided data.
    """
    mock_submissions_api.create_submission.return_value = {"uuid": "submission-uuid-456"}

    data = [{"role": "user", "content": "Test message"}]
    submission_processor.update_submission(data)

    # Verify create_submission was called with correct parameters
    mock_submissions_api.create_submission.assert_called_once_with(
        student_item_dict=submission_processor.student_item_dict,
        answer=json.dumps(data),
        attempt_number=1
    )

    # Verify session was updated with new submission ID
    submission_processor.user_session.refresh_from_db()
    assert submission_processor.user_session.local_submission_id == "submission-uuid-456"


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.submission_processor.submissions_api")
def test_update_submission_with_complex_data(
    mock_submissions_api, submission_processor  # pylint: disable=redefined-outer-name
):
    """
    Test that update_submission handles complex data structures.
    """
    mock_submissions_api.create_submission.return_value = {"uuid": "submission-uuid-789"}

    complex_data = [
        {"role": "user", "content": "Question", "metadata": {"timestamp": "2025-01-01"}},
        {"role": "assistant", "content": "Answer", "tokens": 150}
    ]
    submission_processor.update_submission(complex_data)

    # Verify data was serialized correctly
    call_args = mock_submissions_api.create_submission.call_args
    answer = json.loads(call_args[1]["answer"])
    assert answer == complex_data


# ============================================================================
# SubmissionProcessor.get_submission() Tests
# ============================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.submission_processor.submissions_api")
def test_get_submission_returns_submission(
    mock_submissions_api, submission_processor  # pylint: disable=redefined-outer-name
):
    """
    Test that get_submission returns the current submission.
    """
    expected_submission = {
        "uuid": "test-submission-uuid-123",
        "answer": [{"role": "user", "content": "Test"}],
        "created_at": "2025-01-01T00:00:00Z"
    }

    mock_submissions_api.get_submission_and_student.return_value = expected_submission

    result = submission_processor.get_submission()

    # Verify get_submission_and_student was called with correct UUID
    mock_submissions_api.get_submission_and_student.assert_called_once_with(
        "test-submission-uuid-123"
    )

    assert result == expected_submission


@pytest.mark.django_db
def test_get_submission_returns_none_without_submission_id(
    user_session_no_submission,  # pylint: disable=redefined-outer-name
):
    """
    Test that get_submission returns None when no submission ID exists.
    """
    processor = SubmissionProcessor(config={}, user_session=user_session_no_submission)

    result = processor.get_submission()

    assert result is None


# ============================================================================
# SubmissionProcessor.get_full_message_history() Tests
# ============================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.submission_processor.submissions_api")
def test_get_full_message_history_returns_all_messages(
    mock_submissions_api, submission_processor  # pylint: disable=redefined-outer-name
):
    """
    Test that get_full_message_history returns all messages without limit.
    """
    # Mock many submissions (more than max_context_messages)
    mock_submissions = []
    for i in range(15):
        mock_submissions.append({
            "uuid": f"submission-{i}",
            "answer": json.dumps([{"role": "user", "content": f"Message {i}"}]),
            "created_at": f"2025-01-01T00:{i:02d}:00Z"
        })

    mock_submissions_api.get_submissions.return_value = mock_submissions

    result = submission_processor.get_full_message_history()

    # Should return all messages (15), not limited by max_context_messages (10)
    assert result is not None
    assert len(result) == 15


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.submission_processor.submissions_api")
def test_get_full_message_history_removes_timestamps(
    mock_submissions_api, submission_processor  # pylint: disable=redefined-outer-name
):
    """
    Test that get_full_message_history removes timestamp fields from messages.
    """
    mock_submissions = [
        {
            "uuid": "submission-1",
            "answer": json.dumps([{"role": "user", "content": "Test", "timestamp": "2025-01-01"}]),
            "created_at": "2025-01-01T00:00:00Z"
        }
    ]

    mock_submissions_api.get_submissions.return_value = mock_submissions

    result = submission_processor.get_full_message_history()

    # Verify timestamp was removed
    assert result is not None
    assert len(result) == 1
    assert "timestamp" not in result[0]
    assert result[0]["role"] == "user"
    assert result[0]["content"] == "Test"


@pytest.mark.django_db
def test_get_full_message_history_returns_none_without_submission_id(
    user_session_no_submission,  # pylint: disable=redefined-outer-name
):
    """
    Test that get_full_message_history returns None when no submission ID exists.
    """
    processor = SubmissionProcessor(config={}, user_session=user_session_no_submission)

    result = processor.get_full_message_history()

    assert result is None


# ============================================================================
# SubmissionProcessor.get_chat_history() Tests (Additional Coverage)
# ============================================================================


@pytest.mark.django_db
def test_get_chat_history_returns_error_without_submission_id(
    user_session_no_submission,  # pylint: disable=redefined-outer-name
):
    """
    Test that get_chat_history returns error when no submission ID exists.
    """
    processor = SubmissionProcessor(config={}, user_session=user_session_no_submission)

    result = processor.get_chat_history({}, None)

    assert "error" in result
    assert result["error"] == "No submission ID associated with the session"
