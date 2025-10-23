# client_litellm.py
import asyncio
from fastmcp import Client, tools
from litellm import completion, responses
import openai


import os 
os.environ["OPENAI_API_KEY"] = "your_openai_api_key_here"


openai_client = openai.OpenAI()

async def main():
    # Connect to the MCP server
    async with Client("http://127.0.0.1:9001/mcp") as client:

        # List resources (optional, just to show it works)
        resources = await client.list_tools()
        print("Available resources:", [r.name for r in resources])

    response = responses(
        model="gpt-4.1-nano",
        reasoning=None,
        tools=[
            {
                "type": "mcp",
                "server_label": "dice_server",
                "server_url": "https://<your_ngrok_subdomain>.ngrok-free.app/mcp/",
                "require_approval": "never",
            },
        ],
        input="Roll a dice for me.",
    )

    print("Response:", response)


if __name__ == "__main__":
    asyncio.run(main())
