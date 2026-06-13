from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lib.db.models.models import DigestLog


class DigestLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: int,
        channel: str,
        channels: list[str] | None = None,
        channels_count: int | None = None,
        interests: list[str] | None = None,
        items_count: int = 0,
        tokens_used: int = 0,
        status: str = "success",
        error_message: str | None = None,
    ) -> DigestLog:
        log = DigestLog(
            user_id=user_id,
            channel=channel,
            channels=channels,
            channels_count=channels_count or len(channels or [channel]),
            interests=interests,
            items_count=items_count,
            tokens_used=tokens_used,
            status=status,
            error_message=error_message,
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def get_user_logs(
        self, user_id: int, limit: int = 10
    ) -> list[DigestLog]:
        query = (
            select(DigestLog)
            .where(DigestLog.user_id == user_id)
            .order_by(DigestLog.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
