AI Extensibility Framework
###########################

|Status Badge| |License Badge|

.. |Status Badge| image:: https://img.shields.io/badge/Status-Experimental-orange
   :alt: Experimental Status

.. |License Badge| image:: https://img.shields.io/badge/License-AGPL%20v3-blue
   :alt: License

**An experimental Open edX plugin for AI-powered educational workflows**

The AI Extensibility Framework is a proof-of-concept plugin that explores artificial intelligence integration in Open edX. It provides a modular, extensible architecture for building AI-powered workflows that enhance the learning experience.

.. contents::
   :local:
   :depth: 2

Overview
********

This plugin demonstrates how AI capabilities can be integrated into Open edX in a modular and extensible way, following the principle of "open for extension, closed for modification." It provides infrastructure for AI workflows while maintaining compliance with educational requirements and Open edX standards.

**Key Features (planned for V1):**

- Modular workflow-based architecture for AI processing
- Support for multiple LLM providers via LiteLLM (OpenAI, Anthropic, local models)
- Context-aware AI assistance examples integrated into the learning experience
- Observable workflows with event analytics in aspects
- Configuration-driven behavior without code changes


Current Status
**************

.. warning::
   **Experimental** - This plugin is in active development and should not be used in production environments.

This is an exploratory project developed by edunext as part of FC-111 to investigate AI extensibility patterns for Open edX. The plugin serves as a testing ground for AI integration concepts that may inform future development.

**What Works:**

- Frontend integration with Learning MFE via plugin slots
- Basic content extraction from course unit
- AI-powered content summarization


Installation
************

Prerequisites
=============

- Open edX installation (Tutor-based deployment recommended)
- Python 3.11 or higher
- Node.js 18.x or higher (for frontend development)
- API key for supported LLM provider (OpenAI, Anthropic, etc.)

Installation
============

Install the plugin in your Open edX environment using the provided tutor plugin::

    git clone git@github.com:openedx/openedx-ai-extensions.git
    pip install openedx-ai-extensions/tutor
    tutor plugins enable openedx-ai-extensions
    tutor images build openedx
    tutor images build mfe
    tutor local launch



Setting Up Development Environment
===================================

TBD when the tutor plugin PR is merged.


Code Standards
==============

- All code, comments, and documentation must be in clear, concise English
- Write descriptive commit messages using conventional commits.
- Follow the CI instructions on code quality.


Architecture Decisions
======================

Significant architectural decisions are documented in ADRs (Architectural Decision Records) located in the ``docs/decisions/`` directory.

Contributing
************

We welcome contributions! This is an experimental project exploring AI integration patterns for Open edX.

**How to Contribute:**

1. Fork the repository
2. Create a feature branch (``git checkout -b feature/your-feature``)
3. Make your changes following the code standards
4. Write or update tests as needed
5. Submit a pull request with a clear description

For questions or discussions, please use the `Open edX discussion forum <https://discuss.openedx.org>`_.


References
**********

- `Open edX Conference Paris 2025 Presentation <https://www.canva.com/design/DAGqjcS2mT4/nTHQIDIeZ89wqsBvh9GWKA/view>`_
- `Open edX Plugin Development <https://docs.openedx.org/en/latest/developers/references/plugin_reference.html>`_
- `LiteLLM Documentation <https://docs.litellm.ai/>`_
- `Architectural Decision Records (ADRs) <docs/decisions/>`_

License
*******

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0). See the LICENSE file for details.

Maintainer
**********

This repository is covered by the Open edX maintainers program and the current maintainers are listed in the `catalog-info.yaml <catalog-info.yaml>`_ file.

**Community Support:**

- Open edX Forum: https://discuss.openedx.org
- `GitHub Issues <https://github.com/openedx/openedx-ai-extensions/issues>`_

**Note:** As this is an experimental project, support is provided on a best-effort basis.