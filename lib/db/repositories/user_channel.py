from datetime import time

from sqlalchemy import delete, exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from lib.db.models.models import DigestInterest, User, UserChannel


class UserChannelRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_active_by_user(self, user_id: int) -> list[UserChannel]:
        query = (
            select(UserChannel)
            .where(
                UserChannel.user_id == user_id,
                UserChannel.is_active,
            )
            .order_by(UserChannel.position, UserChannel.id)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_active_by_user(self, user_id: int) -> int:
        return len(await self.list_active_by_user(user_id))

    async def replace_for_user(
        self,
        user_id: int,
        channels: list[str],
    ) -> list[UserChannel]:
        await self.session.execute(
            delete(UserChannel).where(UserChannel.user_id == user_id)
        )
        user_channels = [
            UserChannel(
                user_id=user_id,
                channel=channel,
                position=index,
            )
            for index, channel in enumerate(channels)
        ]
        self.session.add_all(user_channels)
        await self.session.flush()
        return user_channels

    async def add_channel(self, user_id: int, channel: str) -> UserChannel:
        existing = await self.get_by_user_and_channel(user_id, channel)
        if existing:
            if not existing.is_active:
                existing.is_active = True
                await self.session.flush()
            return existing

        position = await self.count_active_by_user(user_id)
        user_channel = UserChannel(
            user_id=user_id,
            channel=channel,
            position=position,
        )
        self.session.add(user_channel)
        await self.session.flush()
        return user_channel

    async def remove_channel(self, user_id: int, channel: str) -> bool:
        result = await self.session.execute(
            update(UserChannel)
            .where(
                UserChannel.user_id == user_id,
                UserChannel.channel == channel,
                UserChannel.is_active,
            )
            .values(is_active=False)
        )
        await self.session.flush()
        return bool(result.rowcount)

    async def get_by_user_and_channel(
        self,
        user_id: int,
        channel: str,
    ) -> UserChannel | None:
        query = select(UserChannel).where(
            UserChannel.user_id == user_id,
            UserChannel.channel == channel,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def user_has_channels(self, user_id: int) -> bool:
        query = select(
            exists().where(
                UserChannel.user_id == user_id,
                UserChannel.is_active,
            )
        )
        result = await self.session.execute(query)
        return bool(result.scalar())

    async def get_users_by_schedule_time(
        self,
        hour: int,
        minute: int,
    ) -> list[User]:
        schedule = time(hour, minute)
        has_channels = exists().where(
            UserChannel.user_id == User.telegram_id,
            UserChannel.is_active,
        )
        has_interests = exists().where(
            DigestInterest.user_id == User.telegram_id,
        )
        query = select(User).where(
            User.is_active,
            User.schedule_time == schedule,
            has_channels,
            has_interests,
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
