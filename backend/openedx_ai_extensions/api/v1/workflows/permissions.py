"""
DRF permission classes and shared request utilities for AI Workflows API.
"""

import json
import logging

from django.core.exceptions import ValidationError
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey
from rest_framework.permissions import BasePermission

from openedx_ai_extensions.edxapp_wrapper.student_module import permission_is_course_staff

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

    course_id_raw = context.get("courseId") or context.get("course_id")
    if course_id_raw:
        try:
            CourseKey.from_string(course_id_raw)
            validated_context["course_id"] = course_id_raw
        except InvalidKeyError as e:
            raise ValidationError(f"Invalid course_id format: {course_id_raw}") from e

    location_id_raw = context.get("locationId") or context.get("location_id")
    if location_id_raw:
        try:
            UsageKey.from_string(location_id_raw)
            validated_context["location_id"] = location_id_raw
        except InvalidKeyError as e:
            raise ValidationError(f"Invalid location_id format: {location_id_raw}") from e

    ui_slot_selector_id_raw = context.get("uiSlotSelectorId") or context.get("ui_slot_selector_id")
    if ui_slot_selector_id_raw:
        validated_context["ui_slot_selector_id"] = str(ui_slot_selector_id_raw)

    return validated_context


class CourseStaffPermission(BasePermission):
    """
    Restricts access to users who are authorised to manage advanced settings
    for a course.

    * Staff and superusers are always allowed.
    * Otherwise, requires a valid ``course_id`` in the ``context`` query param
      and delegates to the configured ``STUDENT_MODULE_BACKEND`` to check
      whether the user holds a course-level staff or instructor role.
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
            return True

        try:
            context = get_context_from_request(request)
        except ValidationError as e:
            logger.debug("CourseStaffPermission denied — invalid context: %s", e)
            return False

        course_id = context.get("course_id")
        if not course_id:
            return False

        return permission_is_course_staff(user, course_id)
