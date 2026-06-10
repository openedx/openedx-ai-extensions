"""
XBlock runtime service exposing AI workflow capabilities to XBlocks.

Registered under the ``xblock.service.v1`` entry-point group in setup.py, as
proposed in docs/decisions/0011-xblock-service-entry-points.rst.
"""

from openedx_ai_extensions.xblock_service.service import AIExtensionsService

__all__ = ["AIExtensionsService"]
