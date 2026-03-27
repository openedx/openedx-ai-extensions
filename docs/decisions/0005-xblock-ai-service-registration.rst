0005 XBlock AI Service Registration
####################################

Status
******
**Deferred** — Upstream platform changes are out of scope for this project;
a community discussion is needed to define a standard extension mechanism.

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
changes upstream to ``openedx-platform``.

Four approaches were explored.  Options 2, 3, and 4 are technically viable but
require upstream contributions to ``openedx-platform`` or ``openedx-filters`` —
work that falls outside the scope of this plugin project and cannot be delivered
within the project's current timeline.  Option 1 is set aside on architectural
grounds regardless of timeline.  None of the four options is being pursued at
this time.


Option 1 — Monkey-patch ``Runtime.service`` (Not viable)
*********************************************************

**Scope of changes:** ``openedx-ai-extensions`` only (no openedx-platform changes).

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
  ``xblock`` or ``openedx-platform`` refactors the ``Runtime`` class.
* Multiple plugins using the same pattern risk overwriting each other's
  patches with no conflict detection.
* The pattern is difficult to discover and debug; service availability
  depends on import order and ``AppConfig.ready()`` timing.
* Monkey-patching is considered an anti-pattern in the Open edX ecosystem.


Option 2 — Upstream entry-point group ``openedx.xblock_service`` (Out of scope)
********************************************************************************

**Scope of changes:** ``openedx-ai-extensions`` + ``openedx-platform``.

This approach introduces a new ``openedx.xblock_service`` setuptools
entry-point group in ``openedx-platform``, consistent with the ~15 existing
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

(`commit 27edda4 <https://github.com/Henrrypg/openedx-platform/commit/27edda4de6130b84a0e2586e14512f79f2b01057>`_):
**openedx-platform changes**

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
  ADR in openedx-platform.

**Why deferred:**

This approach is technically sound and follows established Open edX conventions.
However, it requires an upstream contribution to ``openedx-platform`` that touches
7 files across LMS, CMS, and the modern runtime.  Modifying the platform is
outside the scope of this plugin project, and the review and acceptance timeline
for an upstream PR cannot be guaranteed within the current project schedule.
Furthermore, ``openedx-platform`` ADR-0006 (*Role of XBlocks*) points in the
opposite direction: the platform is deliberately reducing XBlock's runtime
dependencies, not expanding them.  A proposal to add a new plugin-registered
runtime service would need to contend with that architectural intent.


Option 3 — Upstream ``XBLOCK_EXTRA_SERVICES`` Django setting (Out of scope)
***************************************************************************

**Scope of changes:** ``openedx-ai-extensions`` + ``openedx-platform``.

This approach adds an ``XBLOCK_EXTRA_SERVICES`` dictionary setting to
``openedx-platform`` (analogous to the existing ``XBLOCK_EXTRA_MIXINS`` tuple).
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

(`commit 087fce3 <https://github.com/Henrrypg/openedx-platform/commit/087fce3868a6a94e51409dacf1c82e2232f322e9>`_):
**openedx-platform changes**

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

**Why deferred:**

This approach is also technically viable and is consistent with the existing
``XBLOCK_EXTRA_MIXINS`` precedent in the platform.  The same constraints apply
as in Option 2: it requires upstream changes to ``openedx-platform`` (4 files),
which is outside the scope of this project and cannot be scheduled within the
current timeline, and ADR-0006 points in the opposite direction.  Additionally,
a Django setting is less discoverable than an
entry-point group — it requires operators to configure it explicitly rather than
being discovered automatically from installed packages.


Option 4 — OpenEdX Filter at service resolution time (Out of scope)
*******************************************************************

**Scope of changes:** ``openedx-ai-extensions`` + ``openedx-filters`` + ``openedx-platform``.

This approach uses the OpenEdX Filters framework (OEP-50) to allow plugins to
intercept the service resolution call.  A new filter —
``org.openedx.learning.xblock.service.requested.v1`` — would be defined in the
``openedx-filters`` library and called inside ``XBlockRuntime.service()`` (and
the legacy runtime equivalent) before the hardcoded ``if/elif`` chain is
reached.  A plugin implements a pipeline step that checks the requested service
name and returns its service object if it matches.

**openedx-ai-extensions changes:**

* ``xblock_service/filters.py`` — implements the pipeline step:

  .. code-block:: python

      from openedx_filters.tooling import OpenEdxPublicFilter

      class AIExtensionsServiceStep(PipelineStep):
          def run_filter(self, block, service_name, service):
              if service_name == "ai_extensions":
                  return {"service": AIExtensionsXBlockService(block)}
              return {"service": service}

* ``settings/common.py`` — registers the step via ``OPEN_EDX_FILTERS_CONFIG``.

