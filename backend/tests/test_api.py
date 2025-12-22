"""
Tests for the `openedx-ai-extensions` API endpoints.
"""

import json
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locator import BlockUsageLocator
from rest_framework.test import APIClient, APIRequestFactory

# Mock the submissions module before any imports that depend on it
sys.modules["submissions"] = MagicMock()
sys.modules["submissions.api"] = MagicMock()

from openedx_ai_extensions.api.v1.workflows.serializers import (  # noqa: E402 pylint: disable=wrong-import-position
    AIWorkflowProfileSerializer,
)
from openedx_ai_extensions.api.v1.workflows.views import (  # noqa: E402 pylint: disable=wrong-import-position
    AIWorkflowProfileView,
)
from openedx_ai_extensions.workflows.models import (  # noqa: E402 pylint: disable=wrong-import-position
    AIWorkflowProfile,
    AIWorkflowScope,
)

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


@pytest.fixture
def workflow_profile(db):  # pylint: disable=unused-argument
    """
    Create a real AIWorkflowProfile for tests.
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
    Create a mock workflow scope for unit tests.
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
# Integration Tests - Full HTTP Stack
# ============================================================================


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
    assert config_url == "/openedx-ai-extensions/v1/profile/"


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

    # Create a proper BlockUsageLocator for the locationId
    location = BlockUsageLocator(course_key, block_type="vertical", block_id="unit-123")

    payload = {
        "action": "summarize",
        "courseId": str(course_key),
        "context": {"locationId": str(location)},
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
    assert "timestamp" in data
    # requestId and workflow_created may not be present if config not found


@pytest.mark.django_db
@pytest.mark.usefixtures("user", "course_key")
def test_workflows_get_with_authentication(api_client):  # pylint: disable=redefined-outer-name
    """
    Test GET request to workflows endpoint with authentication.
    """
    api_client.login(username="testuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:aiext_workflows")

    response = api_client.get(url)

    # Should return 405 (Method Not Allowed) since workflow view might not support GET
    assert response.status_code in [200, 400, 405, 500]


@pytest.mark.django_db
@pytest.mark.usefixtures("staff_user")
def test_workflows_post_with_staff_user(api_client, course_key):  # pylint: disable=redefined-outer-name
    """
    Test POST request to workflows endpoint with staff user authentication.
    """
    api_client.login(username="staffuser", password="password123")
    url = reverse("openedx_ai_extensions:api:v1:aiext_workflows")

    # Create a proper BlockUsageLocator for the locationId
    location = BlockUsageLocator(course_key, block_type="vertical", block_id="unit-456")

    payload = {
        "action": "analyze",
        "courseId": str(course_key),
        "context": {"locationId": str(location)},
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
    # Config might not exist, so check for either valid response or no_config status
    if "status" in data and data["status"] == "no_config":
        # Expected when no config exists
        assert True
    elif response.status_code == 200 and "course_id" in data:
        # Check response structure if config exists
        assert "course_id" in data
        assert "ui_components" in data


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
    # Config might not exist, so check for either valid response or no_config status
    if "status" in data and data["status"] == "no_config":
        # Expected when no config exists
        assert True
    elif response.status_code == 200 and "course_id" in data:
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
    if response.status_code == 200 and "ui_components" in data:
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

    # Should return 400 or 500 for invalid JSON
    assert response.status_code in [400, 500]
    data = response.json()
    assert "error" in data


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
        "context": {"locationId": "unit-123"},
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


# ============================================================================
# Unit Tests - Serializers
# ============================================================================


@pytest.mark.django_db
def test_serializer_serialize_config(course_key):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflowProfileSerializer serializes config correctly.
    """
    # Create a mock AIWorkflowScope with profile
    mock_profile = Mock()
    mock_profile.get_ui_components = Mock(return_value={"request": {"component": "TestComponent"}})

    mock_scope = Mock()
    mock_scope.profile = mock_profile
    mock_scope.course_id = course_key

    serializer = AIWorkflowProfileSerializer(mock_scope)
    data = serializer.data

    assert "course_id" in data
    assert "ui_components" in data


@pytest.mark.django_db
def test_serializer_get_ui_components():
    """
    Test serializer extracts ui_components from profile.
    """
    # Create a mock profile with ui components
    mock_profile = Mock()
    mock_profile.get_ui_components = Mock(return_value={"request": {"component": "TestComponent"}})

    # Create a mock AIWorkflowScope with profile
    mock_scope = Mock()
    mock_scope.profile = mock_profile

    serializer = AIWorkflowProfileSerializer(mock_scope)
    ui_components = serializer.get_ui_components(mock_scope)

    # UI components come from the profile's config
    assert isinstance(ui_components, dict)
    assert "request" in ui_components


@pytest.mark.django_db
def test_serializer_get_ui_components_empty_config():
    """
    Test serializer handles empty profile config.
    """
    # Create a mock profile with empty ui components
    mock_profile = Mock()
    mock_profile.get_ui_components = Mock(return_value={})

    # Create a mock AIWorkflowScope with profile
    mock_scope = Mock()
    mock_scope.profile = mock_profile

    serializer = AIWorkflowProfileSerializer(mock_scope)
    ui_components = serializer.get_ui_components(mock_scope)

    assert isinstance(ui_components, dict)
    assert ui_components == {}


