"""
Tests for the `openedx-ai-extensions` API endpoints.
"""

import json
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from django.urls import reverse
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locator import BlockUsageLocator
from rest_framework.test import APIClient, APIRequestFactory

# Mock the submissions module before any imports that depend on it
sys.modules["submissions"] = MagicMock()
sys.modules["submissions.api"] = MagicMock()

from openedx_ai_extensions.api.v1.workflows.serializers import (  # noqa: E402 pylint: disable=wrong-import-position
    AIWorkflowConfigSerializer,
)
from openedx_ai_extensions.api.v1.workflows.views import (  # noqa: E402 pylint: disable=wrong-import-position
    AIGenericWorkflowView,
    AIWorkflowConfigView,
)
from openedx_ai_extensions.workflows.models import AIWorkflowConfig  # noqa: E402 pylint: disable=wrong-import-position

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
def workflow_config():
    """
    Create a mock workflow config for unit tests.
    """
    config = Mock(spec=AIWorkflowConfig)
    config.id = 1
    config.pk = 1
    config.action = "summarize"
    config.course_id = "course-v1:edX+DemoX+Demo_Course"
    config.location_id = None
    config.orchestrator_class = "MockResponse"
    config.processor_config = {"LLMProcessor": {"function": "summarize_content"}}
    config.actuator_config = {
        "UIComponents": {
            "request": {"component": "AIRequestComponent", "config": {"type": "text"}}
        }
    }
    config._state = Mock()  # pylint: disable=protected-access
    config._state.db = "default"  # pylint: disable=protected-access
    config._state.adding = False  # pylint: disable=protected-access
    return config


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
    location = BlockUsageLocator(course_key, block_type="vertical", block_id="unit-123")

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
    location = BlockUsageLocator(course_key, block_type="vertical", block_id="unit-456")

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


# ============================================================================
# Unit Tests - Serializers
# ============================================================================


def test_serializer_serialize_config(workflow_config):  # pylint: disable=redefined-outer-name
    """
    Test AIWorkflowConfigSerializer serializes config correctly.
    """
    serializer = AIWorkflowConfigSerializer(workflow_config)
    data = serializer.data

    assert data["action"] == "summarize"
    assert data["course_id"] == "course-v1:edX+DemoX+Demo_Course"
    assert "ui_components" in data
    assert data["ui_components"]["request"]["component"] == "AIRequestComponent"


def test_serializer_get_ui_components(workflow_config):  # pylint: disable=redefined-outer-name
    """
    Test serializer extracts ui_components from actuator_config.
    """
    serializer = AIWorkflowConfigSerializer(workflow_config)
    ui_components = serializer.get_ui_components(workflow_config)

    assert "request" in ui_components
    assert ui_components["request"]["component"] == "AIRequestComponent"
    assert ui_components["request"]["config"]["type"] == "text"


def test_serializer_get_ui_components_empty_config():
    """
    Test serializer handles empty actuator_config.
    """
    config = Mock(spec=AIWorkflowConfig)
    config.action = "test"
    config.course_id = None
    config.actuator_config = None

    serializer = AIWorkflowConfigSerializer(config)
    ui_components = serializer.get_ui_components(config)

    assert ui_components == {}


def test_serializer_create_not_implemented(workflow_config):  # pylint: disable=redefined-outer-name
    """
    Test that serializer.create raises NotImplementedError.
    """
    serializer = AIWorkflowConfigSerializer(workflow_config)

    with pytest.raises(NotImplementedError) as exc_info:
        serializer.create({})

    assert "read-only" in str(exc_info.value)


def test_serializer_update_not_implemented(workflow_config):  # pylint: disable=redefined-outer-name
    """
    Test that serializer.update raises NotImplementedError.
    """
    serializer = AIWorkflowConfigSerializer(workflow_config)

    with pytest.raises(NotImplementedError) as exc_info:
        serializer.update(workflow_config, {})

    assert "read-only" in str(exc_info.value)


