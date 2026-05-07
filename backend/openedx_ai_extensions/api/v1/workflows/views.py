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
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from openedx_ai_extensions.api.v1.workflows.permissions import (
    CourseStaffPermission,
    get_context_from_request,
)
from openedx_ai_extensions.decorators import handle_ai_errors
from openedx_ai_extensions.models import PromptTemplate
from openedx_ai_extensions.utils import is_generator
from openedx_ai_extensions.workflows.models import AIWorkflowScope

from .serializers import (
    AIWorkflowProfileListSerializer,
    AIWorkflowProfileSerializer,
    PromptTemplateSerializer,
    PromptTemplateUpdateSerializer,
)

logger = logging.getLogger(__name__)


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


class AIWorkflowProfilesListView(APIView):
    """
    API endpoint to list all AI Workflow Profiles matching a given context.

    Returns every distinct AIWorkflowProfile reachable for the requested
    course_id / location_id / ui_slot_selector_id / service_variant combination.
    Effective configurations are included with all sensitive values redacted.

    When no ``uiSlotSelectorId`` is provided, profiles for all slots are returned
    — the intended call pattern for the Studio settings panel.
    """

    permission_classes = [CourseStaffPermission]

    def get(self, request):
        """
        List workflow profiles for the given context.

        Accepts the same ``context`` JSON query param as ``profile/``, with optional
        ``courseId``, ``locationId``, ``uiSlotSelectorId``, and ``serviceVariant``
        keys. When ``serviceVariant`` is omitted, profiles for all service variants
        are returned.

        Returns:
            200: {"profiles": [...], "count": N, "timestamp": "..."}
            400: Validation error (malformed course or location key)
            500: Unexpected server error
        """
        try:
            context = get_context_from_request(request)

            # service_variant is specific to this endpoint and is read directly
            # from the raw context rather than through get_context_from_request.
            raw_context = json.loads(request.query_params.get("context", "{}"))
            service_variant = (
                raw_context.get("serviceVariant") or raw_context.get("service_variant") or None
            )

            profiles = AIWorkflowScope.list_profiles_for_context(
                **context, service_variant=service_variant
            )
            serializer = AIWorkflowProfileListSerializer(profiles, many=True)

            return Response(
                {
                    "profiles": serializer.data,
                    "count": len(profiles),
                    "timestamp": datetime.now().isoformat(),
                },
                status=status.HTTP_200_OK,
            )

        except ValidationError as e:
            logger.warning("🤖 PROFILES LIST VALIDATION ERROR: %s", str(e))
            return Response(
                {
                    "error": str(e),
                    "status": "validation_error",
                    "timestamp": datetime.now().isoformat(),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.exception("🤖 PROFILES LIST ERROR")
            return Response(
                {
                    "error": str(e),
                    "status": "error",
                    "timestamp": datetime.now().isoformat(),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PromptTemplateDetailView(APIView):
    """
    API endpoint to retrieve a single PromptTemplate by slug or UUID.

    Accepts either form as the ``identifier`` URL segment:
    ``GET /v1/prompts/<slug>/``
    ``GET /v1/prompts/<uuid>/``
    """

    permission_classes = [CourseStaffPermission]

    def _get_template(self, identifier):
        """
        Look up a PromptTemplate by slug first, then by UUID.

        Args:
            identifier (str): Slug or UUID string.

        Returns:
            PromptTemplate or None
        """
        try:
            return PromptTemplate.objects.get(slug=identifier)
        except PromptTemplate.DoesNotExist:
            pass
        try:
            return PromptTemplate.objects.get(id=identifier)
        except (PromptTemplate.DoesNotExist, Exception):  # pylint: disable=broad-exception-caught
            return None

    def get(self, request, identifier):
        """
        Retrieve a prompt template by slug or UUID.

        Args:
            identifier (str): Slug or UUID of the prompt template.

        Returns:
            200: Serialized prompt template.
            404: No template found for the given identifier.
        """
        template = self._get_template(identifier)
        if template is None:
            return Response(
                {"error": f"Prompt template '{identifier}' not found.", "status": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(PromptTemplateSerializer(template).data, status=status.HTTP_200_OK)

    def patch(self, request, identifier):
        """
        Update the body of a prompt template.

        Only the ``body`` field may be changed. Any other field in the request
        payload is rejected with HTTP 400.

        Args:
            identifier (str): Slug or UUID of the prompt template.

        Returns:
            200: Updated serialized prompt template.
            400: Payload contains fields other than ``body``, or body is blank.
            404: No template found for the given identifier.
        """
        template = self._get_template(identifier)
        if template is None:
            return Response(
                {"error": f"Prompt template '{identifier}' not found.", "status": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PromptTemplateUpdateSerializer(template, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(PromptTemplateSerializer(template).data, status=status.HTTP_200_OK)
