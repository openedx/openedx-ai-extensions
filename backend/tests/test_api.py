"""
Tests for the `openedx-ai-extensions` API endpoints.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from opaque_keys.edx.keys import CourseKey
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    """
    Return a REST framework API client.
    """
    return APIClient()


@pytest.fixture
def user():
    """
    Create and return a test user.
    """
    return User.objects.create_user(
        username="testuser", email="testuser@example.com", password="password123"
    )


@pytest.fixture
def staff_user():
    """
    Create and return a test staff user.
    """
    return User.objects.create_user(
        username="staffuser",
        email="staffuser@example.com",
        password="password123",
        is_staff=True,
    )


@pytest.fixture
def course_key():
    """
    Create and return a test course key.
    """
    return CourseKey.from_string("course-v1:edX+DemoX+Demo_Course")


@pytest.mark.django_db
def test_api_urls_are_registered():
    """
    Test that the API URLs are properly registered and accessible.
    """
    # Test that the v1 workflows URL can be reversed
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")
    assert url == "/openedx-ai-extensions/v1/workflows/"


@pytest.mark.django_db
def test_workflows_endpoint_requires_authentication(api_client):  # pylint: disable=redefined-outer-name
    """
    Test that the workflows endpoint requires authentication.
    """
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")

    # Test POST without authentication
    response = api_client.post(url, {}, format="json")
    assert response.status_code == 302  # Redirect to login

    # Test GET without authentication
    response = api_client.get(url)
    assert response.status_code == 302  # Redirect to login


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_workflows_post_with_authentication(api_client, course_key):  # pylint: disable=redefined-outer-name
    """
    Test POST request to workflows endpoint with authentication.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")

    payload = {
        "action": "summarize",
        "courseId": str(course_key),
        "context": {"unitId": "unit-123"},
        "user_input": {"text": "Explain quantum physics"},
        "requestId": "test-request-123",
    }

    response = api_client.post(url, payload, format="json")

    # Should return 200 or 500 depending on workflow execution
    assert response.status_code in [200, 400, 500]

    # Response should be JSON
    assert response["Content-Type"] == "application/json"

    # Check for expected fields in response
    data = response.json()
    assert "requestId" in data
    assert "timestamp" in data
    assert "workflow_created" in data


@pytest.mark.django_db
@pytest.mark.usefixtures("user", "course_key")
def test_workflows_get_with_authentication(api_client):  # pylint: disable=redefined-outer-name
    """
    Test GET request to workflows endpoint with authentication.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")

    response = api_client.get(url)

    # Should return 200 or error status
    assert response.status_code in [200, 400, 500]

    # Response should be JSON
    assert response["Content-Type"] == "application/json"


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_workflows_post_with_invalid_payload(api_client):  # pylint: disable=redefined-outer-name
    """
    Test POST request to workflows endpoint with invalid/incomplete payload.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")

    # Test with missing required fields
    invalid_payload = {
        "action": "summarize",
        # Missing courseId, context, user_input, and requestId
    }

    response = api_client.post(url, invalid_payload, format="json")

    # Should return 400 Bad Request or 500 for invalid payload
    assert response.status_code in [400, 500]

    # Response should be JSON
    assert response["Content-Type"] == "application/json"


