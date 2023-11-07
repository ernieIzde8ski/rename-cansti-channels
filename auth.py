import asyncio
from os import getenv

from discord import Client
from dotenv import load_dotenv


class AuthFailure(Exception):
    pass


async def login_with_env(client: Client):
    """Login + connect (without losing control) to Discord"""
    load_dotenv()

    token = getenv("DISCORD_BOT_TOKEN")

    if not token:
        raise AuthFailure(
            "Couldn't find a token in the environment! "
            "Try setting the `DISCORD_BOT_TOKEN` variable in your shell or .env file."
        )

    await client.login(token)
    asyncio.get_event_loop().create_task(client.connect())
