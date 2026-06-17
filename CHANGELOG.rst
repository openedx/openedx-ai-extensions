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

*

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
