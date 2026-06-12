from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lib.db.models.models import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, telegram_id: int) -> User | None:
        return await self.session.get(User, telegram_id)

    async def get_or_create(
        self, telegram_id: int, username: str | None = None
    ) -> User:
        user = await self.get_by_id(telegram_id)
        if user is None:
            user = User(telegram_id=telegram_id, username=username)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
        return user

    async def get_all_active(self) -> list[User]:
        query = select(User).where(
            User.is_active, User.target_channel.isnot(None)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_schedule_time(self, hour: int, minute: int) -> list[User]:
        schedule = time(hour, minute)
        query = select(User).where(
            User.is_active,
            User.target_channel.isnot(None),
            User.schedule_time == schedule,
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_channel(
        self, telegram_id: int, channel: str
    ) -> User | None:
        user = await self.get_by_id(telegram_id)
        if user:
            user.target_channel = channel
            await self.session.commit()
            await self.session.refresh(user)
        return user

    async def update_schedule(
        self, telegram_id: int, hour: int, minute: int
    ) -> User | None:
        user = await self.get_by_id(telegram_id)
        if user:
            user.schedule_time = time(hour, minute)
            await self.session.commit()
            await self.session.refresh(user)
        return user

    async def set_active(
        self, telegram_id: int, is_active: bool
    ) -> User | None:
        user = await self.get_by_id(telegram_id)
        if user:
            user.is_active = is_active
            await self.session.commit()
            await self.session.refresh(user)
        return user
