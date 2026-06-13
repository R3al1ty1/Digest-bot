from lib.services.telegram_sender import (
    TELEGRAM_CHUNK_LIMIT,
    sanitize_telegram_html,
    split_telegram_message,
)


def test_sanitize_telegram_html_preserves_allowed_tags() -> None:
    text = '<b>Title</b> & <a href="https://example.com">Source</a>'

    assert sanitize_telegram_html(text) == (
        '<b>Title</b> &amp; <a href="https://example.com">Source</a>'
    )


def test_split_telegram_message_keeps_full_text() -> None:
    text = ("hello world\n" * 400).strip()

    chunks = split_telegram_message(text)

    assert len(chunks) > 1
    assert "".join(chunks) == text
    assert all(len(chunk) <= TELEGRAM_CHUNK_LIMIT for chunk in chunks)
