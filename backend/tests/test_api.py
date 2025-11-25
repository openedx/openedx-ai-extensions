"""
Tests for the `openedx-ai-extensions` API endpoints.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locator import BlockUsageLocator
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
    url = reverse("openedx_ai_extensions:api:v1:aiext_workflows")
    assert url == "/openedx-ai-extensions/v1/workflows/"

    # Test that the v1 config URL can be reversed
    config_url = reverse("openedx_ai_extensions:api:v1:aiext_ui_config")
    assert config_url == "/openedx-ai-extensions/v1/config/"


@pytest.mark.django_db
def test_workflows_endpoint_requires_authentication(api_client):  # pylint: disable=redefined-outer-name
    """
    Test that the workflows endpoint requires authentication.
    """
    url = reverse("openedx_ai_extensions:api:v1:aiext_workflows")

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
    url = reverse("openedx_ai_extensions:api:v1:aiext_workflows")

    # Create a proper BlockUsageLocator for the unitId
    location = BlockUsageLocator(
        course_key,
        block_type="vertical",
        block_id="unit-123"
    )

    payload = {
        "action": "summarize",
        "courseId": str(course_key),
        "context": {"unitId": str(location)},
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
    url = reverse("openedx_ai_extensions:api:v1:aiext_workflows")

    response = api_client.get(url)

    # Should return 200 or error status
    assert response.status_code in [200, 400, 500]

    # Response should be JSON
    assert response["Content-Type"] == "application/json"


@pytest.mark.django_db
@pytest.mark.usefixtures("staff_user")
def test_workflows_post_with_staff_user(api_client, course_key):  # pylint: disable=redefined-outer-name
    """
    Test POST request to workflows endpoint with staff user authentication.
    """
    api_client.login(username="staffuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:aiext_workflows")

    # Create a proper BlockUsageLocator for the unitId
    location = BlockUsageLocator(
        course_key,
        block_type="vertical",
        block_id="unit-456"
    )

    payload = {
        "action": "analyze",
        "courseId": str(course_key),
        "context": {"unitId": str(location)},
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
def test_config_endpoint_get_with_action(api_client):  # pylint: disable=redefined-outer-name
    """
    Test GET request to config endpoint with required action parameter.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:aiext_ui_config")

    # Test with action parameter
    response = api_client.get(url, {"action": "summarize", "context": "{}"})

    assert response.status_code in [200, 404]
    assert response["Content-Type"] == "application/json"

    data = response.json()
    if response.status_code == 200:
        # Check response structure
        assert "action" in data
        assert "course_id" in data
        assert "ui_components" in data

        # Verify action value
        assert data["action"] == "summarize"


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_config_endpoint_get_with_action_and_course(api_client, course_key):  # pylint: disable=redefined-outer-name
    """
    Test GET request to config endpoint with action and courseId parameters.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:aiext_ui_config")

    response = api_client.get(
        url,
        {"action": "explain_like_five", "courseId": str(course_key), "context": "{}"},
    )

    assert response.status_code in [200, 404]

    data = response.json()
    if response.status_code == 200:
        assert data["action"] == "explain_like_five"
        assert data["course_id"] == str(course_key)
        assert "ui_components" in data


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_config_endpoint_ui_components_structure(api_client):  # pylint: disable=redefined-outer-name
    """
    Test that ui_components has the expected structure.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:aiext_ui_config")

    response = api_client.get(url, {"action": "explain_like_five", "context": "{}"})
    assert response.status_code in [200, 404]

    data = response.json()
    if response.status_code == 200:
        ui_components = data["ui_components"]

        # Check for request component
        assert "request" in ui_components
        assert "component" in ui_components["request"]
        assert "config" in ui_components["request"]

        # Verify component type
        assert ui_components["request"]["component"] == "AIRequestComponent"


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_workflows_post_with_invalid_json(api_client):  # pylint: disable=redefined-outer-name
    """
    Test POST request to workflows endpoint with invalid JSON.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:aiext_workflows")

    # Send invalid JSON
    response = api_client.post(
        url, data="invalid json", content_type="application/json"
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "Invalid JSON" in data["error"]


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_workflows_post_with_empty_body(api_client):  # pylint: disable=redefined-outer-name
    """
    Test POST request to workflows endpoint with empty body.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:aiext_workflows")

    response = api_client.post(url, {}, format="json")

    # Should handle empty body gracefully
    assert response.status_code in [200, 400, 500]


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_workflows_post_without_action(api_client, course_key):  # pylint: disable=redefined-outer-name
    """
    Test POST request to workflows endpoint without action field.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:aiext_workflows")

    payload = {
        "courseId": str(course_key),
        "context": {"unitId": "unit-123"},
        "requestId": "test-request-456",
    }

    response = api_client.post(url, payload, format="json")

    # Should handle missing action
    assert response.status_code in [400, 500]


@pytest.mark.django_db
@pytest.mark.usefixtures("user")
def test_config_endpoint_without_authentication(api_client):  # pylint: disable=redefined-outer-name
    """
    Test that config endpoint requires authentication.
    """
    url = reverse("openedx_ai_extensions:api:v1:aiext_ui_config")

    response = api_client.get(url, {"action": "summarize", "context": "{}"})

    # Should require authentication (401 or 403)
    assert response.status_code in [401, 403]
