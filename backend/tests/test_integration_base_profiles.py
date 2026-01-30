"""
Integration tests for base workflow profiles.

Tests the complete flow:
1. GET /config - retrieves configuration based on location and course_id
2. POST /workflows - executes the workflow with action and user_input
"""
import json
import logging
import sys
from unittest.mock import MagicMock, patch
from urllib.parse import urlencode

import pytest
import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locator import BlockUsageLocator
from rest_framework.test import APIClient

# Mock the submissions and xmodule modules before any imports that depend on them
sys.modules["submissions"] = MagicMock()
sys.modules["submissions.api"] = MagicMock()
sys.modules["xmodule"] = MagicMock()
sys.modules["xmodule.modulestore"] = MagicMock()
sys.modules["xmodule.modulestore.django"] = MagicMock()

settings.SERVICE_VARIANT = "lms"

from openedx_ai_extensions.workflows.models import (  # noqa: E402 pylint: disable=wrong-import-position
    AIWorkflowProfile,
    AIWorkflowScope,
)

User = get_user_model()

logger = logging.getLogger(__name__)


@pytest.fixture
def api_client():
    """Return a REST framework API client."""
    return APIClient()


@pytest.fixture
def user(db):  # pylint: disable=unused-argument
    """Create and return a test user."""
    return User.objects.create_user(
        username="testuser",
        email="testuser@example.com",
        password="password123"
    )


@pytest.fixture
def course_key():
    """Create and return a test course key."""
    return CourseKey.from_string("course-v1:edX+DemoX+Demo_Course")


@pytest.fixture
def location_id(course_key):  # pylint: disable=redefined-outer-name
    """Create and return a test location."""
    return BlockUsageLocator(course_key, block_type="vertical", block_id="test_unit_123")


# ============================================================================
# Base Profile: summary.json
# ============================================================================


@pytest.mark.django_db
def test_summary_profile_integration(
    api_client, user, course_key, location_id  # pylint: disable=redefined-outer-name,unused-argument
):
    """
    Test complete flow for summary.json profile.
    Uses DirectLLMResponse orchestrator with summarize_content action.
    """
    # Create profile and scope
    profile = AIWorkflowProfile.objects.create(
        slug="test-summary",
        description="Summary workflow test",
        base_filepath="base/summary.json",
        content_patch='{}'  # Keep streaming enabled
    )

    AIWorkflowScope.objects.create(
        location_regex=".*test_unit.*",
        course_id=course_key,
        service_variant="lms",
        profile=profile,
        enabled=True
    )

    # Authenticate
    api_client.login(username="testuser", password="password123")

    # Step 1: GET /config to retrieve configuration
    config_url = reverse("openedx_ai_extensions:api:v1:aiext_ui_config")
    context = json.dumps({
        "courseId": str(course_key),
        "locationId": str(location_id)
    })

    config_response = api_client.get(config_url, {"context": context})

    assert config_response.status_code == 200
    config_data = config_response.json()
    assert "ui_components" in config_data
    assert "request" in config_data["ui_components"]
    assert config_data["ui_components"]["request"]["component"] == "AIRequestComponent"

    # Step 2: POST /workflows to execute the workflow
    workflows_url = reverse("openedx_ai_extensions:api:v1:aiext_workflows")

    # Mock the actual AI and content fetching calls for streaming
    def mock_streaming_response():
        """Generator that simulates streaming chunks."""
        test_message = "This is a summary of the content."
        for char in test_message:
            chunk = MagicMock()
            chunk.choices = [MagicMock(delta=MagicMock(content=char))]
            chunk.usage = None
            yield chunk
        # Final chunk with usage info
        final_chunk = MagicMock()
        final_chunk.choices = [MagicMock(delta=MagicMock(content=None))]
        final_chunk.usage = MagicMock(total_tokens=150)
        yield final_chunk

    with patch("openedx_ai_extensions.processors.llm.llm_processor.completion") as mock_completion, \
         patch("openedx_ai_extensions.processors.openedx.openedx_processor.OpenEdXProcessor.process") as mock_openedx:

        mock_completion.return_value = mock_streaming_response()
        mock_openedx.return_value = "Sample course content for summarization"

        workflow_payload = {
            "action": "run",
            "user_input": {}
        }

        # Include the same context query params as in the config request
        # Use urlencode to properly encode the context JSON (preserves + symbols)
        query_string = urlencode({"context": context})
        workflow_response = api_client.post(
            f"{workflows_url}?{query_string}",
            data=json.dumps(workflow_payload),
            content_type="application/json"
        )

        # Verify streaming response
        assert workflow_response.status_code == 200
        assert workflow_response["Content-Type"] == "text/plain"

        # Read streaming content
        streaming_content = b"".join(workflow_response.streaming_content).decode("utf-8")
        assert "summary" in streaming_content.lower()

        assert mock_completion.called
        assert mock_openedx.called


