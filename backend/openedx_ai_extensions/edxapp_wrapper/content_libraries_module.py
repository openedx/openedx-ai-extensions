""" Backend abstraction. """
from importlib import import_module

from django.conf import settings


def get_content_libraries():
    """ Get content_libraries module. """
    backend_function = settings.CONTENT_LIBRARIES_MODULE_BACKEND
    backend = import_module(backend_function)
    return backend.get_content_libraries()
