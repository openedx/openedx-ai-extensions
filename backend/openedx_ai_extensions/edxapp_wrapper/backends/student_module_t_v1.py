""" Backend abstraction for Teak and later. """
from common.djangoapps.student.models import CourseAccessRole  # pylint: disable=import-error
from opaque_keys.edx.keys import CourseKey

_COURSE_STAFF_ROLES = frozenset(["instructor"])  # higher than "staff"


def permission_is_course_staff(user, course_id):
    """ Return True if user holds a staff or instructor role for course_id. """
    try:
        course_key = CourseKey.from_string(course_id)
        return CourseAccessRole.objects.filter(
            user=user,
            course_id=course_key,
            role__in=_COURSE_STAFF_ROLES,
        ).exists()
    except Exception:  # pylint: disable=broad-exception-caught
        return False
