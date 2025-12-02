""" Track module wrapper for Open edX AI Extensions."""
from common.djangoapps import track  # pylint: disable=import-error


def get_track_module():
    """ Get track module."""
    return track
