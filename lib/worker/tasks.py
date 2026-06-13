import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from lib.core.container import container
from lib.services.reducer.ai_client import generate_interest_based_digest
from lib.services.scraper.scraper import fetch_channel_posts
from lib.services.telegram_sender import send_telegram_message
from lib.worker.celery_app import app

logger = logging.getLogger(__name__)


async def _generate_digest_for_user(
    user_id: int,
    channels: list[str] | None = None,
    interests: list[str] | None = None,
) -> None:
    """Generate and send digest for a single user."""
    logger.info("Generating digest for user %s", user_id)

    async with container.uow() as uow:
        try:
            user = await uow.users.get_by_id(user_id)
            if not user:
                logger.warning("User %s not found for digest", user_id)
                return

            if not channels:
                user_channels = await uow.user_channels.list_active_by_user(user_id)
                channels = [item.channel for item in user_channels]

            if not channels and user.target_channel:
                channels = [user.target_channel]

            if not interests:
                user_interests = await uow.digest_interests.list_by_user(user_id)
                interests = [item.interest for item in user_interests]

            if not channels:
                await send_telegram_message(
                    user_id,
                    "Сначала укажи каналы для дайджеста командой /set_channels",
                )
                return

            if not interests:
                await send_telegram_message(
                    user_id,
                    "Сначала укажи интересы для дайджеста командой /set_interests",
                )
                return

            posts_by_channel = {}
            fetch_errors: list[str] = []

            for channel in channels:
                try:
                    posts = await fetch_channel_posts(channel, hours=24)
                    posts_by_channel[channel] = posts
                    logger.info("Fetched %s posts from %s", len(posts), channel)
                except Exception as e:
                    logger.exception("Failed to fetch channel %s: %s", channel, e)
                    fetch_errors.append(channel)

            total_posts = sum(len(posts) for posts in posts_by_channel.values())

            if not posts_by_channel and fetch_errors:
                error_message = "Failed to fetch all channels: " + ", ".join(fetch_errors)
                await uow.digest_logs.create(
                    user_id=user_id,
                    channel="multiple" if len(channels) > 1 else channels[0],
                    channels=channels,
                    channels_count=len(channels),
                    interests=interests,
                    status="error",
                    error_message=error_message[:1000],
                )
                await send_telegram_message(
                    user_id,
                    "Не удалось получить данные ни из одного канала. Попробуйте позже.",
                )
                return

            digest_text, tokens_used = await generate_interest_based_digest(
                posts_by_channel,
                interests,
            )

            sent = await send_telegram_message(user_id, digest_text)
            legacy_channel = channels[0] if len(channels) == 1 else "multiple"
            error_message = None
            if fetch_errors:
                error_message = "Failed to fetch channels: " + ", ".join(fetch_errors)

            if sent:
                await uow.digest_logs.create(
                    user_id=user_id,
                    channel=legacy_channel,
                    channels=channels,
                    channels_count=len(channels),
                    interests=interests,
                    items_count=total_posts,
                    tokens_used=tokens_used,
                    status="success",
                    error_message=error_message[:1000] if error_message else None,
                )
                logger.info(f"Digest sent to user {user_id}")
            else:
                await uow.digest_logs.create(
                    user_id=user_id,
                    channel=legacy_channel,
                    channels=channels,
                    channels_count=len(channels),
                    interests=interests,
                    items_count=total_posts,
                    tokens_used=tokens_used,
                    status="error",
                    error_message="Failed to send message",
                )
                logger.error(f"Failed to send digest to user {user_id}")

        except Exception as e:
            logger.exception(f"Error generating digest for user {user_id}: {e}")
            await uow.digest_logs.create(
                user_id=user_id,
                channel="multiple" if channels and len(channels) > 1 else (channels or ["unknown"])[0],
                channels=channels,
                channels_count=len(channels or []),
                interests=interests,
                status="error",
                error_message=str(e)[:1000],
            )
            await send_telegram_message(
                user_id,
                "Произошла ошибка при генерации дайджеста.\n\n"
                "Попробуйте позже или проверьте, что канал доступен.",
            )


@app.task(name="lib.worker.tasks.generate_digest_task")
def generate_digest_task(
    user_id: int,
    channel: str | None = None,
    channels: list[str] | None = None,
    interests: list[str] | None = None,
) -> dict:
    """
    Celery task: Generate digest for a specific user.
    Called manually via /digest command.
    """
    if channel and not channels:
        channels = [channel]

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_generate_digest_for_user(user_id, channels, interests))
    return {
        "user_id": user_id,
        "channels": channels,
        "interests": interests,
        "status": "completed",
    }


@app.task(name="lib.worker.tasks.scheduled_digest_task")
def scheduled_digest_task() -> dict:
    """
    Celery task: Generate digests for users scheduled at current hour.
    Called by Celery Beat every hour.
    """
    async def _run_for_scheduled_users():
        now = datetime.now(ZoneInfo("Europe/Moscow"))
        current_hour = now.hour
        current_minute = 0

        async with container.uow() as uow:
            users = await uow.user_channels.get_users_by_schedule_time(
                current_hour,
                current_minute,
            )

        logger.info(
            f"Running scheduled digest for {len(users)} users at {current_hour:02d}:{current_minute:02d} GMT+3"
        )

        for user in users:
            try:
                await _generate_digest_for_user(user.telegram_id)
            except Exception as e:
                logger.exception(f"Error for user {user.telegram_id}: {e}")

        return len(users)

    loop = asyncio.get_event_loop()
    count = loop.run_until_complete(_run_for_scheduled_users())
    return {"processed_users": count, "status": "completed"}
