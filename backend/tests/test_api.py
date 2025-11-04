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
