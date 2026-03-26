"""
Decorators for Open edX AI Extensions.
"""

import logging
from datetime import datetime, timezone
from functools import wraps

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from litellm.exceptions import (
    APIConnectionError,
    AuthenticationError,
    ContextWindowExceededError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)
from rest_framework import status

logger = logging.getLogger(__name__)

# Mapping of exception types to error codes, messages, and HTTP status codes.
# This can be moved to Django settings later for even greater extensibility.
EXCEPTION_MAP = {
    AuthenticationError: {
        "code": "invalid_api_key",
        "message": "The AI service is currently unavailable due to an authentication error.",
        "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
    },
    RateLimitError: {
        "code": "rate_limit_exceeded",
        "message": "The AI service is currently busy. Please try again later.",
        "status": status.HTTP_429_TOO_MANY_REQUESTS,
    },
    ContextWindowExceededError: {
        "code": "context_window_exceeded",
        "message": "The request is too long for the AI service to process.",
        "status": status.HTTP_400_BAD_REQUEST,
    },
    (APIConnectionError, ServiceUnavailableError, Timeout): {
        "code": "service_unavailable",
        "message": "The AI service is currently unavailable. Please try again later.",
        "status": status.HTTP_503_SERVICE_UNAVAILABLE,
    },
    ValidationError: {
        "code": "validation_error",
        "message": "The provided input or configuration is invalid.",
        "status": status.HTTP_400_BAD_REQUEST,
    },
}


def handle_ai_errors(func):
    """
    Decorate Django/DRF views to catch AI-related and general exceptions.

    Returns a standardized JSON error contract.
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except Exception as e:  # pylint: disable=broad-exception-caught
            # 1. Log the exact error with stack trace for backend debugging
            logger.error("AI Workflow Failure: %s", str(e), exc_info=True)

            # 2. Find the mapping for this exception
            error_config = None
            for exc_type, config in EXCEPTION_MAP.items():
                if isinstance(e, exc_type):
                    error_config = config
                    break

            # 3. Fallback for unmapped exceptions
            if not error_config:
                error_config = {
                    "code": "internal_error",
                    "message": "An unexpected error occurred. Please try again later.",
                    "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                }

            # 4. Return the standardized JSON contract
            return JsonResponse(
                {
                    "error": {
                        "code": error_config["code"],
                        "message": list(e.messages) if isinstance(e, ValidationError) else error_config["message"],
                    },
                    "status": "error",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                status=error_config["status"],
            )
    return wrapper