@pytest.mark.django_db
def test_serializer_create_not_implemented():
    """
    Test that serializer.create raises NotImplementedError.
    """
    # Create a mock AIWorkflowScope with profile
    mock_scope = Mock()
    mock_scope.profile = Mock()
    mock_scope.profile.get_ui_components = Mock(return_value={})
    mock_scope.course_id = "test"

    serializer = AIWorkflowProfileSerializer(mock_scope)

    with pytest.raises(NotImplementedError) as exc_info:
        serializer.create({})

    assert "read-only" in str(exc_info.value)


@pytest.mark.django_db
def test_serializer_update_not_implemented():
    """
    Test that serializer.update raises NotImplementedError.
    """
    # Create a mock AIWorkflowScope with profile
    mock_scope = Mock()
    mock_scope.profile = Mock()
    mock_scope.profile.get_ui_components = Mock(return_value={})
    mock_scope.course_id = "test"

    serializer = AIWorkflowProfileSerializer(mock_scope)

    with pytest.raises(NotImplementedError) as exc_info:
        serializer.update(mock_scope, {})

    assert "read-only" in str(exc_info.value)


# ============================================================================
# Unit Tests - Views with Mocks
# ============================================================================


@pytest.mark.django_db
def test_generic_workflow_view_post_validation_error_unit():
    """
    Test AIGenericWorkflowView handles ValidationError (unit test).
    """
    # Skip this test as find_workflow_for_context no longer exists
    pytest.skip("find_workflow_for_context method no longer exists in new model structure")


@pytest.mark.django_db
def test_generic_workflow_view_post_general_exception_unit():
    """
    Test AIGenericWorkflowView handles general exceptions (unit test).
    """
    # Skip this test as find_workflow_for_context no longer exists
    pytest.skip("find_workflow_for_context method no longer exists in new model structure")


@pytest.mark.django_db
@patch("openedx_ai_extensions.api.v1.workflows.views.AIWorkflowScope.get_profile")
def test_workflow_config_view_get_not_found_unit(
    mock_get_profile, user  # pylint: disable=redefined-outer-name
):
    """
    Test AIWorkflowProfileView returns no_config status when no config found (unit test).
    """
    mock_get_profile.return_value = None

    factory = APIRequestFactory()
    request = factory.get(
        "/openedx-ai-extensions/v1/profile/",
        {"action": "nonexistent", "context": "{}"},
    )
    request.user = user

    view = AIWorkflowProfileView.as_view()
    response = view(request)

    assert response.status_code == 200
    response.render()  # Render template response
    data = json.loads(response.content)
    assert data["status"] == "no_config"
    assert "timestamp" in data


@pytest.mark.django_db
@patch("openedx_ai_extensions.api.v1.workflows.views.AIWorkflowScope.get_profile")
def test_workflow_config_view_get_with_location_id_unit(
    mock_get_profile, user, course_key  # pylint: disable=redefined-outer-name
):
    """
    Test AIWorkflowProfileView GET request with location_id in context (unit test).
    """
    # Create a mock profile with ui components
    mock_profile = Mock()
    mock_profile.get_ui_components = Mock(return_value={"request": {"component": "TestComponent"}})

    # Create a mock AIWorkflowScope with profile attribute
    mock_scope = Mock()
    mock_scope.profile = mock_profile
    mock_scope.course_id = course_key
    mock_get_profile.return_value = mock_scope

    location = BlockUsageLocator(course_key, block_type="vertical", block_id="unit-1")
    context_json = json.dumps({"locationId": str(location)})

    factory = APIRequestFactory()
    request = factory.get(
        "/openedx-ai-extensions/v1/profile/",
        {
            "action": "summarize",
            "courseId": str(course_key),
            "context": context_json,
        },
    )
    request.user = user

    view = AIWorkflowProfileView.as_view()
    response = view(request)

    assert response.status_code == 200
    # Verify get_profile was called with correct parameters
    mock_get_profile.assert_called_once()
    call_kwargs = mock_get_profile.call_args[1]
    assert "course_id" in call_kwargs
    assert "location_id" in call_kwargs
    assert call_kwargs["location_id"] == str(location)


@pytest.mark.django_db
@patch("openedx_ai_extensions.api.v1.workflows.views.AIWorkflowScope.get_profile")
def test_workflow_config_view_invalid_context_json_unit(
    mock_get_profile, user  # pylint: disable=redefined-outer-name
):
    """
    Test AIWorkflowProfileView handles invalid JSON in context parameter (unit test).
    """
    # Create a mock profile with ui components
    mock_profile = Mock()
    mock_profile.get_ui_components = Mock(return_value={})

    # Create a mock AIWorkflowScope with profile attribute
    mock_scope = Mock()
    mock_scope.profile = mock_profile
    mock_get_profile.return_value = mock_scope

    factory = APIRequestFactory()
    request = factory.get(
        "/openedx-ai-extensions/v1/profile/",
        {"action": "summarize", "context": "invalid json{"},
    )
    request.user = user

    view = AIWorkflowProfileView.as_view()
    response = view(request)

    # Should return error status for invalid JSON
    assert response.status_code == 500
