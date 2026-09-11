Change Log
##########

..
   All enhancements and patches to openedx_ai_extensions will be documented
   in this file.  It adheres to the structure of https://keepachangelog.com/ ,
   but in reStructuredText instead of Markdown (for ease of incorporation into
   Sphinx documentation and the PyPI description).

   This project adheres to Semantic Versioning (https://semver.org/).

.. There should always be an "Unreleased" section for changes pending release.

Unreleased
**********

Added
=====

* ``AIUnitSidebarPanel``: adds an AI page, marked by the ``AutoAwesome`` sparkle
  icon, to Studio's redesigned unit sidebar. The page hosts one box per
  configured ``ui_slot_selector_id``, so further AI experiences are added with a
  workflow scope and a list entry rather than new UI code.
* ``AI_EXTENSIONS_ENABLE_UNIT_SIDEBAR_PAGE`` tutor setting, defaulting to true on
  Verawood (tutor 22) and above.
* A ``course_unit_sidebar.v1`` contribution for the legacy sidebar, which
  Verawood falls back to whenever ``ENABLE_UNIT_PAGE_NEW_DESIGN`` is off and
  which is the only sidebar on earlier releases. That slot sits inside the
  sidebar's own padded, width-capped column, so the box lines up with the
  publish and location sections instead of hanging below them. The widget id is
  unchanged, so existing ``AIWorkflowScope`` rows keep matching.

Changed
=======

* The ``course_unit_sidebar.v2`` contribution now wraps the sidebar instead of
  inserting a widget beside it, so on Verawood the box joins the sidebar's icon
  rail rather than landing next to the sidebar.

2.6.0 – 2026-09-01
**********************************************

Changed
=======

* Relaxed the ``tutor`` and ``tutor-mfe`` upper bounds from ``<22`` to ``<23`` to
  support Open edX Verawood (tutor 22 / tutor-mfe 22).

1.0.0 – 2025-12-24
**********************************************

Added
=====

* Prompt template model for reusable AI prompts across profiles
* Custom prompt support via Django admin interface
* Async task orchestrator for long-running AI workflows with Celery
* Session metadata support for task status tracking
* Documentation: comprehensive configuration guide and usage guide
* Support for provider-specific configuration overrides via "options" key
* Base models for workflows, profiles, scopes, and prompt templates

Changed
=======

* **BREAKING**: Renamed "config" key to "provider" in profile configurations
* Improved streaming response handling to eliminate double messages
* Enhanced test coverage across all major features
* Moved PromptModel to top-level models to avoid circular imports

Fixed
=====

* Validation errors now trigger on clean() instead of save()
* Faster mocked streaming for testing
* Double streaming message bug resolved
* Various QA and test coverage improvements

0.1.0 – 2025-04-11
**********************************************

Added
=====

* First release on PyPI.
