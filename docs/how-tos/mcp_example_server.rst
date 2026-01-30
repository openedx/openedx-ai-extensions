.. _local MCP:

Setting Up a Local MCP Example Server
======================================

This guide demonstrates how to create and run a simple MCP (Model Context Protocol) server for testing and development purposes. This example server implements a basic ``roll_dice`` tool to illustrate MCP concepts.

.. note::
   **This is a demonstration only.** The example server shown here is for understanding MCP concepts and testing your integration. This is not intended for production use.

Overview
--------

This example includes:

- A FastMCP server with a sample ``roll_dice`` tool
- A server runner script that exposes the server via HTTP
- A client example showing how to interact with the server

The example demonstrates the complete MCP workflow and can serve as a template for building your own MCP servers.

Prerequisites
-------------

**Python Dependencies:**

Install the required packages:

.. code-block:: bash

    pip install fastmcp litellm openai

**Environment Setup:**

Set your OpenAI API key (needed for the client example):

.. code-block:: bash

    export OPENAI_API_KEY="your-openai-api-key"

Implementation
--------------

Step 1: Create the MCP Server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a file named ``server.py`` with the following content:

.. code-block:: python

    """
    MCP Server implementation using FastMCP

    This is a demonstration server that implements a simple dice-rolling tool.
    Use this as a template for understanding MCP concepts.
    """
    import logging
    from fastmcp import FastMCP
    import random

    logger = logging.getLogger(__name__)

    # Initialize the FastMCP server
    # The 'name' should be descriptive and unique for your server
    # The 'port' is where the server will listen (can be any available port)
    mcp = FastMCP(name="dice_server", port=9001)

    @mcp.tool()
    def roll_dice(n_dice: int) -> list[int]:
        """
        Roll n_dice 6-sided dice and return the results.

        Args:
            n_dice: The number of dice to roll (must be a positive integer)

        Returns:
            A list of integers, each representing the result of one die roll (1-6)

        Example:
            >>> roll_dice(3)
            [4, 2, 6]
        """
        if n_dice <= 0:
            raise ValueError("n_dice must be a positive integer")
        if n_dice > 100:
            raise ValueError("n_dice cannot exceed 100")

        return [random.randint(1, 6) for _ in range(n_dice)]

    # You can add more tools here following the same pattern:
    #
    # @mcp.tool()
    # def your_custom_tool(param1: str, param2: int) -> dict:
    #     """Tool description for the AI model"""
    #     # Your implementation here
    #     return {"result": "some_value"}

**Key Points:**

- The ``@mcp.tool()`` decorator exposes a function as an MCP tool
- The function docstring describes the tool for the AI model
- Type hints are important - they define the tool's input/output schema
- Add error handling for invalid inputs

Step 2: Create the Server Runner
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a file named ``run_server.py``:

.. code-block:: python

    #!/usr/bin/env python
    """
    Run the FastMCP server with HTTP transport

    This script starts the MCP server and makes it accessible via HTTP.
    The 'streamable-http' transport allows the server to be consumed
    by HTTP clients and can be exposed via reverse proxies or tunneling
    services like ngrok.
    """
    from server import mcp

    if __name__ == "__main__":
        # Start the server with HTTP transport
        # The server will be available at http://127.0.0.1:9001/mcp
        mcp.run(transport="streamable-http")

**Transport Options:**

- ``streamable-http``: Exposes the server via HTTP (recommended for network access)
- ``stdio``: Uses standard input/output (for local-only communication)

Step 3: Expose the Server with ngrok
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since MCP clients (including Open edX AI Extensions) need to access the server via a public URL, you must expose your local server using ngrok:

.. code-block:: bash

    # Install ngrok from https://ngrok.com/
    ngrok http 9001

ngrok will provide you with a public URL like:

.. code-block:: text

    https://abc123.ngrok-free.app

**Important:** Copy this URL as you'll need it for the client configuration.

