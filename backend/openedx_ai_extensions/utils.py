"""
Utility functions for Open edX AI Extensions.
"""


from common.djangoapps.track import contexts  # pylint: disable=import-error
from eventtracking import tracker
from opaque_keys.edx.keys import CourseKey


def emit_event(event_name, course_id, event_data):
    """
    Emit an xAPI event with the given name, course ID, and event data.
    """
    course_key = CourseKey.from_string(course_id)
    context = contexts.course_context_from_course_id(course_key)

    with tracker.get_tracker().context(event_name, context):
        tracker.emit(event_name, event_data)
