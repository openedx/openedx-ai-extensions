.. _MCP integration:

Model Context Protocol (MCP) Integration
=========================================

.. warning::
   **Important: Open edX AI Extensions acts as an MCP CLIENT only**
   
   This application **does not run or host MCP servers**. It only connects to external MCP servers as a client.
   
   - You are responsible for deploying and maintaining your own MCP servers
   - The MCP servers must be externally accessible (e.g., via HTTPS endpoints)
   - This application will never expose MCP server functionality - it only consumes MCP tools from external servers

Overview
--------

The Model Context Protocol (MCP) is an open standard that enables AI assistants to securely interact with external tools and data sources. Open edX AI Extensions integrates with MCP by acting as a **client** that can connect to external MCP servers, allowing your AI workflows to leverage custom tools and capabilities.

Key Concepts
~~~~~~~~~~~~

- **MCP Server**: An external service that exposes tools and resources via the MCP protocol. You must deploy and manage these servers independently.
- **MCP Client**: Open edX AI Extensions acts as a client, connecting to your MCP servers and making their tools available to AI workflows.
- **MCP Tools**: Functions exposed by MCP servers that the AI model can call to perform specific operations (e.g., data retrieval, computations, integrations).

Architecture
------------

.. code-block:: text

    ┌────────────────────────────────────────────┐
    │   Open edX AI Extensions                   │
    │   (MCP Client / Orchestrator)              │
    │                                            │
    │   ┌──────────────────────┐                 │
    │   │  AI Workflow         │                 │
    │   │  Processor           │                 │
    │   └─────────┬────────────┘                 │
    │             │                              │
    │             │ 1. LLM API call              │
    │             │    (optional MCP config:     │
    │             │     tools, servers, auth)    │
    │             ▼                              │
    │   ┌──────────────────────┐                 │
    │   │   LLM Provider API   │                 │
    │   │   (OpenAI, etc.)     │                 │
    │   └─────────┬────────────┘                 │
    │             │                              │
    │   Tool call │ 2. Tool-use request          │
    │   decision  │    (by the LLM)              │
    │             ▼                              │
    │   ┌──────────────────────┐                 │
    │   │ MCP Tool Executor    │                 │
    │   │ (client-side logic)  │                 │
    │   └─────────┬────────────┘                 │
    │             │ HTTPS                        │
    └─────────────┼──────────────────────────────┘
                  │
                  │ 3. Execute MCP tools
                  │
    ┌─────────────▼──────────────────────────────┐
    │   External MCP Server                      │
    │   (Your Infrastructure)                    │
    │                                            │
    │   - Custom tools                           │
    │   - Resources                              │
    │   - Business logic                         │
    │                                            │
    └─────────────┬──────────────────────────────┘
                  │
                  │ 4. Tool results
                  │
    ┌─────────────▼──────────────────────────────┐
    │   Back to LLM Provider API                 │
    │   (tool results sent, final response)      │
    └────────────────────────────────────────────┘


Configuration
-------------

Step 1: Configure MCP Server Connections
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

MCP servers are configured in your Django settings using the ``AI_EXTENSIONS_MCP_CONFIGS`` setting. This dictionary maps server labels to their connection details.

**Configuration Format:**

.. code-block:: python

    AI_EXTENSIONS_MCP_CONFIGS = {
        "server_label": {
            "require_approval": "never",  # or "always"
            "server_url": "https://your-mcp-server.example.com/mcp"
        },
        "another_server": {
            "require_approval": "always",
            "server_url": "https://another-server.example.com/mcp"
        }
    }

**Configuration Parameters:**

The configuration accepts any parameter supported by `LiteLLM's MCP configuration <https://docs.litellm.ai/docs/>`_. Common parameters include:

- ``server_label`` (key): A unique identifier for the MCP server. You'll reference this label in your AI workflow configuration.
- ``server_url`` (string): The HTTPS endpoint of your MCP server. Must be publicly accessible.
- ``require_approval`` (string): Controls whether tool calls require approval
  
  - ``"never"``: Tools are called automatically without user intervention (use for trusted servers)
  - ``"always"``: User must approve each tool call (recommended for testing or sensitive operations)

- ``authorization`` (string, optional): Authorization header value for authenticating with the MCP server (e.g., ``"Bearer your-token-here"``)

You can use any additional parameters that LiteLLM supports for MCP server configuration.

**Example Configuration:**

.. code-block:: python

    # In your Django settings
    AI_EXTENSIONS_MCP_CONFIGS = {
        "analytics_server": {
            "require_approval": "never",
            "server_url": "https://analytics.mycompany.com/mcp"
        },
        "content_manager": {
            "require_approval": "always",
            "server_url": "https://cms-tools.mycompany.com/mcp"
        }
    }

Step 2: Enable MCP in AI Workflow Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once your MCP servers are configured, you need to enable them in your AI workflow processor configuration. Add the ``mcp_configs`` parameter to your processor configuration, listing the server labels you want to use.

**Configuration Format:**

.. code-block:: json

    {
        "processor_config": {
            "ResponsesProcessor": {
                "function": "chat_with_context",
                "config": "openai",
                "mcp_configs": [
                    "server_label_1",
                    "server_label_2"
                ]
            }
        }
    }

**Example Configuration:**

.. code-block:: json

    {
        "processor_config": {
            "ResponsesProcessor": {
                "function": "chat_with_context",
                "config": "openai",
                "mcp_configs": [
                    "analytics_server",
                    "content_manager"
                ]
            },
            "ContextProcessor": {
                "function": "retrieve_relevant_documents",
                "config": "default"
            }
        }
    }

In this example:

- The ``ResponsesProcessor`` will have access to tools from both ``analytics_server`` and ``content_manager``
- The AI model can call any tools exposed by these MCP servers during the chat workflow
- Multiple MCP servers can be combined to provide a rich set of capabilities

Usage Workflow
--------------

Once configured, MCP tools are automatically available to your AI workflows:

1. **User makes a request** to the AI assistant
2. **AI model analyzes** the request and determines if MCP tools are needed
3. **AI model calls** the appropriate MCP tool(s) via the configured server(s)
4. **MCP server processes** the tool call and returns results
5. **AI model uses** the results to formulate a response
6. **User receives** the final response

This happens transparently - users don't need to know about MCP implementation details.

Best Practices
--------------

Security
~~~~~~~~

- **Always use HTTPS** for MCP server URLs
- **Implement authentication** on your MCP servers to prevent unauthorized access
- **Use "require_approval: always"** when testing new MCP servers
- **Audit tool usage** regularly to ensure tools are being used appropriately
- **Limit tool capabilities** - only expose what's necessary through your MCP servers

Further Reading
---------------

- :doc:`mcp_example_server` - Learn how to set up a local MCP server for testing
- `MCP Specification <https://modelcontextprotocol.io/>`_ - Official Model Context Protocol documentation
- `FastMCP Framework <https://github.com/jlowin/fastmcp>`_ - Python framework for building MCP servers

.. note::
   For a complete working example of an MCP server setup for local testing and development, see the :doc:`mcp_example_server` guide.
