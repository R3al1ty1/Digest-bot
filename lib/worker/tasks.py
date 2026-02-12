import asyncio
import html
import logging
import re

import httpx

from lib.core.config import settings
from lib.db.database import async_session_maker
from lib.db.repositories import DigestLogRepository, UserRepository
from lib.worker.ai_client import generate_digest
from lib.worker.celery_app import app
from lib.worker.scraper import fetch_channel_posts


logger = logging.getLogger(__name__)


def _sanitize_telegram_html(text: str) -> str:
    """
    Sanitize HTML for Telegram - escape invalid chars but preserve allowed tags.
    Telegram allows: <b>, <i>, <u>, <s>, <code>, <pre>, <a href="">.
    """
    # First, escape all HTML entities
    text = html.escape(text)

    # Then restore allowed tags
    # Restore <b> and </b>
    text = re.sub(r'&lt;b&gt;', '<b>', text)
    text = re.sub(r'&lt;/b&gt;', '</b>', text)

    # Restore <i> and </i>
    text = re.sub(r'&lt;i&gt;', '<i>', text)
    text = re.sub(r'&lt;/i&gt;', '</i>', text)

    # Restore <a href="..."> and </a>
    text = re.sub(r'&lt;a href=&quot;([^&]+)&quot;&gt;', r'<a href="\1">', text)
    text = re.sub(r'&lt;/a&gt;', '</a>', text)

    return text


async def _send_telegram_message(chat_id: int, text: str) -> bool:
    """Send message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"

    # Telegram message limit is 4096 characters
    MAX_LENGTH = 4096

    # Truncate if too long
    if len(text) > MAX_LENGTH:
        text = text[:MAX_LENGTH - 50] + "\n\n... (сообщение обрезано)"
        logger.warning(f"Message truncated to {MAX_LENGTH} chars for chat {chat_id}")

    async with httpx.AsyncClient() as client:
        # Try with HTML first (sanitize to fix invalid entities)
        sanitized_text = _sanitize_telegram_html(text)

        # Check if text is empty after sanitization
        if not sanitized_text.strip():
            logger.error("Message is empty after sanitization, original text was: %s", text[:500])
            sanitized_text = text  # Use original text as fallback

        payload = {
            "chat_id": chat_id,
            "text": sanitized_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        response = await client.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            return True

        # Log the error
        logger.error(f"Telegram API error (HTML): {response.status_code} - {response.text}")

        # Fallback: try without HTML parsing (plain text)
        payload_plain = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        response = await client.post(url, json=payload_plain, timeout=30)

        if response.status_code == 200:
            logger.info("Message sent successfully with plain text fallback")
            return True

        logger.error(f"Telegram API error (plain): {response.status_code} - {response.text}")
        return False


async def _generate_digest_for_user(user_id: int, channel: str) -> None:
    """Generate and send digest for a single user."""
    logger.info(f"Generating digest for user {user_id}, channel: {channel}")

    async with async_session_maker() as session:
        log_repo = DigestLogRepository(session)

        try:
            # Fetch posts from channel
            posts = await fetch_channel_posts(channel, hours=24)

            logger.info(f"Fetched {len(posts)} posts from {channel}")

            # Generate digest via AI
            digest_text, tokens_used = await generate_digest(posts)

            # Send to user
            sent = await _send_telegram_message(user_id, digest_text)

            if sent:
                await log_repo.create(
                    user_id=user_id,
                    channel=channel,
                    items_count=len(posts),
                    tokens_used=tokens_used,
                    status="success",
                )
                logger.info(f"Digest sent to user {user_id}")
            else:
                await log_repo.create(
                    user_id=user_id,
                    channel=channel,
                    items_count=len(posts),
                    tokens_used=tokens_used,
                    status="error",
                    error_message="Failed to send message",
                )
                logger.error(f"Failed to send digest to user {user_id}")

        except Exception as e:
            logger.exception(f"Error generating digest for user {user_id}: {e}")
            await log_repo.create(
                user_id=user_id,
                channel=channel,
                status="error",
                error_message=str(e)[:1000],
            )
            # Notify user about the error
            await _send_telegram_message(
                user_id,
                f"Произошла ошибка при генерации дайджеста для канала @{channel}.\n\n"
                f"Попробуйте позже или проверьте, что канал доступен.",
            )


@app.task(name="lib.worker.tasks.generate_digest_task")
def generate_digest_task(user_id: int, channel: str) -> dict:
    """
    Celery task: Generate digest for a specific user.
    Called manually via /digest command.
    """
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_generate_digest_for_user(user_id, channel))
    return {"user_id": user_id, "channel": channel, "status": "completed"}


@app.task(name="lib.worker.tasks.scheduled_digest_task")
def scheduled_digest_task() -> dict:
    """
    Celery task: Generate digests for all active users.
    Called by Celery Beat on schedule.
    """
    async def _run_for_all_users():
        async with async_session_maker() as session:
            user_repo = UserRepository(session)
            users = await user_repo.get_all_active()

            logger.info(f"Running scheduled digest for {len(users)} users")

            for user in users:
                if user.target_channel:
                    try:
                        await _generate_digest_for_user(
                            user.telegram_id,
                            user.target_channel,
                        )
                    except Exception as e:
                        logger.exception(f"Error for user {user.telegram_id}: {e}")

            return len(users)

    loop = asyncio.get_event_loop()
    count = loop.run_until_complete(_run_for_all_users())
    return {"processed_users": count, "status": "completed"}