**openedx-filters changes:**

* Define ``XBlockServiceRequested`` filter class with the
  ``org.openedx.learning.xblock.service.requested.v1`` event type.

**openedx-platform changes:**

* ``openedx/core/djangoapps/xblock/runtime/runtime.py`` — add the filter call
  in ``XBlockRuntime.service()`` before the existing ``if/elif`` chain.
* Legacy runtime — same call in the equivalent service-resolution path.

**Why deferred:**

This is the approach the ``openedx-ai-extensions`` team considers most
idiomatic given the existing Open edX ecosystem.  We are confident it would
work: the OpenEdX Filters framework is designed precisely for this kind of
plugin-provided interception, and our team has extensive experience with it.
The filter call site is a small, well-contained change to ``openedx-platform``,
and the filter definition in ``openedx-filters`` is straightforward.

The reason it was not implemented is the same as for Options 2 and 3: it
requires upstream contributions that are outside the scope of this project and
cannot be scheduled within the current timeline.  It is documented here because
it represents a strong candidate for the community discussion described in the
Decision section below.


Decision
********

**No option is being implemented at this time.**

Option 1 (monkey-patching) is set aside regardless of timeline: it is an
anti-pattern in the Open edX ecosystem, fragile across upgrades, and
incompatible with multiple plugins coexisting.

Options 2, 3, and 4 are technically sound but are **out of scope** for this
project.  Modifying ``openedx-platform`` or ``openedx-filters`` falls outside
the responsibilities of a standalone pip-installable plugin, and the upstream
review and acceptance cycle cannot be accommodated within the project's current
schedule.

It is also worth noting that ``openedx-platform`` ADR-0006 (*Role of XBlocks*)
establishes a clear architectural direction: XBlocks are being scoped down, not
expanded.  Higher-level concerns such as grading, scheduling, and navigation are
moving to dedicated platform applications with their own APIs, deliberately
decoupled from the XBlock runtime.  Introducing a new plugin-provided runtime
service would run counter to that intent and would be difficult to justify to
the upstream community without strong motivation.

**The recommended path forward is to open a discussion with the Open edX
community** — through the forums, an OEP, or a working-group proposal — to
define a standard, officially supported mechanism by which plugins can
contribute XBlock runtime services.  Of the options explored, Option 4
(OpenEdX Filter) is the team's preferred candidate for that conversation: it
is the most idiomatic approach given the existing hooks framework, requires the
smallest upstream footprint, and does not introduce a new convention.  Options 2
and 3 are complementary technical proposals that could inform the same
discussion.  A community-backed decision would benefit all plugins that face
this need, not just ``openedx-ai-extensions``.


Consequences
************

* The ``"ai_extensions"`` XBlock service is **not available** to XBlocks for
  the duration of the current project.
* XBlocks that need AI capabilities must use alternative integration paths
  (e.g. direct Django imports or REST API calls) in the interim, following
  the pattern sanctioned by ``openedx-platform`` ADR-0006.
* The ``openedx-ai-extensions`` team will initiate a community discussion to
  establish an official extension point.  The research captured in this ADR —
  particularly Option 4 (OpenEdX Filter), with Options 2 and 3 as complementary
  proposals — provides concrete technical starting points to anchor that
  conversation.


References
**********

* XBlock services documentation — https://docs.openedx.org/projects/xblock/en/latest/
* Open edX plugin entry points — ``setup.py`` in openedx-platform
* openedx-platform ADR-0006 (Role of XBlocks) — ``docs/decisions/0006-role-of-xblocks.rst`` in openedx-platform
* Option 1 (monkey-patch) — `openedx-ai-extensions commit 0152bf6 <https://github.com/openedx/openedx-ai-extensions/commit/0152bf6d02cc318085d4734b2af468e7f22a4194>`_
* Option 2 (entry points) — `openedx-ai-extensions commit c838f7c <https://github.com/openedx/openedx-ai-extensions/commit/c838f7c494f2784e003d6a66ee23c2f644d7416a>`_
  and `edx-platform commit 27edda4 <https://github.com/Henrrypg/openedx-platform/commit/27edda4de6130b84a0e2586e14512f79f2b01057>`_
* Option 3 (setting) — `openedx-ai-extensions commit 9823902 <https://github.com/openedx/openedx-ai-extensions/commit/9823902af0df3ad8e249450580a46796681bfc01>`_
  and `edx-platform commit 087fce3 <https://github.com/Henrrypg/openedx-platform/commit/087fce3868a6a94e51409dacf1c82e2232f322e9>`_
* OpenEdX Filters framework (OEP-50) — https://github.com/openedx/openedx-filters
* Community discussion — https://discuss.openedx.org/t/plugin-provided-xblock-runtime-services/18682
