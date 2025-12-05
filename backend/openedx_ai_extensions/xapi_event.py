"""
Utility functions for Open edX AI Extensions.
"""

from eventtracking import tracker
from opaque_keys.edx.keys import CourseKey

from openedx_ai_extensions.edxapp_wrapper.track_context_module import get_track_module


def emit_event(event_name, course_id, event_data):
    """
    Emit an xAPI event with the given name, course ID, and event data.
    """
    track = get_track_module()
    course_key = CourseKey.from_string(course_id)
    context = track.contexts.course_context_from_course_id(course_key)

    with tracker.get_tracker().context(event_name, context):
        tracker.emit(event_name, event_data)