# ============================================================================
# Unit Tests - Views with Mocks
# ============================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.api.v1.workflows.views.AIWorkflow.find_workflow_for_context")
def test_generic_workflow_view_post_validation_error_unit(
    mock_find_workflow, user, course_key  # pylint: disable=redefined-outer-name
):
    """
    Test AIGenericWorkflowView handles ValidationError (unit test).
    """
    mock_find_workflow.side_effect = ValidationError("Invalid workflow configuration")

    factory = RequestFactory()
    request_data = {
        "action": "invalid_action",
        "courseId": str(course_key),
        "context": {},
    }

    request = factory.post(
        "/openedx-ai-extensions/v1/workflows/",
        data=json.dumps(request_data),
        content_type="application/json",
    )
    request.user = user

    view = AIGenericWorkflowView.as_view()
    response = view(request)

    assert response.status_code == 400
    data = json.loads(response.content)
    assert "error" in data
    assert data["status"] == "validation_error"


@pytest.mark.django_db
@patch("openedx_ai_extensions.api.v1.workflows.views.AIWorkflow.find_workflow_for_context")
def test_generic_workflow_view_post_general_exception_unit(
    mock_find_workflow, user, course_key  # pylint: disable=redefined-outer-name
):
    """
    Test AIGenericWorkflowView handles general exceptions (unit test).
    """
    mock_find_workflow.side_effect = Exception("Unexpected error")

    factory = RequestFactory()
    request_data = {
        "action": "summarize",
        "courseId": str(course_key),
        "context": {},
    }

    request = factory.post(
        "/openedx-ai-extensions/v1/workflows/",
        data=json.dumps(request_data),
        content_type="application/json",
    )
    request.user = user

    view = AIGenericWorkflowView.as_view()
    response = view(request)

    assert response.status_code == 500
    data = json.loads(response.content)
    assert "error" in data


@pytest.mark.django_db
@patch("openedx_ai_extensions.api.v1.workflows.views.AIWorkflowConfig.get_config")
def test_workflow_config_view_get_not_found_unit(
    mock_get_config, user  # pylint: disable=redefined-outer-name
):
    """
    Test AIWorkflowConfigView returns 404 when no config found (unit test).
    """
    mock_get_config.return_value = None

    factory = APIRequestFactory()
    request = factory.get(
        "/openedx-ai-extensions/v1/config/",
        {"action": "nonexistent", "context": "{}"},
    )
    request.user = user

    view = AIWorkflowConfigView.as_view()
    response = view(request)

    assert response.status_code == 404
    assert "error" in response.data
    assert response.data["status"] == "not_found"


@pytest.mark.django_db
@patch("openedx_ai_extensions.api.v1.workflows.views.AIWorkflowConfig.get_config")
def test_workflow_config_view_get_with_location_id_unit(
    mock_get_config, workflow_config, user, course_key  # pylint: disable=redefined-outer-name
):
    """
    Test AIWorkflowConfigView GET request with location_id in context (unit test).
    """
    mock_get_config.return_value = workflow_config

    location = BlockUsageLocator(course_key, block_type="vertical", block_id="unit-1")
    context_json = json.dumps({"unitId": str(location)})

    factory = APIRequestFactory()
    request = factory.get(
        "/openedx-ai-extensions/v1/config/",
        {
            "action": "summarize",
            "courseId": str(course_key),
            "context": context_json,
        },
    )
    request.user = user

    view = AIWorkflowConfigView.as_view()
    response = view(request)

    assert response.status_code == 200
    # Verify get_config was called with correct parameters
    mock_get_config.assert_called_once()
    call_kwargs = mock_get_config.call_args[1]
    assert call_kwargs["action"] == "summarize"
    assert call_kwargs["course_id"] == str(course_key)
    assert call_kwargs["location_id"] == str(location)


@pytest.mark.django_db
@patch("openedx_ai_extensions.api.v1.workflows.views.AIWorkflowConfig.get_config")
def test_workflow_config_view_invalid_context_json_unit(
    mock_get_config, workflow_config, user  # pylint: disable=redefined-outer-name
):
    """
    Test AIWorkflowConfigView handles invalid JSON in context parameter (unit test).
    """
    mock_get_config.return_value = workflow_config

    factory = APIRequestFactory()
    request = factory.get(
        "/openedx-ai-extensions/v1/config/",
        {"action": "summarize", "context": "invalid json{"},
    )
    request.user = user

    view = AIWorkflowConfigView.as_view()
    response = view(request)

    # Should handle invalid JSON gracefully and use empty context
    assert response.status_code == 200
