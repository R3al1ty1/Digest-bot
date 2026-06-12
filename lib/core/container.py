import logging
from functools import cached_property

from lib.core.config import settings
from lib.core.database import DatabaseManager


class AppContainer:
    @cached_property
    def db(self) -> DatabaseManager:
        db = DatabaseManager(
            dsn=settings.database_url,
            environment=settings.environment,
            logger=logging.getLogger("lib.core.database"),
        )
        db.init()
        return db

    async def close(self) -> None:
        if "db" in self.__dict__:
            await self.db.close()


container = AppContainer()
