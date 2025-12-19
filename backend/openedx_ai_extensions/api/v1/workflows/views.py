"""
AI Workflows API Views
Refactored to use Django models and workflow orchestrators
"""

import json
import logging
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse, StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from openedx_ai_extensions.utils import is_generator
from openedx_ai_extensions.workflows.models import AIWorkflowScope

from .serializers import AIWorkflowProfileSerializer

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class AIGenericWorkflowView(View):
    """
    AI Workflow API endpoint
    """

    def post(self, request):
        """Common handler for GET and POST requests"""

        try:
            config = AIWorkflowScope.get_config(request=request)

            request_body = {}
            if request.body:
                request_body = json.loads(request.body.decode("utf-8"))
            action = request_body.get("action", "")
            user_input = request_body.get("userInput", {})

            result = config.execute(
                user_input=user_input,
                action=action,
                user=request.user,
            )

            if is_generator(result):
                return StreamingHttpResponse(
                    result,
                    content_type="text/plain"
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


class AIWorkflowProfileView(APIView):
    """
    API endpoint to retrieve workflow profile configuration
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Retrieve workflow configuration for a given action and context
        """

        try:
            # Get workflow configuration
            config = AIWorkflowScope.get_config(request=request)

            if not config:
                return Response(
                    {
                        "error": "No workflow scope configuration found for current context.",
                        "status": "not_found",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = AIWorkflowProfileSerializer(config)

            response_data = serializer.data
            response_data["timestamp"] = datetime.now().isoformat()

            return Response(response_data, status=status.HTTP_200_OK)

        except ValidationError as e:
            logger.warning("🤖 CONFIG VALIDATION ERROR: %s", str(e))
            return Response(
                {
                    "error": str(e),
                    "status": "validation_error",
                    "timestamp": datetime.now().isoformat(),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("🤖 CONFIG ERROR: %s", str(e))
            return Response(
                {
                    "error": str(e),
                    "status": "error",
                    "timestamp": datetime.now().isoformat(),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
