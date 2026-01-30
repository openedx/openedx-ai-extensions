.. _qs config:

Configuration Guide
###################

This guide walks you through the essential configuration steps to get AI workflows running in your Open edX installation.

.. note::

  These instructions are written for site operators. You'll need access to your site backend; it is recommend to use `Tutor <https://docs.tutor.edly.io/>`_.

.. contents::
 :local:
 :depth: 1

Prerequisites
*************

Before configuring the plugin, ensure you have:

- Completed the :ref:`plugin installation <readme>`
- Access to your Tutor configuration files (``config.yml``)
- An API key from a supported LLM provider (OpenAI, Anthropic, or a local model server)
- Django admin access to your Open edX instance

Core Concepts
*************

The plugin uses three main configuration concepts:

**Provider**
   Handles authentication and model routing. Defines which AI service to use and how to connect to it.

**Scope**
   Defines the **where** - the context in which an AI workflow will be visible and usable (LMS/CMS, specific course, location).

**Profile**
   Defines the **what** - what the AI will be instructed to do and which information it will have access to.

Configuring Providers
*********************

Using Tutor Configuration (Recommended)
========================================

The recommended approach for production environments is to configure providers in your Tutor ``config.yml`` file. This keeps API keys secure and separate from your workflow configurations.


Add the following to your ``config.yml``:

.. code-block:: yaml

   AI_EXTENSIONS:
     provider:
       API_KEY: "sk-proj-your-api-key"
       MODEL: "provider/your-model"

Depending on your selected provider, the configuration should look like this:

.. code-block:: yaml

   AI_EXTENSIONS:
     openai:
       API_KEY: "sk-proj-your-api-key"
       MODEL: "openai/gpt-4o-mini"
     anthropic:
       API_KEY: "sk-ant-api-abc123"
       MODEL: "anthropic/claude-3-haiku-20240307"
     ollama:
       API_BASE: "http://ollama:11434"
       MODEL: "ollama/llama3.2:1b"

**Configuration Parameters:**

- ``API_KEY``: Your authentication key for the provider
- ``MODEL``: The model identifier in format ``provider/model-name``
- ``API_BASE``: (Optional) Custom API endpoint for self-hosted solutions
- Additional LiteLLM parameters can be passed as needed (see `LiteLLM documentation <https://docs.litellm.ai/>`_)

Then enable the plugin:

.. code-block:: yaml

   PLUGINS:
     - openedx-ai-extensions

After updating your configuration:

.. code-block:: bash

   tutor config save
   tutor local launch

If you haven't built the images yet, run these commands first:

.. code-block:: bash

   tutor images build openedx
   tutor images build mfe


Using the Provider in Workflow Profiles
----------------------------------------

Reference your configured provider in workflow profiles using a patch. The ``default`` provider is the first one in the list. If you have only one provider, you can skip this.

.. code-block:: json

   {
     "processor_config": {
       "LLMProcessor": {
         "provider": "openai"
       }
     }
   }

The provider name must match one of the keys defined in ``AI_EXTENSIONS``.

Direct Configuration in Profiles (Testing Only)
================================================

For testing and development, you can configure the model and API key directly in the workflow profile. This approach is convenient for quick tests but is not recommended for production.

.. warning::
   **Security Risk**: API keys stored in profiles are visible to users with Django admin access. Use Tutor configuration for production environments.

Add the following to your profile configuration:

.. code-block:: json

   {
     "processor_config": {
       "LLMProcessor": {
         "options": {
           "MODEL": "openai/gpt-4o-mini",
           "API_KEY": "sk-proj-put-your-api-key-here"
         }
       }
     }
   }

Example Profile
---------------

The plugin includes an example profile at ``backend/openedx_ai_extensions/workflows/profiles/base/standalone_config.json`` that demonstrates this approach. You can access this example in the Django admin interface at ``/admin/``.

Self-Hosted Models
******************

For organizations that prefer to run their own models, the plugin has been tested with CPU-based Ollama deployments. However, for production workloads, we recommend using a proper LLM inference engine.

Tested Solutions
================

- **Ollama** (CPU, development/testing): See `deployment guide <https://gist.github.com/felipemontoya/509495d3fbaa696fa2b684880a8388da>`_
- **vLLM** (GPU, production recommended): `vLLM Project <https://github.com/vllm-project/vllm>`_

Ollama Configuration Example
-----------------------------

.. code-block:: yaml

   AI_EXTENSIONS:
     local-llama:
       API_BASE: "http://ollama:11434"
       MODEL: "ollama/llama3.2:1b"

vLLM Configuration Example
--------------------------

TBD

Troubleshooting
***************

Provider Connection Issues
==========================

If you encounter connection errors:

- Verify API keys are correct and have proper permissions
- For self-hosted solutions, ensure the API_BASE URL is accessible from the Open edX containers
- Check network connectivity and firewall rules

Profile Not Appearing
=====================

If configured profiles don't appear in the UI:

- Verify the scope configuration matches your current context
- Check that the profile is active in Django admin
- Ensure the provider referenced in the profile exists in your configuration

For additional support, visit the `GitHub Issues <https://github.com/openedx/openedx-ai-extensions/issues>`_ page.

.. seealso::

  :ref:`qs-usage`

  :ref:`local MCP`

  :ref:`MCP Integration`