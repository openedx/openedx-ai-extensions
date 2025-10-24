# client_litellm.py
import asyncio
from fastmcp import Client
from litellm import responses
import os
import openai

from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.server.auth.providers.bearer import RSAKeyPair
from pydantic import SecretStr

# Read key pair
with open("private.pem", "r") as private_key_file:
    private_key_content = private_key_file.read()

with open("public.pem", "r") as public_key_file:
    public_key_content = public_key_file.read()

os.environ["OPENAI_API_KEY"] = "your_openai_api_key_here"


openai_client = openai.OpenAI()
key_pair = RSAKeyPair(
    private_key=SecretStr(private_key_content),
    public_key=public_key_content
)

async def main():
    # Generate JWT token
    token = key_pair.create_token(
        subject="user@example.com",
        issuer="https://<your_ngrok_subdomain>.ngrok-free.app",
        audience="dice_server",
        scopes=["read", "write"]
    )


    response = responses(
        model="gpt-4.1-nano",
        reasoning=None,
        tools=[
            {
                "type": "mcp",
                "server_label": "dice_server",
                "server_url": "https://ce888b1c33bf.ngrok-free.app/mcp/",
                "require_approval": "never",
                "authorization": token,
            },
        ],
        input="Roll a dice for me.",
    )

    print("Response:", response)


if __name__ == "__main__":
    asyncio.run(main())