# ============================================================================
# Base Profile: mocked_llm_completion.json
# ============================================================================


@pytest.mark.django_db
def test_mocked_completion_profile_integration(
    api_client, user, course_key, location_id  # pylint: disable=redefined-outer-name,unused-argument
):
    """
    Test complete flow for mocked_llm_completion.json profile.
    Uses MockResponse orchestrator - no external calls needed.
    """
    # Create profile and scope
    profile = AIWorkflowProfile.objects.create(
        slug="test-mocked-completion",
        description="Mocked completion workflow test",
        base_filepath="base/mocked_llm_completion.json",
        content_patch='{}'
    )

    AIWorkflowScope.objects.create(
        location_regex=".*test_unit.*",
        course_id=course_key,
        service_variant="lms",
        profile=profile,
        enabled=True
    )

    # Authenticate
    api_client.login(username="testuser", password="password123")

    # Step 1: GET /config
    config_url = reverse("openedx_ai_extensions:api:v1:aiext_ui_config")
    context = json.dumps({
        "courseId": str(course_key),
        "locationId": str(location_id)
    })

    config_response = api_client.get(config_url, {"context": context})

    assert config_response.status_code == 200
    config_data = config_response.json()
    assert "ui_components" in config_data
    assert config_data["ui_components"]["request"]["component"] == "AIRequestComponent"
    assert config_data["ui_components"]["response"]["component"] == "AISidebarResponse"

    # Step 2: POST /workflows - MockResponse doesn't need any mocking
    workflows_url = reverse("openedx_ai_extensions:api:v1:aiext_workflows")

    workflow_payload = {
        "action": "run",
        "user_input": {}
    }

    query_string = urlencode({"context": context})
    workflow_response = api_client.post(
        f"{workflows_url}?{query_string}",
        data=json.dumps(workflow_payload),
        content_type="application/json"
    )

    # MockResponse returns JSON immediately
    assert workflow_response.status_code == 200
    response_data = workflow_response.json()
    assert response_data["status"] == "completed"
    assert "response" in response_data
    assert "Mock response" in response_data["response"]


# ============================================================================
# Base Profile: mocked_llm_streaming.json
# ============================================================================


@pytest.mark.django_db
def test_mocked_streaming_profile_integration(
    api_client, user, course_key, location_id  # pylint: disable=redefined-outer-name,unused-argument
):
    """
    Test complete flow for mocked_llm_streaming.json profile.
    Uses MockStreamResponse orchestrator - no external calls needed.
    """
    # Create profile and scope
    profile = AIWorkflowProfile.objects.create(
        slug="test-mocked-streaming",
        description="Mocked streaming workflow test",
        base_filepath="base/mocked_llm_streaming.json",
        content_patch='{}'
    )

    AIWorkflowScope.objects.create(
        location_regex=".*test_unit.*",
        course_id=course_key,
        service_variant="lms",
        profile=profile,
        enabled=True
    )

    # Authenticate
    api_client.login(username="testuser", password="password123")

    # Step 1: GET /config
    config_url = reverse("openedx_ai_extensions:api:v1:aiext_ui_config")
    context = json.dumps({
        "courseId": str(course_key),
        "locationId": str(location_id)
    })

    config_response = api_client.get(config_url, {"context": context})

    assert config_response.status_code == 200
    config_data = config_response.json()
    assert "ui_components" in config_data
    assert config_data["ui_components"]["response"]["component"] == "AISidebarResponse"

    # Step 2: POST /workflows - MockStreamResponse doesn't need any mocking
    workflows_url = reverse("openedx_ai_extensions:api:v1:aiext_workflows")

    workflow_payload = {
        "action": "run",
        "user_input": {}
    }

    query_string = urlencode({"context": context})
    workflow_response = api_client.post(
        f"{workflows_url}?{query_string}",
        data=json.dumps(workflow_payload),
        content_type="application/json"
    )

    # MockStreamResponse returns streaming response
    assert workflow_response.status_code == 200
    assert workflow_response["Content-Type"] == "text/plain"

    # Read streaming content
    streaming_content = b"".join(workflow_response.streaming_content).decode("utf-8")
    assert len(streaming_content) > 0
    assert "streaming" in streaming_content.lower()