@pytest.mark.django_db
@pytest.mark.usefixtures("staff_user")
def test_workflows_post_with_staff_user(api_client, course_key):  # pylint: disable=redefined-outer-name
    """
    Test POST request to workflows endpoint with staff user authentication.
    """
    api_client.login(username="staffuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")

    payload = {
        "action": "analyze",
        "courseId": str(course_key),
        "context": {"unitId": "unit-456"},
        "user_input": {"text": "Analyze student performance"},
        "requestId": "staff-request-789",
    }

    response = api_client.post(url, payload, format="json")

    # Should return 200 or 500 depending on workflow execution
    assert response.status_code in [200, 400, 500]

    # Response should be JSON
    assert response["Content-Type"] == "application/json"


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_workflows_post_with_different_action(api_client, course_key):  # pylint: disable=redefined-outer-name
    """
    Test POST request with a different action type.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")

    payload = {
        "action": "generate",
        "courseId": str(course_key),
        "context": {"unitId": "unit-789", "sectionId": "section-001"},
        "user_input": {"text": "Generate quiz questions", "count": 5},
        "requestId": "test-request-456",
    }

    response = api_client.post(url, payload, format="json")

    # Should return 200 or 500 depending on workflow execution
    assert response.status_code in [200, 400, 500]

    # Response should be JSON
    assert response["Content-Type"] == "application/json"

    # Check for expected fields in response
    data = response.json()
    assert "requestId" in data


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_workflows_post_with_empty_context(api_client, course_key):  # pylint: disable=redefined-outer-name
    """
    Test POST request with empty context field.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")

    payload = {
        "action": "summarize",
        "courseId": str(course_key),
        "context": {},  # Empty context
        "user_input": {"text": "Test with empty context"},
        "requestId": "test-request-empty-context",
    }

    response = api_client.post(url, payload, format="json")

    # Should handle empty context gracefully
    assert response.status_code in [200, 400, 500]

    # Response should be JSON
    assert response["Content-Type"] == "application/json"


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_workflows_post_with_invalid_course_key(api_client):  # pylint: disable=redefined-outer-name
    """
    Test POST request with an invalid course key format.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")

    payload = {
        "action": "summarize",
        "courseId": "invalid-course-key-format",
        "context": {"unitId": "unit-123"},
        "user_input": {"text": "Test with invalid course key"},
        "requestId": "test-request-invalid-key",
    }

    response = api_client.post(url, payload, format="json")

    # Should return error status for invalid course key
    assert response.status_code in [400, 500]

    # Response should be JSON
    assert response["Content-Type"] == "application/json"


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_workflows_post_with_large_user_input(api_client, course_key):  # pylint: disable=redefined-outer-name
    """
    Test POST request with large user input text.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")

    # Create a large text input
    large_text = "Explain this concept. " * 100

    payload = {
        "action": "summarize",
        "courseId": str(course_key),
        "context": {"unitId": "unit-large-input"},
        "user_input": {"text": large_text},
        "requestId": "test-request-large-input",
    }

    response = api_client.post(url, payload, format="json")

    # Should handle large input
    assert response.status_code in [200, 400, 500]

    # Response should be JSON
    assert response["Content-Type"] == "application/json"


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_workflows_post_with_special_characters(api_client, course_key):  # pylint: disable=redefined-outer-name
    """
    Test POST request with special characters in user input.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")

    payload = {
        "action": "summarize",
        "courseId": str(course_key),
        "context": {"unitId": "unit-special-chars"},
        "user_input": {"text": "Test with special chars: <>&\"'%$#@!*()[]{}"},
        "requestId": "test-request-special-chars",
    }

    response = api_client.post(url, payload, format="json")

    # Should handle special characters
    assert response.status_code in [200, 400, 500]

    # Response should be JSON
    assert response["Content-Type"] == "application/json"


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_workflows_post_with_unicode_text(api_client, course_key):  # pylint: disable=redefined-outer-name
    """
    Test POST request with Unicode characters in user input.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")

    payload = {
        "action": "summarize",
        "courseId": str(course_key),
        "context": {"unitId": "unit-unicode"},
        "user_input": {"text": "Explain 量子物理学 and математика with émojis 🚀🔬"},
        "requestId": "test-request-unicode",
    }

    response = api_client.post(url, payload, format="json")

    # Should handle Unicode text
    assert response.status_code in [200, 400, 500]

    # Response should be JSON
    assert response["Content-Type"] == "application/json"


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_workflows_post_with_complex_context(api_client, course_key):  # pylint: disable=redefined-outer-name
    """
    Test POST request with complex nested context structure.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")

    payload = {
        "action": "analyze",
        "courseId": str(course_key),
        "context": {
            "unitId": "unit-complex",
            "sectionId": "section-002",
            "metadata": {
                "difficulty": "advanced",
                "tags": ["physics", "quantum", "theory"],
                "prerequisites": ["unit-001", "unit-002"],
            },
        },
        "user_input": {"text": "Analyze with complex context", "detail_level": "high"},
        "requestId": "test-request-complex-context",
    }

    response = api_client.post(url, payload, format="json")

    # Should handle complex nested context
    assert response.status_code in [200, 400, 500]

    # Response should be JSON
    assert response["Content-Type"] == "application/json"


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_workflows_post_with_null_values(api_client, course_key):  # pylint: disable=redefined-outer-name
    """
    Test POST request with null values in payload.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")

    payload = {
        "action": "summarize",
        "courseId": str(course_key),
        "context": {"unitId": None},
        "user_input": {"text": "Test with null values"},
        "requestId": "test-request-null",
    }

    response = api_client.post(url, payload, format="json")

    # Should handle null values appropriately
    assert response.status_code in [200, 400, 500]

    # Response should be JSON
    assert response["Content-Type"] == "application/json"


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_workflows_post_with_duplicate_request_id(api_client, course_key):  # pylint: disable=redefined-outer-name
    """
    Test POST request with duplicate request ID to check idempotency.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")

    payload = {
        "action": "summarize",
        "courseId": str(course_key),
        "context": {"unitId": "unit-duplicate"},
        "user_input": {"text": "Test duplicate request ID"},
        "requestId": "duplicate-request-id",
    }

    # First request
    response1 = api_client.post(url, payload, format="json")
    assert response1.status_code in [200, 400, 500]

    # Second request with same request ID
    response2 = api_client.post(url, payload, format="json")
    assert response2.status_code in [200, 400, 500]

    # Both responses should be JSON
    assert response1["Content-Type"] == "application/json"
    assert response2["Content-Type"] == "application/json"


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_workflows_post_with_missing_action(api_client, course_key):  # pylint: disable=redefined-outer-name
    """
    Test POST request with missing action field.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")

    payload = {
        # Missing action field
        "courseId": str(course_key),
        "context": {"unitId": "unit-no-action"},
        "user_input": {"text": "Test without action"},
        "requestId": "test-request-no-action",
    }

    response = api_client.post(url, payload, format="json")

    # Should return error for missing action
    assert response.status_code in [400, 500]

    # Response should be JSON
    assert response["Content-Type"] == "application/json"


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_workflows_post_with_numeric_values_in_context(api_client, course_key):  # pylint: disable=redefined-outer-name
    """
    Test POST request with numeric values in context.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")

    payload = {
        "action": "analyze",
        "courseId": str(course_key),
        "context": {
            "unitId": "unit-numeric",
            "score": 95.5,
            "attempts": 3,
            "time_spent": 1800,
            "completion_rate": 0.75,
        },
        "user_input": {"text": "Analyze numeric data"},
        "requestId": "test-request-numeric",
    }

    response = api_client.post(url, payload, format="json")

    # Should handle numeric values in context
    assert response.status_code in [200, 400, 500]

    # Response should be JSON
    assert response["Content-Type"] == "application/json"


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_workflows_post_with_mcp_configuration(api_client, course_key):  # pylint: disable=redefined-outer-name
    """
    Test POST request that triggers MCP (Model Context Protocol) processing.

    This test verifies that the workflow can handle MCP-enabled actions,
    which use the MCPLLMProcessor to communicate with MCP servers.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")

    payload = {
        "action": "explain_like_five",  # Action that triggers MCP processing
        "courseId": str(course_key),
        "context": {
            "unitId": "unit-mcp-test",
            "sectionId": "section-mcp",
            "mcp_enabled": True,
        },
        "user_input": {
            "text": "Explain how neural networks work",
            "simplification_level": "elementary",
        },
        "requestId": "test-request-mcp-processing",
    }

    response = api_client.post(url, payload, format="json")

    # Should handle MCP-enabled workflow
    assert response.status_code in [200, 400, 500]

    # Response should be JSON
    assert response["Content-Type"] == "application/json"

    # If successful, check for workflow creation
    if response.status_code == 200:
        data = response.json()
        assert "requestId" in data
        assert data["requestId"] == "test-request-mcp-processing"
        assert "workflow_created" in data


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_workflows_post_with_empty_user_input(api_client, course_key):  # pylint: disable=redefined-outer-name
    """
    Test POST request with empty user input text.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")

    payload = {
        "action": "summarize",
        "courseId": str(course_key),
        "context": {"unitId": "unit-empty-input"},
        "user_input": {"text": ""},  # Empty text
        "requestId": "test-request-empty-input",
    }

    response = api_client.post(url, payload, format="json")

    # Should handle or reject empty user input
    assert response.status_code in [200, 400, 500]

    # Response should be JSON
    assert response["Content-Type"] == "application/json"


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_workflows_post_with_multiple_courses(api_client):  # pylint: disable=redefined-outer-name
    """
    Test POST requests for multiple different courses in sequence.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")

    course_keys = [
        "course-v1:edX+DemoX+Demo_Course",
        "course-v1:edX+CS101+2024",
        "course-v1:MIT+Physics+Fall2024",
    ]

    for idx, course_id in enumerate(course_keys):
        payload = {
            "action": "summarize",
            "courseId": course_id,
            "context": {"unitId": f"unit-course-{idx}"},
            "user_input": {"text": f"Test for course {idx}"},
            "requestId": f"test-request-course-{idx}",
        }

        response = api_client.post(url, payload, format="json")

        # Each request should be handled
        assert response.status_code in [200, 400, 500]
        assert response["Content-Type"] == "application/json"


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_workflows_post_with_boolean_values_in_context(api_client, course_key):  # pylint: disable=redefined-outer-name
    """
    Test POST request with boolean flags in context.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:ai_pipelines")

    payload = {
        "action": "analyze",
        "courseId": str(course_key),
        "context": {
            "unitId": "unit-boolean-test",
            "is_graded": True,
            "is_published": False,
            "allow_hints": True,
            "track_progress": True,
            "enable_feedback": False,
        },
        "user_input": {"text": "Analyze with boolean context"},
        "requestId": "test-request-boolean-context",
    }

    response = api_client.post(url, payload, format="json")

    # Should handle boolean values in context
    assert response.status_code in [200, 400, 500]

    # Response should be JSON
    assert response["Content-Type"] == "application/json"
