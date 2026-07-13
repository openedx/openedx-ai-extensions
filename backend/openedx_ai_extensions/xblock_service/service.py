"""
The ``ai_extensions`` XBlock runtime service.

Proof of concept for entry-point based service registration (ADR-0011). The
XBlock runtime instantiates this class as
``AIExtensionsService(runtime=runtime, xblock=block)`` when a block that
declared ``@XBlock.needs("ai_extensions")`` / ``@XBlock.wants("ai_extensions")``
calls ``self.runtime.service(self, "ai_extensions")``.

This module must not import ``xblock``: the provider contract is only "a
class instantiable with ``runtime=`` and ``xblock=`` keyword arguments", so
the plugin stays decoupled from the XBlock library version shipped by the
platform.
"""

import logging

logger = logging.getLogger(__name__)


class AIExtensionsService:
    """
    Facade giving XBlocks access to AI workflow profiles.

    ``run_profile`` is currently a stub: it validates the piping from an
    XBlock through the runtime into this plugin and returns a canned payload.
    The real implementation will dispatch to the workflows engine
    (``openedx_ai_extensions.workflows``) using the same signature.
    """

    def __init__(self, **kwargs):
        self.runtime = kwargs.get("runtime")
        self.xblock = kwargs.get("xblock")

    @property
    def usage_key(self):
        """The usage key of the calling block, or None if unavailable."""
        scope_ids = getattr(self.xblock, "scope_ids", None)
        return getattr(scope_ids, "usage_id", None)

    @property
    def course_key(self):
        """The learning context (course) key of the calling block, or None."""
        return getattr(self.usage_key, "context_key", None)

    @property
    def user_id(self):
        """The runtime user id the block is bound to, or None."""
        scope_ids = getattr(self.xblock, "scope_ids", None)
        return getattr(scope_ids, "user_id", None)

    def run_profile(self, profile_id, user_input):
        """
        Run the AI workflow profile ``profile_id`` with ``user_input``.

        STUB: returns a bogus response without calling any workflow or LLM.
        """
        logger.info(
            "ai_extensions service stub called: profile=%s usage_key=%s user_id=%s",
            profile_id,
            self.usage_key,
            self.user_id,
        )
        return {
            "status": "ok",
            "stub": True,
            "profile_id": profile_id,
            "response": (
                f"[stubbed ai_extensions response for profile {profile_id!r}]"
            ),
            "context": {
                "usage_key": str(self.usage_key) if self.usage_key else None,
                "course_key": str(self.course_key) if self.course_key else None,
                "user_id": self.user_id,
            },
            "echo": user_input,
        }
