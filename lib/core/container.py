import logging
from functools import cached_property

from openai import AsyncOpenAI

from lib.core.config import Settings
from lib.core.database import DatabaseManager
from lib.core.uow import UnitOfWork
from lib.services.reducer.ai_client import DigestAIClient
from lib.services.telegram_sender import TelegramSender


class AppContainer:
    @cached_property
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

    @cached_property
    def openrouter_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(
            base_url=self.settings.openrouter_base_url,
            api_key=self.settings.openrouter_api_key,
        )

    @cached_property
    def digest_ai_client(self) -> DigestAIClient:
        return DigestAIClient(
            client=self.openrouter_client,
            model=self.settings.openrouter_model,
            logger=self.logger,
        )

    @cached_property
    def telegram_sender(self) -> TelegramSender:
        return TelegramSender(
            bot_token=self.settings.bot_token,
            logger=self.logger,
        )

    def uow(self) -> UnitOfWork:
        return self.db.uow()

    async def close(self) -> None:
        if "db" in self.__dict__:
            await self.db.close()
        if "openrouter_client" in self.__dict__:
            await self.openrouter_client.close()


container = AppContainer()
