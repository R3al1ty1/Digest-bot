from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from lib.db.models.models import DigestInterest


class DigestInterestRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_user(self, user_id: int) -> list[DigestInterest]:
        query = (
            select(DigestInterest)
            .where(DigestInterest.user_id == user_id)
            .order_by(DigestInterest.position, DigestInterest.id)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def replace_for_user(
        self,
        user_id: int,
        interests: list[str],
    ) -> list[DigestInterest]:
        await self.session.execute(
            delete(DigestInterest).where(DigestInterest.user_id == user_id)
        )
        digest_interests = [
            DigestInterest(
                user_id=user_id,
                interest=interest,
                position=index,
            )
            for index, interest in enumerate(interests)
        ]
        self.session.add_all(digest_interests)
        await self.session.flush()
        return digest_interests
