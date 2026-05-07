""" Backend abstraction for edx-platform student module. """
from importlib import import_module

from django.conf import settings


def permission_is_course_staff(user, course_id):
    """ Return True if user may manage advanced settings for the given course. """
    backend = import_module(settings.STUDENT_MODULE_BACKEND)
    return backend.permission_is_course_staff(user, course_id)
