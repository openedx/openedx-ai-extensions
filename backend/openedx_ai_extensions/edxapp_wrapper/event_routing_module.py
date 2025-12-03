"""
Wrapper for event routing backends module.

This module dynamically imports the event routing backend based on Django settings,
allowing for flexible backend selection without direct coupling.
"""
import importlib

from django.conf import settings


def get_event_routing_backend():
    """
    Import and return the configured event routing backend module.

    The backend module path is specified in settings.EVENT_ROUTING_BACKEND.

    Returns:
        module: The imported event routing backend module
    """
    backend_path = settings.EVENT_ROUTING_BACKEND
    return importlib.import_module(backend_path)


# Import registry and transformer from the configured backend
backend_module = get_event_routing_backend()

XApiTransformersRegistry = backend_module.get_xapi_transformer_registry()
XApiTransformer = backend_module.get_xapi_transformer()
