""""Wrapper module to access event-routing-backends xAPI classes."""
from event_routing_backends.processors.xapi.registry import XApiTransformersRegistry
from event_routing_backends.processors.xapi.transformer import XApiTransformer


def get_xapi_transformer_registry():
    """Allow to get the XApiTransformersRegistry class from
    https://github.com/openedx/event-routing-backends/blob/master/event_routing_backends/processors/xapi/registry.py#L7

    Returns:
        XApiTransformersRegistry class.
    """
    return XApiTransformersRegistry


def get_xapi_transformer():
    """Allow to get the XApiTransformer class from
    https://github.com/openedx/event-routing-backends/blob/master/event_routing_backends/processors/xapi/transformer.py#L27

    Returns:
        XApiTransformer class.
    """
    return XApiTransformer
