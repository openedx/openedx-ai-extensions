"""
Runtime patching for the ``"ai_extensions"`` XBlock service.

``patch_runtime()`` is called once from ``OpenedxAIExtensionsConfig.ready()``.
It monkey-patches ``xblock.runtime.Runtime.service`` so that every runtime
subclass (LMS ``LmsModuleSystem``, CMS ``ModuleSystem``, modern
``XBlockRuntime``, XBlock SDK ``WorkbenchRuntime``, …) automatically
provides the ``"ai_extensions"`` service without any changes to edx-platform.

The patch is:

* **Idempotent** — calling ``patch_runtime()`` more than once is safe.
* **Non-breaking** — only the ``"ai_extensions"`` name is intercepted;
  every other service name is forwarded to the original implementation.
* **Graceful** — if building the service fails for any reason, ``None``
  is returned, honouring the ``@XBlock.wants`` contract.
"""

import logging

logger = logging.getLogger(__name__)

_PATCHED = False  # module-level guard for idempotency


def patch_runtime():
    """
    Patch ``xblock.runtime.Runtime.service`` to inject the
    ``"ai_extensions"`` service into every XBlock runtime instance.

    ``XBLOCK_MIXINS`` mixes classes into XBlock *classes*, not runtimes, so
    it cannot be used to register runtime services.  Patching the base
    ``Runtime`` class directly is the only plugin-safe approach that works
    across all Open edX runtime variants (legacy ModuleSystem, modern
    XBlockRuntime, XBlock SDK WorkbenchRuntime).

    Safe to call multiple times.
    """
    global _PATCHED  # pylint: disable=global-statement
    if _PATCHED:
        return

    try:
        import xblock.runtime as xblock_runtime  # noqa: PLC0415  pylint: disable=import-outside-toplevel,import-error

        original_service = xblock_runtime.Runtime.service

        def _patched_service(runtime_self, block, service_name):
            if service_name == "ai_extensions":
                return _build_service(runtime_self, block)
            return original_service(runtime_self, block, service_name)

        xblock_runtime.Runtime.service = _patched_service
        _PATCHED = True
        logger.info(
            "openedx_ai_extensions: patched xblock.runtime.Runtime.service "
            "to provide the 'ai_extensions' XBlock service."
        )
    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception(
            "openedx_ai_extensions: failed to patch XBlock runtime — "
            "the 'ai_extensions' service will not be available to XBlocks."
        )


def _build_service(runtime, block):
    """
    Construct an :class:`~openedx_ai_extensions.xblock_service.service.AIExtensionsXBlockService`
    from the current *runtime* and *block* context.

    Returns ``None`` on any error so the ``@XBlock.wants`` contract is upheld.
    """
    from openedx_ai_extensions.xblock_service.service import (  # noqa: PLC0415  pylint: disable=import-outside-toplevel
        AIExtensionsXBlockService,
    )

    try:
        user = _get_user(runtime)
        course_id = _get_course_id(block)
        location_id = _get_location_id(block)

        return AIExtensionsXBlockService(
            user=user,
            course_id=course_id,
            location_id=location_id,
        )
    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception(
            "openedx_ai_extensions: failed to build AIExtensionsXBlockService "
            "for block %r",
            getattr(block, "location", repr(block)),
        )
        return None


# ---------------------------------------------------------------------------
# Context extractors — work across both legacy ModuleSystem and modern
# XBlockRuntime, failing safely if neither shape is present.
# ---------------------------------------------------------------------------

def _get_user(runtime):
    """
    Return the Django ``User`` for the current request, or ``None``.

    Tries:
      1. ``runtime.user``                 — modern XBlockRuntime
      2. ``runtime.get_real_user(id)``    — legacy ModuleSystem helper
      3. ``User.objects.get(pk=...)``     — last resort DB lookup
    """
    user = getattr(runtime, "user", None)
    if user is not None:
        return user

    user_id = getattr(runtime, "user_id", None)
    if user_id is not None:
        get_real_user = getattr(runtime, "get_real_user", None)
        if callable(get_real_user):
            try:
                return get_real_user(user_id)
            except Exception:  # pylint: disable=broad-exception-caught
                pass

        try:
            from django.contrib.auth import get_user_model  # noqa: PLC0415  pylint: disable=import-outside-toplevel
            return get_user_model().objects.get(pk=user_id)
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    return None


def _get_course_id(block):
    """Return the ``CourseKey`` for *block*, or ``None``."""
    scope_ids = getattr(block, "scope_ids", None)
    if scope_ids is not None:
        usage_id = getattr(scope_ids, "usage_id", None)
        if usage_id is not None:
            try:
                return usage_id.course_key
            except AttributeError:
                pass

    return getattr(block, "course_id", None)


def _get_location_id(block):
    """Return a string usage key for *block*, or ``None``."""
    location = getattr(block, "location", None)
    if location is not None:
        return str(location)

    scope_ids = getattr(block, "scope_ids", None)
    if scope_ids is not None:
        usage_id = getattr(scope_ids, "usage_id", None)
        if usage_id is not None:
            return str(usage_id)

    return None
