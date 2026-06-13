import asyncio
import json
import logging

from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError

from lib.core.config import settings
from lib.core.constants import ModelInteraction
from lib.services.scraper.scraper import Post


logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds - бесплатные модели имеют лимит ~8 req/min


def get_openrouter_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
    )


def _format_posts_for_prompt(posts: list[Post]) -> str:
    posts_data = [
        {
            "id": p.id,
            "text": p.text[:2000],  # Truncate long posts
            "link": p.link,
        }
        for p in posts
    ]
    return json.dumps(posts_data, ensure_ascii=False, indent=2)


def _format_posts_by_channel_for_prompt(
    posts_by_channel: dict[str, list[Post]]
) -> str:
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


async def generate_interest_based_digest(
    posts_by_channel: dict[str, list[Post]],
    interests: list[str],
) -> tuple[str, int]:
    posts_count = sum(len(posts) for posts in posts_by_channel.values())
    if not posts_count:
        return "За последние 24 часа важных новостей не было.", 0

    client = get_openrouter_client()
    posts_json = _format_posts_by_channel_for_prompt(posts_by_channel)
    interests_json = json.dumps(interests, ensure_ascii=False)

    system_prompt = (
        ModelInteraction.SYSTEM_PROMPT
        + """

    # USER INTERESTS MODE
    Пользователь задал список интересов/сфер. Итоговый дайджест должен быть сгруппирован по этим интересам, а не по каналам.
    Не создавай отдельные разделы по каналам.
    Внутри каждого пункта сохраняй ссылку на источник через <a href="URL">Источник</a>.
    Если новость не относится ни к одному интересу и не является важной, пропусти ее.
    Если по интересу нет важных новостей, не добавляй пустой раздел.
        """
    )

    user_message = (
        "Интересы пользователя:\n"
        f"{interests_json}\n\n"
        "Посты из каналов за последние 24 часа, сгруппированные по источникам:\n\n"
        f"{posts_json}"
    )

    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=settings.openrouter_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=2000,
                temperature=0.3,
            )

            content = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else 0

            logger.info(
                "AI interest digest received: %s chars, %s tokens",
                len(content),
                tokens_used,
            )

            if not content.strip():
                logger.warning("AI returned empty content, using fallback")
                return "Не удалось сгенерировать дайджест. Попробуйте позже.", tokens_used

            return content, tokens_used

        except RateLimitError as e:
            logger.warning(f"Rate limit hit (attempt {attempt}/{MAX_RETRIES}): {e}")
            last_error = e
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY * attempt)

        except APITimeoutError as e:
            logger.warning(f"API timeout (attempt {attempt}/{MAX_RETRIES}): {e}")
            last_error = e
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)

        except APIError as e:
            logger.error(f"API error (attempt {attempt}/{MAX_RETRIES}): {e}")
            last_error = e
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)

    raise Exception(f"Failed to generate digest after {MAX_RETRIES} attempts: {last_error}")


async def generate_digest(posts: list[Post]) -> tuple[str, int]:
    """
    Generate a news digest from posts using OpenRouter AI.

    Args:
        posts: List of Post objects to summarize

    Returns:
        Tuple of (digest_text, tokens_used)

    Raises:
        Exception if all retries fail
    """
    if not posts:
        return "За последние 24 часа важных новостей не было.", 0

    client = get_openrouter_client()
    posts_json = _format_posts_for_prompt(posts)

    user_message = f"Вот посты из канала за последние 24 часа:\n\n{posts_json}"

    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=settings.openrouter_model,
                messages=[
                    {"role": "system", "content": ModelInteraction.SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=2000,
                temperature=0.3,
            )

            content = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else 0

            logger.info(f"AI response received: {len(content)} chars, {tokens_used} tokens")

            if not content.strip():
                logger.warning("AI returned empty content, using fallback")
                return "Не удалось сгенерировать дайджест. Попробуйте позже.", tokens_used

            return content, tokens_used

        except RateLimitError as e:
            logger.warning(f"Rate limit hit (attempt {attempt}/{MAX_RETRIES}): {e}")
            last_error = e
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY * attempt)

        except APITimeoutError as e:
            logger.warning(f"API timeout (attempt {attempt}/{MAX_RETRIES}): {e}")
            last_error = e
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)

        except APIError as e:
            logger.error(f"API error (attempt {attempt}/{MAX_RETRIES}): {e}")
            last_error = e
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)

    raise Exception(f"Failed to generate digest after {MAX_RETRIES} attempts: {last_error}")
