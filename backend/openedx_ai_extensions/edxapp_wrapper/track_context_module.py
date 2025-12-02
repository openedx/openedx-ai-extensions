""" Backend abstraction. """
from importlib import import_module

from django.conf import settings


def get_track_module():
    """ Get track contexts module. """
    backend_function = settings.TRACK_MODULE_BACKEND
    backend = import_module(backend_function)
    return backend.get_track_module()
