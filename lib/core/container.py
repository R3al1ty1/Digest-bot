import logging
from functools import cached_property

from lib.core.config import Settings
from lib.core.database import DatabaseManager
from lib.core.uow import UnitOfWork


class AppContainer:
    @property
    def logger(self) -> logging.Logger:
        return logging.getLogger("lib")

    @cached_property
    def settings(self) -> Settings:
        return Settings()

    @cached_property
    def db(self) -> DatabaseManager:
        return DatabaseManager(
            dsn=self.settings.database_url,
            environment=self.settings.environment,
            logger=self.logger,
        )

    def uow(self) -> UnitOfWork:
        return self.db.uow()

    async def close(self) -> None:
        if "db" in self.__dict__:
            await self.db.close()


container = AppContainer()
