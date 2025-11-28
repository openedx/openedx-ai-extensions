""" Backend abstraction. """
from openedx.core.djangoapps import content_libraries  # pylint: disable=import-error


def get_content_libraries():
    """ Get content_libraries module. """
    return content_libraries
