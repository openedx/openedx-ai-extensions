0005 XBlock AI Service Registration
####################################

Status
******
**Rejected** — All three options explored were rejected.

Context
*******

The ``openedx-ai-extensions`` plugin needs to expose an ``"ai_extensions"``
XBlock service so that any XBlock can call LLM capabilities through the
standard ``self.runtime.service(self, "ai_extensions")`` mechanism, without
importing Django models or plugin internals directly.

The XBlock runtime in Open edX wires services in several places:

1. **LMS learner view** —
   ``lms/djangoapps/courseware/block_render.py`` builds a dict of ~15
   services and assigns them to ``runtime._services``.

2. **CMS preview** —
   ``cms/djangoapps/contentstore/views/preview.py:_prepare_runtime_for_preview()``
   builds a similar dict of ~10 services.

3. **CMS Studio view** —
   ``cms/djangoapps/contentstore/utils.py:load_services_for_studio()``
   builds a dict of ~7 services.

4. **Modern XBlockRuntime** —
   ``openedx/core/djangoapps/xblock/runtime/runtime.py`` uses a hardcoded
   ``if/elif`` chain for ~12 services.

There is **no plugin-friendly extension point** for external Open edX plugins
to register new XBlock services.  This forces plugins that need to expose
functionality to XBlocks to resort to monkey-patching or to contribute
changes upstream to ``edx-platform``.

Three approaches were explored and ultimately all rejected.


Option 1 — Monkey-patch ``Runtime.service`` (Rejected)
******************************************************

**Scope of changes:** ``openedx-ai-extensions`` only (no edx-platform changes).

This approach patches ``xblock.runtime.Runtime.service`` from the plugin's
``AppConfig.ready()`` method.  A wrapper function intercepts requests for the
``"ai_extensions"`` service name and delegates everything else to the original
implementation.

**openedx-ai-extensions changes**
(`commit 0152bf6 <https://github.com/openedx/openedx-ai-extensions/commit/0152bf6d02cc318085d4734b2af468e7f22a4194>`_):

* ``apps.py`` — calls ``patch_runtime()`` in ``ready()``.
* ``xblock_service/mixin.py`` — contains the ``patch_runtime()`` function that
  replaces ``xblock.runtime.Runtime.service`` with a wrapped version.
* ``xblock_service/service.py`` — the ``AIExtensionsXBlockService`` façade.
* ``xblock_service/__init__.py`` — module docstring and lazy imports.

Key code (``mixin.py``):

.. code-block:: python

    import xblock.runtime as xblock_runtime

    original_service = xblock_runtime.Runtime.service

    def _patched_service(runtime_self, block, service_name):
        if service_name == "ai_extensions":
            return _build_service(runtime_self, block)
        return original_service(runtime_self, block, service_name)

    xblock_runtime.Runtime.service = _patched_service

**Why rejected:**

* Monkey-patching is inherently fragile — it can break silently when
  ``xblock`` or ``edx-platform`` refactors the ``Runtime`` class.
* Multiple plugins using the same pattern risk overwriting each other's
  patches with no conflict detection.
* The pattern is difficult to discover and debug; service availability
  depends on import order and ``AppConfig.ready()`` timing.
* Monkey-patching is considered an anti-pattern in the Open edX ecosystem.


Option 2 — Upstream entry-point group ``openedx.xblock_service`` (Rejected)
****************************************************************************

**Scope of changes:** ``openedx-ai-extensions`` + ``edx-platform``.

This approach introduces a new ``openedx.xblock_service`` setuptools
entry-point group in ``edx-platform``, consistent with the ~15 existing
``openedx.*`` entry-point groups (e.g. ``openedx.course_tab``,
``openedx.dynamic_partition_generator``).

**openedx-ai-extensions changes**
(`commit c838f7c <https://github.com/openedx/openedx-ai-extensions/commit/c838f7c494f2784e003d6a66ee23c2f644d7416a>`_):

* ``xblock_service/__init__.py`` — adds ``ai_extensions_factory(runtime, block)``
  as the entry-point callable.
* ``xblock_service/mixin.py`` — contains ``_build_service(runtime, block)`` and
  context extractors (``_get_user``, ``_get_course_id``, ``_get_location_id``);
  no monkey-patching.
* ``setup.py`` — registers the entry point:

  .. code-block:: python

      "openedx.xblock_service": [
          "ai_extensions = openedx_ai_extensions.xblock_service:ai_extensions_factory",
      ],

**edx-platform changes**
(`commit 27edda4 <https://github.com/Henrrypg/openedx-platform/commit/27edda4de6130b84a0e2586e14512f79f2b01057>`_):

* ``openedx/core/djangoapps/xblock/runtime/plugin_services.py`` (new) —
  ``_discover_service_factories()`` scans the ``openedx.xblock_service``
  entry-point group (result is ``lru_cache``-d) and ``get_plugin_service()``
  invokes the factory.
* ``openedx/core/djangoapps/xblock/runtime/runtime.py`` — calls
  ``get_plugin_service()`` in ``XBlockRuntime.service()`` before falling back
  to the base implementation.
* ``lms/djangoapps/courseware/block_render.py`` — merges plugin-registered
  services into the legacy runtime's ``_services`` dict via ``partial``.
* ``cms/djangoapps/contentstore/views/preview.py`` — same merge for CMS
  preview runtime.
