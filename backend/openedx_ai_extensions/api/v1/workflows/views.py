"""
AI Workflows API Views
Refactored to use Django models and workflow orchestrators
"""

import json
import logging
import pprint
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from openedx_ai_extensions.workflows.models import AIWorkflow, AIWorkflowConfig

from .serializers import AIWorkflowConfigSerializer

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class AIGenericWorkflowView(View):
    """
    AI Workflow API endpoint
    """

    def post(self, request):
        """Handle POST request for AI assistance"""
        return self._handle_request(request, "POST")

    def get(self, request):
        """Handle GET request for AI assistance"""
        return self._handle_request(request, "GET")

    def _handle_request(self, request, method):
        """Common handler for GET and POST requests"""

        # Parse request body if present
        try:
            if request.body:
                body_data = json.loads(request.body.decode("utf-8"))
            else:
                body_data = {}
        except json.JSONDecodeError:
            return JsonResponse(
                {"error": "Invalid JSON in request body", "status": "error"}, status=400
            )

        context = body_data.get("context", {})

        # Extract obligatory workflow identification fields
        action = body_data.get("action")  # This value is set at the UI trigger
        course_id = body_data.get("courseId")
        user = request.user
        context = body_data.get("context", {})

        # TODO: Remove verbose logging
        logger.info(
            "🤖 AI WORKFLOW REQUEST:\n%s",
            pprint.pformat(
                {
                    "timestamp": datetime.now().isoformat(),
                    "method": method,
                    "action": action,
                    "user_id": user.id,
                    "username": user.username,
                    "course_id": course_id,
                    "query_params": dict(request.GET),
                    "request_body": body_data,
                },
                indent=2,
                width=100,
            ),
        )

        try:
            # Get or create workflow based on context
            workflow, created = AIWorkflow.find_workflow_for_context(
                action=action, course_id=course_id, user=user, context=context
            )

            result = workflow.execute(body_data.get("user_input", {}))

            # TODO: this should go through a serializer so that every UI actuator receives a compatible object
            request_id = body_data.get("requestId", "no-request-id")
            result.update(
                {
                    "requestId": request_id,
                    "timestamp": datetime.now().isoformat(),
                    "workflow_created": created,
                }
            )

            # Check result status and return appropriate HTTP status
            result_status = result.get("status", "success")
            if result_status == "error":
                http_status = 500  # Internal Server Error for processing failures
            elif result_status in ["validation_error", "bad_request"]:
                http_status = 400  # Bad Request for validation issues
            else:
                http_status = 200  # Success for completed/success status

            return JsonResponse(result, status=http_status)

        except ValidationError as e:
            logger.warning("🤖 WORKFLOW VALIDATION ERROR: %s", str(e))
            return JsonResponse(
                {
                    "error": str(e),
                    "status": "validation_error",
                    "timestamp": datetime.now().isoformat(),
                },
                status=400,
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("🤖 WORKFLOW ERROR: %s", str(e))
            return JsonResponse(
                {
                    "error": str(e),
                    "status": "error",
                    "timestamp": datetime.now().isoformat(),
                },
                status=500,
            )


class AIWorkflowConfigView(APIView):
    """
    API endpoint to retrieve workflow configuration
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Retrieve workflow configuration for a given action and context
        """
        # Extract query parameters
        context_str = request.query_params.get("context", "{}")
        try:
            context = json.loads(context_str)
        except (json.JSONDecodeError, TypeError):
            context = {}
        location_id = context.get("unitId")
        course_id = context.get("courseId")

        try:
            # Get workflow configuration
            config = AIWorkflowConfig.get_config(
                course_id=course_id, location_id=location_id
            )

            if not config:
                # No config found - return empty response so UI doesn't show components
                return Response(
                    {
                        "status": "no_config",
                        "timestamp": datetime.now().isoformat(),
                    },
                    status=status.HTTP_200_OK,
                )

            # Serialize the configuration
            serializer = AIWorkflowConfigSerializer(config)

            response_data = serializer.data
            response_data["timestamp"] = datetime.now().isoformat()

            return Response(response_data, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(
                {
                    "error": str(e),
                    "status": "validation_error",
                    "timestamp": datetime.now().isoformat(),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            return Response(
                {
                    "error": str(e),
                    "status": "error",
                    "timestamp": datetime.now().isoformat(),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
