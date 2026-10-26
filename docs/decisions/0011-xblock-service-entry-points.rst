0011 XBlock Service Entry Points in the XBlock Library
#######################################################

Status
******
**Proposed** — pending Open edX community discussion and an upstream PR to
``openedx/XBlock``.  Extends the Decision section of ADR-0005.

Context
*******

ADR-0005 (*XBlock AI Service Registration*) documented four approaches for
letting an Open edX plugin expose an XBlock runtime service (such as
``"ai_extensions"``) without monkey-patching, and deferred all of them because
each required upstream changes to ``openedx-platform`` and/or
``openedx-filters``.  It recommended opening a community discussion, which now
exists:

* https://discuss.openedx.org/t/plugin-provided-xblock-runtime-services/18682

In that thread, Dave Ormsbee (a maintainer of the XBlock framework) confirmed
that *"XBlock runtime services were broadly intended to be pluggable"*
historically, asked what the consuming-XBlock API would look like, and
suggested entry points as the natural fit if XBlocks will declare the service
as a dependency.

Since ADR-0005 was written, further analysis of the runtime code uncovered
three facts that materially change the option space.

Finding 1 — Every runtime funnels into one method
=================================================

ADR-0005 assumed the extension point had to be wired into four separate places
in ``openedx-platform`` (LMS courseware, CMS preview, Studio, and the modern
``XBlockRuntime``).  In fact, all of them resolve services through the same
base method:

* The three legacy wiring sites (``lms/djangoapps/courseware/block_render.py``,
  ``cms/djangoapps/contentstore/views/preview.py``,
  ``cms/djangoapps/contentstore/utils.py:load_services_for_studio``) only
  populate the ``runtime._services`` dict.  Lookup happens in
  ``xmodule/x_module.py:ModuleStoreRuntime.service()``, which delegates
  directly to ``super().service()`` — i.e.
  ``xblock.runtime.Runtime.service()`` in the XBlock library.
* The modern ``openedx/core/djangoapps/xblock/runtime/runtime.py:
  XBlockRuntime.service()`` (and therefore ``OpenedXContentRuntime``) runs its
  hardcoded ``if/elif`` chain and then *falls back to the same base method*:
  ``return super().service(block, service_name)``.

Consequently, a single fallback added to ``Runtime.service()`` in the
``openedx/XBlock`` library is reached by **every** Open edX runtime — legacy
LMS, CMS preview, Studio, the learning-core runtime — and by the xblock-sdk
workbench, with **zero changes to openedx-platform**.

Finding 2 — The XBlock library already has the plugin machinery
===============================================================

``xblock/plugin.py`` is a generic entry-point loader already used to discover
XBlocks (``xblock.v1``) and asides (``xblock_asides.v1``).  It provides:

* per-process caching of lookups, including cached misses;
* ``AmbiguousPluginError`` when two installed packages claim the same name —
  exactly the conflict detection whose absence disqualified monkey-patching;
* a ``<group>.overrides`` companion group for *deliberate* replacement of a
  default implementation;
* ``register_temp_plugin`` for clean testing without installing packages.

Moreover, the service plugin concept is not new: the docstring of
``xblock/reference/plugins.py:Service`` states the original design goal —
*"We'd like them to be able to load through Stevedore, and have a plug-in
mechanism similar to XBlock."*  This proposal completes that stated intent.

Finding 3 — ADR-0006 (Role of XBlocks) does not apply to this placement
=======================================================================

ADR-0005 worried that ``openedx-platform`` ADR-0006 points away from expanding
the XBlock runtime's responsibilities *in the platform*.  Placing the
extension point in the XBlock framework itself asks nothing of the platform:
no new platform services, no new platform settings, no new wiring sites.  The
platform's deliberate scope reduction is untouched; the XBlock framework
merely finishes its own plugin story, in its own repository, where the service
abstraction is defined.

Decision
********

Propose to the community a fifth option, **Option 5 — an
``xblock.service.v1`` entry-point group implemented in the ``openedx/XBlock``
library**, as the primary candidate.  Option 4 (OpenEdX Filter) remains the
fallback candidate if the community prefers a hooks-based mechanism.

Mechanism
=========

A plugin offers a service by registering a provider class in its own
``setup.py``::

    entry_points={
        "xblock.service.v1": [
            "ai_extensions = openedx_ai_extensions.xblock_service:AIExtensionsService",
        ],
    }

The entry-point *name* is the service name XBlocks use with
``@XBlock.needs`` / ``@XBlock.wants`` and ``self.runtime.service(self, name)``.

``xblock.runtime.Runtime.service()`` gains a fallback (≈20 lines)::

    declaration = block.service_declaration(service_name)
    if declaration is None:
        raise NoSuchServiceError(f"Service {service_name!r} was not requested.")
    service = self._services.get(service_name)
    if service is None:
        service = self._load_service_from_entry_point(block, service_name)
    if service is None and declaration == "need":
        raise NoSuchServiceError(f"Service {service_name!r} is not available.")
    return service

where ``_load_service_from_entry_point`` resolves the class through a new
``ServiceProvider(Plugin)`` loader with ``entry_point = "xblock.service.v1"``
and instantiates it as ``provider_class(runtime=self, xblock=block)`` —
mirroring the constructor of ``xblock.reference.plugins.Service``.

Properties
==========

:Precedence: Runtime-provided services always shadow plugin-provided ones.
   The entry-point group is consulted only when the runtime has nothing for
   the requested name.  A plugin therefore cannot hijack ``user``,
   ``field-data``, ``i18n``, etc.
