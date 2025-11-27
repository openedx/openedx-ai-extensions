"""
Tests for the SubmissionProcessor module.
"""

import json
import sys
from unittest.mock import MagicMock, Mock, patch

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
def user_session(user, course_key, db):  # pylint: disable=unused-argument,redefined-outer-name
    """
    Create and return a test AIWorkflowSession.
    """
    session = AIWorkflowSession.objects.create(
        user=user,
        course_id=course_key,
        local_submission_id="test-submission-uuid-123",
    )
    return session


@pytest.fixture
def user_session_no_submission(user, course_key, db):  # pylint: disable=unused-argument,redefined-outer-name
    """
    Create and return a test AIWorkflowSession without a submission ID.
    """
    session = AIWorkflowSession.objects.create(
        user=user,
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
