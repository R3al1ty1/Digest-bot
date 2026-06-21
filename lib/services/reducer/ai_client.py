import asyncio
import json
from logging import Logger

from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from lib.core.constants import ModelInteraction
from lib.services.scraper.scraper import Post

MAX_RETRIES = 3
RETRY_DELAY = 10


class DigestAIClient:
    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        logger: Logger,
    ) -> None:
        self._client = client
        self._model = model
        self._logger = logger

    @staticmethod
    def _format_posts_by_channel(posts_by_channel: dict[str, list[Post]]) -> str:
        posts_data = {
            channel: [
                {
                    "id": post.id,
                    "text": post.text[:2000],
                    "link": post.link,
                }
                for post in posts
            ]
            for channel, posts in posts_by_channel.items()
        }
        return json.dumps(posts_data, ensure_ascii=False, indent=2)

    @classmethod
    def _build_user_message(
        cls,
        posts_by_channel: dict[str, list[Post]],
        interests: list[str],
    ) -> str:
        posts_json = cls._format_posts_by_channel(posts_by_channel)
        interests_json = json.dumps(interests, ensure_ascii=False)
        return (
            "Интересы, заданные пользователем:\n"
            f"{interests_json}\n\n"
            "Посты из каналов за последние 24 часа, сгруппированные по источникам:\n\n"
            f"{posts_json}"
        )

    async def generate_interest_based_digest(
        self,
        posts_by_channel: dict[str, list[Post]],
        interests: list[str],
    ) -> tuple[str, int]:
        posts_count = sum(len(posts) for posts in posts_by_channel.values())
        if not posts_count:
            return "За последние 24 часа важных новостей не было.", 0

        user_message = self._build_user_message(posts_by_channel, interests)
        return await self._request_digest_with_retries(user_message, len(interests))

    async def _request_digest(
        self,
        user_message: str,
        interests_count: int,
    ) -> tuple[str, int]:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": ModelInteraction.SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=max(2000, interests_count * 1500),
            temperature=0.3,
        )
        content = response.choices[0].message.content or ""
        tokens_used = response.usage.total_tokens if response.usage else 0

        self._logger.info(
            "AI interest digest received: %s chars, %s tokens",
            len(content),
            tokens_used,
        )

        if not content.strip():
            self._logger.warning("AI returned empty content, using fallback")
            return "Не удалось сгенерировать дайджест. Попробуйте позже.", tokens_used

        return content, tokens_used

    async def _wait_before_retry(self, error: APIError, attempt: int) -> None:
        if isinstance(error, RateLimitError):
            self._logger.warning(
                "Rate limit hit (attempt %s/%s): %s",
                attempt,
                MAX_RETRIES,
                error,
            )
            delay = RETRY_DELAY * attempt
        elif isinstance(error, APITimeoutError):
            self._logger.warning(
                "API timeout (attempt %s/%s): %s",
                attempt,
                MAX_RETRIES,
                error,
            )
            delay = RETRY_DELAY
        else:
            self._logger.error(
                "API error (attempt %s/%s): %s",
                attempt,
                MAX_RETRIES,
                error,
            )
            delay = RETRY_DELAY

        if attempt < MAX_RETRIES:
            await asyncio.sleep(delay)

    async def _request_digest_with_retries(
        self,
        user_message: str,
        interests_count: int,
    ) -> tuple[str, int]:
        last_error: APIError | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return await self._request_digest(user_message, interests_count)
            except APIError as error:
                last_error = error
                await self._wait_before_retry(error, attempt)

        raise Exception(
            f"Failed to generate digest after {MAX_RETRIES} attempts: {last_error}"
        )