* ``cms/djangoapps/contentstore/utils.py`` — same merge for Studio runtime.
* ``setup.py`` — declares the new ``openedx.xblock_service`` entry-point group.
* ``docs/decisions/0024-plugin-xblock-service-registration.rst`` — accompanying
  ADR in edx-platform.

**Why rejected:**

* Requires an upstream contribution to ``edx-platform`` that touches 7 files
  across LMS, CMS, and the modern runtime — a large surface area that increases
  review difficulty and merge risk.
* The duplicated service-injection code in three legacy runtime init sites
  (``block_render.py``, ``preview.py``, ``utils.py``) adds maintenance burden.
* Acceptance timeline for upstream PRs is uncertain and blocks plugin
  functionality in the meantime.


Option 3 — Upstream ``XBLOCK_EXTRA_SERVICES`` Django setting (Rejected)
***********************************************************************

**Scope of changes:** ``openedx-ai-extensions`` + ``edx-platform``.

This approach adds an ``XBLOCK_EXTRA_SERVICES`` dictionary setting to
``edx-platform`` (analogous to the existing ``XBLOCK_EXTRA_MIXINS`` tuple).
Plugins register their service factory as a dotted Python path in the
setting, and the runtime resolves it via ``django.utils.module_loading.import_string``.

**openedx-ai-extensions changes**
(`commit 9823902 <https://github.com/openedx/openedx-ai-extensions/commit/9823902af0df3ad8e249450580a46796681bfc01>`_):

* ``apps.py`` — removes the ``patch_runtime()`` call from ``ready()``.
* ``settings/common.py`` — injects the service factory into the setting:

  .. code-block:: python

      if not hasattr(settings, "XBLOCK_EXTRA_SERVICES"):
          settings.XBLOCK_EXTRA_SERVICES = {}
      settings.XBLOCK_EXTRA_SERVICES.setdefault(
          "ai_extensions",
          "openedx_ai_extensions.xblock_service.mixin.ai_extensions_service_factory",
      )

* ``xblock_service/mixin.py`` — replaces the monkey-patch with a plain factory
  callable ``ai_extensions_service_factory(block, runtime)`` that builds the
  service from the runtime/block context.
* ``xblock_service/__init__.py`` — updated docstring to reference the setting.

**edx-platform changes**
(`commit 087fce3 <https://github.com/Henrrypg/openedx-platform/commit/087fce3868a6a94e51409dacf1c82e2232f322e9>`_):

* ``lms/envs/common.py`` and ``cms/envs/common.py`` — declare
  ``XBLOCK_EXTRA_SERVICES = {}`` with setting documentation.
* ``openedx/core/djangoapps/xblock/runtime/runtime.py`` — checks
  ``settings.XBLOCK_EXTRA_SERVICES`` in ``XBlockRuntime.service()`` before the
  declaration check; imports the factory via ``import_string`` and calls it
  with ``block`` and ``runtime``.
* ``xmodule/x_module.py`` — same check in ``DescriptorSystem.service()``
  (legacy runtime).

Key code (``runtime.py``):

.. code-block:: python

    extra_services = getattr(settings, 'XBLOCK_EXTRA_SERVICES', {})
    if service_name in extra_services:
        factory = import_string(extra_services[service_name])
        return factory(block=block, runtime=self)

**Why rejected:**

* Still requires an upstream contribution to ``edx-platform`` (4 files changed).
* Using a Django setting for service registration is less discoverable than
  entry points — operators must know to configure the setting, and there is no
  automatic discovery from installed packages.
* The ``import_string`` call on every ``service()`` invocation adds overhead
  (no caching) and defers import errors to runtime rather than startup.
* Acceptance timeline for upstream PRs remains uncertain.


Decision
********

All three options are **rejected**.  None of the approaches provides an
acceptable balance between self-containment, code quality, and upstream
acceptance risk.

A future solution should ideally:

* Not require monkey-patching any core class.
* Leverage the existing Open edX plugin entry-point conventions.
* Minimise the edx-platform change surface to improve upstream acceptance
  likelihood.
* Provide automatic discovery from installed packages without operator
  configuration.


Consequences
************

* The ``"ai_extensions"`` XBlock service is **not available** to XBlocks until
  a satisfactory registration mechanism is established.
* XBlocks that need AI capabilities must use alternative integration paths
  (e.g. REST API calls) in the interim.
* Future work should revisit upstream proposals once the Open edX community
  establishes a standard pattern for plugin-provided XBlock services.


References
**********

* XBlock services documentation — https://docs.openedx.org/projects/xblock/en/latest/
* Open edX plugin entry points — ``setup.py`` in edx-platform
* Option 1 (monkey-patch) — `openedx-ai-extensions commit 0152bf6 <https://github.com/openedx/openedx-ai-extensions/commit/0152bf6d02cc318085d4734b2af468e7f22a4194>`_
* Option 2 (entry points) — `openedx-ai-extensions commit c838f7c <https://github.com/openedx/openedx-ai-extensions/commit/c838f7c494f2784e003d6a66ee23c2f644d7416a>`_
  and `edx-platform commit 27edda4 <https://github.com/Henrrypg/openedx-platform/commit/27edda4de6130b84a0e2586e14512f79f2b01057>`_
* Option 3 (setting) — `openedx-ai-extensions commit 9823902 <https://github.com/openedx/openedx-ai-extensions/commit/9823902af0df3ad8e249450580a46796681bfc01>`_
  and `edx-platform commit 087fce3 <https://github.com/Henrrypg/openedx-platform/commit/087fce3868a6a94e51409dacf1c82e2232f322e9>`_
