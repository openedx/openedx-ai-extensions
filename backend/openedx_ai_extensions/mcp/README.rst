Model Context Protocol (MCP) - Proof of Concept
================================================

This directory contains a **proof of concept (MVP)** demonstrating how Model Context Protocol (MCP) works. This is **NOT** the full OpenEdx AI Extensions integration yet, but rather a working example to understand MCP concepts and test the infrastructure.

Overview
--------

This MVP demonstrates the MCP architecture and workflow using a simple dice-rolling example.

**Note:** The actual OpenEdx-specific tools and integration will be implemented in future iterations. This MVP focuses on validating the MCP infrastructure and communication patterns.

Architecture
------------

The current implementation uses:

- **FastMCP** - A framework for building MCP servers
- **Streamable HTTP** transport - Allows the server to be exposed via HTTP
- **LiteLLM** - For integrating the MCP server with language models

Example Tool: ``roll_dice``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The server currently implements a simple example tool that rolls dice. **This is a demonstration tool only** to show how MCP tools work. This pattern will later be extended to implement OpenEdx-specific operations like course management, user administration, content creation, etc.

Setup
-----

Step 1: Expose the Server with ngrok
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since the MCP protocol requires a publicly accessible endpoint for certain use cases, you need to expose your local server using ngrok:

.. code-block:: bash

    ngrok http http://localhost:8000

ngrok will provide you with a public URL like::

    https://abc123.ngrok-free.app

**Important**: Copy the ngrok URL (including the subdomain) as you'll need it for the client configuration.

Step 3: Update Client Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Edit your settings with:

.. code-block:: yaml

    AI_EXTENSIONS_MCP_CONFIGS:
      dice_server:
        require_approval: never
        server_url: https://<your_ngrok_subdomain>/openedx-ai-extensions/v1/mcp

Replace ``<your_ngrok_subdomain>`` with your actual ngrok subdomain (e.g., ``abc123.ngrok-free.app``).

Step 4: Update you AIWorkflow Configuration to allow MCP Usage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There is a model example config:

.. code-block:: json

    "processor_config": {
      ....,
      "ResponsesProcessor": {
        "function": "chat_with_context",
        "config": "openai",
        "mcp_configs": [
          "dice_server"
        ]
      },
      ....
    },

Testing Workflow
----------------

Now you can test the MCP server and client interaction by asking the AI model to roll dice.
