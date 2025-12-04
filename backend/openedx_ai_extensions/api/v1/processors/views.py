"""
Processor API Views
Provides direct access to processor methods without workflow orchestration
"""

import json
import logging
from datetime import datetime

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from openedx_ai_extensions.processors import OpenEdXProcessor

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class OpenEdXProcessorView(View):
    """
    API endpoint for OpenEdXProcessor
    Allows calling processor functions directly via API (unauthenticated)
    """

    def post(self, request):
        """Handle POST request for processor function execution"""
        try:
            # Parse request body
            if request.body:
                body_data = json.loads(request.body.decode("utf-8"))
            else:
                body_data = {}
        except json.JSONDecodeError:
            return JsonResponse(
                {"error": "Invalid JSON in request body", "status": "error"},
                status=400
            )

        # Extract function name and context
        function_name = body_data.get("function")
        context = body_data.get("context", {})
        processor_config = body_data.get("processor_config", {})

        # Validate function name
        if not function_name:
            return JsonResponse(
                {
                    "error": "Missing required parameter: 'function'",
                    "status": "validation_error",
                    "timestamp": datetime.now().isoformat(),
                },
                status=400
            )

        # Initialize processor with config
        config = {
            "OpenEdXProcessor": processor_config
        }
        processor = OpenEdXProcessor(processor_config=config)

        # Verify function exists
        if not hasattr(processor, function_name):
            return JsonResponse(
                {
                    "error": f"Function '{function_name}' not found in OpenEdXProcessor",
                    "status": "validation_error",
                    "available_functions": [
                        "no_context",
                        "get_context_locators",
                        "get_unit_content"
                    ],
                    "timestamp": datetime.now().isoformat(),
                },
                status=400
            )

        # Execute the function
        try:
            function = getattr(processor, function_name)
            result = function(context)

            # Build response
            response_data = {
                "result": result,
                "status": "success" if "error" not in result else "error",
                "function": function_name,
                "timestamp": datetime.now().isoformat(),
            }

            # Determine HTTP status code based on result
            http_status = 500 if "error" in result else 200

            # Get username if authenticated, otherwise use "anonymous"
            username = getattr(request.user, 'username', 'anonymous') if hasattr(request, 'user') else 'anonymous'

            logger.info(
                "🤖 PROCESSOR EXECUTION:\n"
                "  Function: %s\n"
                "  Status: %s\n"
                "  User: %s",
                function_name,
                response_data["status"],
                username
            )

            return JsonResponse(response_data, status=http_status)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("🤖 PROCESSOR ERROR: %s", str(e))
            return JsonResponse(
                {
                    "error": str(e),
                    "status": "error",
                    "function": function_name,
                    "timestamp": datetime.now().isoformat(),
                },
                status=500
            )

    def get(self, request):
        """Handle GET request - returns available processor functions"""
        return JsonResponse({
            "processor": "OpenEdXProcessor",
            "available_functions": [
                {
                    "name": "no_context",
                    "description": "Returns a message when no context is provided"
                },
                {
                    "name": "get_context_locators",
                    "description": "Extracts and returns unit_id from context"
                },
                {
                    "name": "get_unit_content",
                    "description": "Extracts full unit content from Open edX modulestore"
                }
            ],
            "usage": {
                "method": "POST",
                "body": {
                    "function": "function_name",
                    "context": {
                        "extra_context": {
                            "unitId": "block-v1:..."
                        }
                    },
                    "processor_config": {
                        "char_limit": 1000  # optional
                    }
                }
            },
            "timestamp": datetime.now().isoformat()
        })
