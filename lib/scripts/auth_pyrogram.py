"""
Script for initial Pyrogram authorization.
Run this once to create the .session file.

Usage:
    uv run python -m lib.scripts.auth_pyrogram
"""

import asyncio
from pathlib import Path

from pyrogram import Client

from lib.core.config import settings


SESSION_NAME = "digest_bot"
PROJECT_ROOT = Path(__file__).parent.parent.parent


async def main() -> None:
    print("Starting Pyrogram authorization...")
    print(f"API ID: {settings.api_id}")
    print(f"Phone: {settings.phone_number}")
    print(f"Session will be saved to: {PROJECT_ROOT / SESSION_NAME}.session")
    print()

    app = Client(
        name=SESSION_NAME,
        api_id=settings.api_id,
        api_hash=settings.api_hash,
        phone_number=settings.phone_number,
        workdir=str(PROJECT_ROOT),
    )

    async with app:
        me = await app.get_me()
        print()
        print("Authorization successful!")
        print(f"Logged in as: {me.first_name} (@{me.username})")
        print(f"Session file created: {PROJECT_ROOT / SESSION_NAME}.session")
        print()
        print("You can now run the bot and worker.")


if __name__ == "__main__":
    asyncio.run(main())
