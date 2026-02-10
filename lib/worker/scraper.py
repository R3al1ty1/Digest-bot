"""Pyrogram client for scraping Telegram channels."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pyrogram import Client
from pyrogram.types import Message

from lib.core.config import settings


SESSION_NAME = "digest_bot"


def _get_workdir() -> str:
    """Get workdir for session - works both locally and in Docker."""
    # In Docker, workdir is /app
    docker_path = Path("/app") / f"{SESSION_NAME}.session"
    if docker_path.exists():
        return "/app"

    # Locally, session is in project root
    return str(Path(__file__).parent.parent.parent)


@dataclass
class Post:
    id: int
    text: str
    link: str
    date: datetime


def get_pyrogram_client() -> Client:
    return Client(
        name=SESSION_NAME,
        api_id=settings.api_id,
        api_hash=settings.api_hash,
        workdir=_get_workdir(),
    )


def _build_post_link(channel_username: str, message_id: int) -> str:
    return f"https://t.me/{channel_username}/{message_id}"


def _is_valid_message(message: Message) -> bool:
    # Skip service messages (join, leave, pin, etc.)
    if message.service:
        return False

    # Skip empty messages
    if not message.text and not message.caption:
        return False

    return True


def _extract_text(message: Message) -> str:
    return message.text or message.caption or ""


async def fetch_channel_posts(
    channel_username: str,
    hours: int = 24,
    limit: int = 100,
) -> list[Post]:
    """
    Fetch posts from a Telegram channel for the last N hours.

    Args:
        channel_username: Channel username without @
        hours: How many hours back to fetch (default 24)
        limit: Max number of messages to fetch (default 100)

    Returns:
        List of Post objects with id, text, link, date
    """
    channel_username = channel_username.lstrip("@")
    cutoff_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
    posts: list[Post] = []

    client = get_pyrogram_client()

    async with client:
        async for message in client.get_chat_history(channel_username, limit=limit):
            # Stop if message is older than cutoff
            if message.date < cutoff_time:
                break

            if not _is_valid_message(message):
                continue

            text = _extract_text(message)
            if not text.strip():
                continue

            post = Post(
                id=message.id,
                text=text,
                link=_build_post_link(channel_username, message.id),
                date=message.date,
            )
            posts.append(post)

    return posts


async def test_channel_access(channel_username: str) -> bool:
    """
    Test if we can access a channel.

    Returns True if accessible, False otherwise.
    """
    channel_username = channel_username.lstrip("@")
    client = get_pyrogram_client()

    try:
        async with client:
            chat = await client.get_chat(channel_username)
            return chat is not None
    except Exception:
        return False