# ============================================================================
# Base Profile: library_questions_assistant.json
# ============================================================================


@pytest.mark.django_db
def test_library_questions_assistant_profile_integration(
    api_client, user, course_key, location_id  # pylint: disable=redefined-outer-name,unused-argument
):
    """
    Test complete flow for library_questions_assistant.json profile.
    Uses EducatorAssistantOrchestrator - requires mocking AI and library operations.
    Works in CMS (Studio) service variant.
    """
    # Create profile and scope for CMS
    profile = AIWorkflowProfile.objects.create(
        slug="test-library-questions",
        description="Library questions assistant workflow test",
        base_filepath="base/library_questions_assistant.json",
        content_patch='{}'
    )

    AIWorkflowScope.objects.create(
        location_regex=".*test_unit.*",
        course_id=course_key,
        service_variant="cms",  # This profile is for Studio (CMS)
        profile=profile,
        enabled=True
    )

    # Authenticate
    api_client.login(username="testuser", password="password123")

    # Step 1: GET /config (need to mock SERVICE_VARIANT to be cms)
    config_url = reverse("openedx_ai_extensions:api:v1:aiext_ui_config")
    context = json.dumps({
        "courseId": str(course_key),
        "locationId": str(location_id)
    })

    with patch("openedx_ai_extensions.workflows.models.settings.SERVICE_VARIANT", "cms"):
        config_response = api_client.get(config_url, {"context": context})

        assert config_response.status_code == 200
        config_data = config_response.json()
        assert "ui_components" in config_data
        assert config_data["ui_components"]["request"]["component"] == "AIEducatorLibraryAssistComponent"
        assert config_data["ui_components"]["response"]["component"] == "AIEducatorLibraryResponseComponent"

        # Step 2: POST /workflows - Mock AI and library processor
        workflows_url = reverse("openedx_ai_extensions:api:v1:aiext_workflows")

        # Mock LLM response for quiz generation
        mock_llm_response = {
            "response": {
                "collection": "AI Generated Quiz Questions",
                "items": [
                    {
                        "question": "What is Python?",
                        "options": ["A snake", "A programming language", "A tool", "A framework"],
                        "correct_answer": 1
                    },
                    {
                        "question": "What is Django?",
                        "options": ["A database", "A web framework", "A language", "An editor"],
                        "correct_answer": 1
                    }
                ]
            },
            "tokens_used": 200,
            "model_used": "gpt-4"
        }

        educator_path = (
            "openedx_ai_extensions.processors.llm.educator_assistant_processor."
            "EducatorAssistantProcessor.process"
        )
        openedx_path = (
            "openedx_ai_extensions.processors.openedx.openedx_processor."
            "OpenEdXProcessor.process"
        )
        library_path = (
            "openedx_ai_extensions.processors.openedx.content_libraries_processor."
            "ContentLibraryProcessor.create_collection_and_add_items"
        )

        with patch(educator_path) as mock_educator, \
             patch(openedx_path) as mock_openedx, \
             patch(library_path) as mock_library:

            mock_educator.return_value = mock_llm_response
            mock_openedx.return_value = "Sample course unit content for quiz generation"
            mock_library.return_value = "collection-v1:test-collection-key"

            workflow_payload = {
                "action": "run",
                "user_input": {
                    "library_id": "lib:test:library-123",
                    "num_questions": 5
                }
            }

            query_string = urlencode({"context": context})
            workflow_response = api_client.post(
                f"{workflows_url}?{query_string}",
                data=json.dumps(workflow_payload),
                content_type="application/json"
            )

            assert workflow_response.status_code == 200
            response_data = workflow_response.json()
            assert response_data["status"] == "completed"
            assert "response" in response_data
            assert "collection" in response_data["response"]
            assert mock_educator.called
            assert mock_openedx.called
            assert mock_library.called
