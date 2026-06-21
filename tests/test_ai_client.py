import json
from datetime import datetime, timezone

from lib.core.constants import ModelInteraction
from lib.services.reducer.ai_client import DigestAIClient
from lib.services.scraper.scraper import Post


def test_interest_digest_prompt_uses_interests_as_selection_criteria() -> None:
    prompt = ModelInteraction.SYSTEM_PROMPT

    assert "Список интересов — главный критерий отбора" in prompt
    assert "примерно 7-10 ключевых событий на каждый интерес" in prompt
    assert "Это не минимум, не максимум и не квота" in prompt
    assert "Если качественных событий меньше 7 — покажи меньше" in prompt
    assert "Если значимых событий больше 10 — включи все" in prompt
    assert "не относится ни к одному интересу" in prompt
    assert "Не сохраняй новостную часть рекламного поста" in prompt
    assert "Сгруппируй дубли до отбора" in prompt
    assert "даже если они пришли из разных каналов" in prompt


def test_posts_are_grouped_by_source_for_interest_prompt() -> None:
    post = Post(
        id=1,
        text="Новость",
        link="https://t.me/source/1",
        date=datetime.now(timezone.utc),
    )

    formatted = DigestAIClient._format_posts_by_channel({"source": [post]})

    assert json.loads(formatted) == {
        "source": [
            {
                "id": 1,
                "text": "Новость",
                "link": "https://t.me/source/1",
            }
        ]
    }


def test_user_message_contains_interests_and_grouped_posts() -> None:
    post = Post(
        id=1,
        text="Новость",
        link="https://t.me/source/1",
        date=datetime.now(timezone.utc),
    )

    message = DigestAIClient._build_user_message(
        {"source": [post]},
        ["финансы", "технологии"],
    )

    assert '["финансы", "технологии"]' in message
    assert '"source": [' in message
    assert '"link": "https://t.me/source/1"' in message
