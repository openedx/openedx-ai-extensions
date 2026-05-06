"""
DRF permission classes and shared request utilities for AI Workflows API.
"""

import json

from django.core.exceptions import ValidationError
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey
from rest_framework.permissions import BasePermission

try:
    from openedx_authz import api as authz_api
except ImportError:
    authz_api = None

_COURSE_ADVANCED_SETTINGS_ACTION = "courses.manage_advanced_settings"


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


class CourseAdvancedSettingsPermission(BasePermission):
    """
    Restricts access to users who are authorised to manage advanced settings
    for a course — roughly equivalent to the course instructor/admin role.

    This permission is intentionally written to be forward-compatible with the
    openedx-authz RBAC system introduced in Ulmo. The behaviour differs by
    platform, but the intent is the same on both:

    * **Teak and earlier** (openedx-authz not installed): falls back to
      Django's ``is_staff`` flag, which is the coarsest available gate on
      platforms that do not yet ship openedx-authz.

    * **Ulmo and later** (openedx-authz installed): enforces
      ``courses.manage_advanced_settings`` via the Casbin policy engine,
      scoped to the course identified by the ``context`` query param.
      Staff and superusers are always allowed regardless of policy.
      Requests without a valid ``course_id`` in context are denied.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if authz_api is None:
            return bool(request.user.is_staff)

        if request.user.is_staff or request.user.is_superuser:
            return True

        try:
            context = get_context_from_request(request)
        except ValidationError:
            return False

        course_id = context.get("course_id")
        if not course_id:
            return False

        try:
            return authz_api.is_user_allowed(
                request.user.username,
                _COURSE_ADVANCED_SETTINGS_ACTION,
                course_id,
            )
        except Exception:  # pylint: disable=broad-exception-caught
            return False
