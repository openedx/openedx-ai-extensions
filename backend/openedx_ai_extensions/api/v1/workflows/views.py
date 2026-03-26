"""
AI Workflows API Views
Refactored to use Django models and workflow orchestrators
"""

import json
import logging
from datetime import datetime, timezone

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse, StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from openedx_ai_extensions.decorators import handle_ai_errors
from openedx_ai_extensions.utils import is_generator
from openedx_ai_extensions.workflows.models import AIWorkflowScope

from .serializers import AIWorkflowProfileSerializer

logger = logging.getLogger(__name__)


def get_context_from_request(request):
    """
    Extract and validate context from request query parameters.

    Validates course_id and location_id formats using Open edX opaque_keys.
    Returns a dict with snake_case keys.

    Args:
        request: Django request object with query parameters

    Returns:
        dict: Context with validated course_id and location_id in snake_case

    Raises:
        ValidationError: If course_id or location_id are invalid
    """
    if hasattr(request, "GET"):
        context_str = request.GET.get("context", "{}")
    else:
        context_str = request.query_params.get("context", "{}")

    try:
        context = json.loads(context_str)
    except json.JSONDecodeError as e:
        raise ValidationError("Invalid JSON format in 'context' parameter.") from e
    validated_context = {}

    # Validate and convert courseId to course_id
    course_id_raw = context.get("courseId") or context.get("course_id")
    if course_id_raw:
        try:
            CourseKey.from_string(course_id_raw)
            validated_context["course_id"] = course_id_raw
        except InvalidKeyError as e:
            raise ValidationError(f"Invalid course_id format: {course_id_raw}") from e

    # Validate and convert locationId to location_id
    location_id_raw = context.get("locationId") or context.get("location_id")
    if location_id_raw:
        try:
            UsageKey.from_string(location_id_raw)
            validated_context["location_id"] = location_id_raw
        except InvalidKeyError as e:
            raise ValidationError(f"Invalid location_id format: {location_id_raw}") from e

    # Pass ui_slot_selector_id as-is (plain string, no special validation needed)
    ui_slot_selector_id_raw = context.get("uiSlotSelectorId") or context.get("ui_slot_selector_id")
    if ui_slot_selector_id_raw:
        validated_context["ui_slot_selector_id"] = str(ui_slot_selector_id_raw)

    return validated_context


@method_decorator(login_required, name="dispatch")
@method_decorator(handle_ai_errors, name="dispatch")
class AIGenericWorkflowView(View):
    """
    AI Workflow API endpoint
    """

    def post(self, request):
        """Common handler for GET and POST requests"""

        context = get_context_from_request(request)
        workflow_profile = AIWorkflowScope.get_profile(**context)

        request_body = {}
        if request.body:
            try:
                request_body = json.loads(request.body.decode("utf-8"))
            except json.JSONDecodeError as e:
                raise ValidationError("Invalid JSON format in request body.") from e
        action = request_body.get("action", "")
        user_input = request_body.get("user_input", {})

        result = workflow_profile.execute(
            user_input=user_input,
            action=action,
            user=request.user,
            running_context=context,
        )

        # Handle structured error responses from processors/orchestrators
        if not is_generator(result) and isinstance(result, dict) and "error" in result:
            return JsonResponse(
                {
                    "error": {
                        "code": "processor_error",
                        "message": "An error occurred while processing the AI request.",
                    },
                    "status": "error",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if is_generator(result):
            return StreamingHttpResponse(
                result,
                content_type="text/plain"
            )

        return JsonResponse(result, status=200)


class AIWorkflowProfileView(APIView):
    """
    API endpoint to retrieve workflow profile configuration
    """

    permission_classes = [IsAuthenticated]

    @method_decorator(handle_ai_errors)
    def get(self, request):
        """
        Retrieve workflow configuration for a given action and context
        """

        # Get workflow configuration profile
        context = get_context_from_request(request)
        profile = AIWorkflowScope.get_profile(**context)

        if not profile:
            # No profile found - return empty response so UI doesn't show components
            return Response(
                {
                    "status": "no_config",
                    "timestamp": datetime.now().isoformat(),
                },
                status=status.HTTP_200_OK,
            )

        serializer = AIWorkflowProfileSerializer(profile)

        response_data = serializer.data
        response_data["timestamp"] = datetime.now().isoformat()

        return Response(response_data, status=status.HTTP_200_OK)
