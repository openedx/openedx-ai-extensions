Model Context Protocol (MCP) - Proof of Concept
================================================

This directory contains a **proof of concept (MVP)** demonstrating how Model Context Protocol (MCP) works. This is **NOT** the full OpenEdx AI Extensions integration yet, but rather a working example to understand MCP concepts and test the infrastructure.

Overview
--------

This MVP demonstrates the MCP architecture and workflow using a simple dice-rolling example. The implementation consists of three main components:

1. **server.py** - A FastMCP server with an example tool (``roll_dice``)
2. **run_server.py** - Script to run the MCP server in HTTP mode
3. **client_example.py** - Example client showing how to interact with the MCP server

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

Prerequisites
~~~~~~~~~~~~~

Install the required dependencies:

.. code-block:: bash

    pip install fastmcp litellm openai

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

Set your OpenAI API key:

.. code-block:: bash

    export OPENAI_API_KEY="your_openai_api_key_here"

Or update it directly in ``client_example.py``.

Running the Server
------------------

Step 1: Start the MCP Server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the server locally on port 9001:

.. code-block:: bash

    python run_server.py

The server will start and listen on ``http://127.0.0.1:9001/mcp``.

Step 2: Expose the Server with ngrok
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since the MCP protocol requires a publicly accessible endpoint for certain use cases, you need to expose your local server using ngrok:

.. code-block:: bash

    # Install ngrok if you haven't already
    # Visit https://ngrok.com/ to download and set up

    # Expose port 9001
    ngrok http 9001

ngrok will provide you with a public URL like::

    https://abc123.ngrok-free.app

**Important**: Copy the ngrok URL (including the subdomain) as you'll need it for the client configuration.

Step 3: Update the Client Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Edit ``client_example.py`` and update the ``server_url`` with your ngrok URL:

.. code-block:: python

    tools=[
        {
            "type": "mcp",
            "server_label": "dice_server",
            "server_url": "https://<your_ngrok_subdomain>.ngrok-free.app/mcp/",
            "require_approval": "never",
        },
    ],

Replace ``<your_ngrok_subdomain>`` with your actual ngrok subdomain (e.g., ``abc123.ngrok-free.app``).

Step 4: Run the Client Example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In a new terminal (while the server and ngrok are still running):

.. code-block:: bash

    python client_example.py

Testing Workflow
----------------

Here's the complete workflow for testing:

1. **Terminal 1** - Start the MCP server:

   .. code-block:: bash

       cd backend/openedx_ai_extensions/mcp
       python run_server.py

2. **Terminal 2** - Expose with ngrok:

   .. code-block:: bash

       ngrok http 9001

   Copy the ngrok URL from the output.

3. **Terminal 3** - Run the client:

   .. code-block:: bash

       # Update client_example.py with your ngrok URL first
       python client_example.py

Expected Output
---------------

When running the client, you should see:

1. List of available tools from the MCP server
2. The AI model response after using the ``roll_dice`` tool

Example::

    Available resources: ['roll_dice']
    Response: <LiteLLM response object with dice roll results>
