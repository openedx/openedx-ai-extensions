""" Track module test backend for Open edX AI Extensions."""
from unittest.mock import Mock


def get_track_module():
    """ Get mock track module for testing."""
    track_mock = Mock()
    track_mock.contexts = Mock()
    track_mock.contexts.course_context_from_course_id = Mock(return_value={})
    return track_mock