Step 4: Create a Client Example (Optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a file named ``client_example.py`` to test your server:

.. code-block:: python

    """
    Example MCP client using LiteLLM

    This demonstrates how to connect to an MCP server and use its tools
    from a language model. This is similar to how Open edX AI Extensions
    will interact with your MCP servers.
    """
    import asyncio
    from litellm import responses
    import os

    # Set your OpenAI API key
    os.environ["OPENAI_API_KEY"] = "your-api-key-here"

    async def main():
        """
        Connect to the MCP server and ask the AI to use the roll_dice tool
        """
        response = responses(
            model="gpt-4",  # or any supported model
            tools=[
                {
                    "type": "mcp",
                    "server_label": "dice_server",
                    # Use your ngrok URL here
                    "server_url": "https://abc123.ngrok-free.app/mcp/",
                    "require_approval": "never",
                },
            ],
            input="Roll 3 dice for me and tell me what you got.",
        )

        print("Response:", response)

    if __name__ == "__main__":
        asyncio.run(main())

Running the Server
------------------

Complete Workflow
~~~~~~~~~~~~~~~~~

Follow these steps to test the complete MCP workflow:

1. **Start the MCP server** (Terminal 1):

   .. code-block:: bash

       python run_server.py

   The server will be available at ``http://127.0.0.1:9001/mcp``

2. **Expose with ngrok** (Terminal 2):

   .. code-block:: bash

       ngrok http 9001

   Copy the ngrok URL (e.g., ``https://abc123.ngrok-free.app``)

3. **Update the client** with your ngrok URL:

   Edit ``client_example.py`` and replace ``https://abc123.ngrok-free.app`` with your actual ngrok URL.

4. **Run the client** (Terminal 3):

   .. code-block:: bash

       python client_example.py

Testing with Open edX AI Extensions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To integrate this example server with Open edX AI Extensions:

1. **Configure the MCP server** in your Django settings:

   .. code-block:: python

       # In Django settings
       AI_EXTENSIONS_MCP_CONFIGS = {
           "dice_server": {
               "require_approval": "never",
               "server_url": "https://abc123.ngrok-free.app/mcp"  # Your ngrok URL
           }
       }

2. **Add to AI workflow configuration:**

   .. code-block:: json

       {
           "processor_config": {
               "ResponsesProcessor": {
                   "function": "chat_with_context",
                   "config": "openai",
                   "mcp_configs": ["dice_server"]
               }
           }
       }

3. **Test with a query:** Ask the AI assistant something that would trigger the tool, e.g., "Roll some dice for me"

Expected Output
---------------

When everything is configured correctly:

1. The AI model receives your request
2. It identifies that the ``roll_dice`` tool from your MCP server can help
3. It calls the tool with appropriate parameters
4. The tool executes and returns results
5. The AI formulates a response using those results

Example interaction:

.. code-block:: text

    User: Can you roll 3 dice for me?

    AI: I rolled 3 dice for you and got: 4, 2, and 6. The total is 12.

Adding More Tools
-----------------

You can extend this example by adding more tools to the server:

.. code-block:: python

    @mcp.tool()
    def flip_coin() -> str:
        """
        Flip a coin and return either 'heads' or 'tails'.

        Returns:
            A string, either 'heads' or 'tails'
        """
        import random
        return random.choice(['heads', 'tails'])

    @mcp.tool()
    def calculate_sum(numbers: list[int]) -> int:
        """
        Calculate the sum of a list of numbers.

        Args:
            numbers: A list of integers to sum

        Returns:
            The sum of all numbers in the list
        """
        return sum(numbers)

Remember:

- Each tool should have a clear docstring describing its purpose
- Use type hints for parameters and return values
- Keep tools simple and focused on a single task
- Test each tool independently before using with the AI

Further Reading
---------------

- :doc:`mcp_integration` - Main MCP integration guide for Open edX AI Extensions
- `FastMCP Documentation <https://github.com/jlowin/fastmcp>`_ - Complete FastMCP framework documentation
- `MCP Specification <https://modelcontextprotocol.io/>`_ - Official Model Context Protocol specification

.. tip::
   Start with simple tools like the dice example, test thoroughly, then gradually add more complex capabilities. Each tool should do one thing well.