:Gating: Unchanged ``needs``/``wants`` semantics.  A plugin service is only
   ever handed to a block that explicitly declared it; ``wants`` blocks
   degrade gracefully to ``None`` when the providing package is absent.
:Conflicts: Two packages registering the same name raise
   ``AmbiguousPluginError`` (fail loudly, not last-write-wins).  Intentional
   replacement goes through ``xblock.service.v1.overrides``.
:Performance: ``Plugin.load_class`` caches hits *and misses* per process, so
   the steady-state cost for any service name is one dict lookup.
:Coupling: The providing package does not need to import ``xblock`` at all —
   the contract is "a class instantiable with ``runtime=…, xblock=…`` keyword
   arguments".
:Trust model: Identical to XBlocks themselves — installing a package is the
   act of trust that activates its entry points.

Comparison with the options of ADR-0005
=======================================

.. list-table::
   :header-rows: 1

   * - Criterion
     - Opt 1 monkey-patch
     - Opt 2 platform entry points
     - Opt 3 Django setting
     - Opt 4 filter
     - **Opt 5 XBlock-lib entry points**
   * - Repos changed upstream
     - none
     - openedx-platform (7 files)
     - openedx-platform (4 files)
     - openedx-platform + openedx-filters
     - **openedx/XBlock only (1 file + tests)**
   * - Runtimes covered
     - depends on import order
     - the 4 patched sites
     - the 2 patched sites
     - the patched sites
     - **all, incl. xblock-sdk, automatically**
   * - Conflict handling
     - none (silent overwrite)
     - needs custom logic
     - operator-managed dict
     - pipeline order
     - **AmbiguousPluginError + .overrides**
   * - Discoverability
     - none
     - automatic on install
     - manual operator config
     - settings config
     - **automatic on install**
   * - ADR-0006 friction
     - n/a
     - high (expands platform runtime)
     - high
     - medium
     - **none (platform untouched)**
   * - Consistency with existing patterns
     - anti-pattern
     - ~15 ``openedx.*`` groups
     - ``XBLOCK_EXTRA_MIXINS``
     - OEP-50 hooks
     - **``xblock.v1`` / ``xblock_asides.v1`` + stated intent in ``reference/plugins.py``**

Proof of concept
================

Implemented and locally tested in the two working trees (not committed):

* ``openedx/XBlock`` checkout — ``xblock/runtime.py`` (the ``ServiceProvider``
  loader and the ``Runtime.service`` fallback) and
  ``xblock/test/test_plugin_services.py`` (five tests: entry-point load,
  runtime shadowing, want→None, need→raise, undeclared→raise).
* ``openedx-ai-extensions`` — a ``xblock_service`` package registering
  ``ai_extensions`` under ``xblock.service.v1`` and returning a stubbed
  ``run_profile`` response (piping only; no LLM call).

Open questions for the community
================================

1. **Instantiation contract.**  The PoC instantiates the provider class once
   per ``service()`` call.  ``reference/plugins.py`` warns against
   over-initialization; should the base runtime memoize per
   ``(runtime, service_name)``, or is per-call instantiation with
   provider-managed caching acceptable?
2. **Operator kill-switch.**  Is install-time trust sufficient (as with
   XBlocks), or should a setting allow operators to block specific
   plugin-provided service names?
3. **Naming.**  ``xblock.service.v1`` mirrors ``xblock.v1`` /
   ``xblock_asides.v1``; confirm with maintainers.
4. **Failure isolation.**  Should a provider class that raises on import or
   instantiation degrade to ``None`` for ``wants`` blocks (log + continue), or
   propagate?

Path forward
============

1. Reply on the forum thread with the concrete API Dave asked for, the
   single-fallback finding, and the PoC (draft:
   ``0011-forum-reply-draft.md``).
2. If reception is positive, open a PR to ``openedx/XBlock`` with the
   mechanism, tests, documentation, and an ADR in that repo.
3. Once merged and released into a platform release,
   ``openedx-ai-extensions`` adds the one-line entry point and un-defers
   ADR-0005; the interim REST-based integration paths remain for older
   releases.

Consequences
************

* The upstream footprint shrinks to a single, well-tested file in the one
  repository whose maintainer has already signalled that services were meant
  to be pluggable.
* Any Open edX plugin (not just AI extensions) gains a standard, discoverable
  way to offer XBlock services; XBlocks gain a portable way to soft-depend on
  optional capabilities via ``@XBlock.wants``.
* Until the upstream change ships in a named release, the ``ai_extensions``
  service remains unavailable to XBlocks on stock installs (ADR-0005
  consequences still hold).
* ADR-0005 remains the record of the rejected/deferred options; this ADR
  records the proposal actually taken to the community.

References
**********

* ADR-0005 — ``docs/decisions/0005-xblock-ai-service-registration.rst``
* Community thread — https://discuss.openedx.org/t/plugin-provided-xblock-runtime-services/18682
* ``xblock/plugin.py`` and ``xblock/reference/plugins.py`` in
  https://github.com/openedx/XBlock
* ``xmodule/x_module.py:ModuleStoreRuntime.service`` and
  ``openedx/core/djangoapps/xblock/runtime/runtime.py:XBlockRuntime.service``
  in https://github.com/openedx/edx-platform
* openedx-platform ADR-0006 (*Role of XBlocks*)
