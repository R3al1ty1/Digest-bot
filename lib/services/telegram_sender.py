import html
import re
from logging import Logger

import httpx


TELEGRAM_CHUNK_LIMIT = 3500


def sanitize_telegram_html(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"&lt;b&gt;", "<b>", text)
    text = re.sub(r"&lt;/b&gt;", "</b>", text)
    text = re.sub(r"&lt;i&gt;", "<i>", text)
    text = re.sub(r"&lt;/i&gt;", "</i>", text)
    text = re.sub(r"&lt;a href=&quot;([^&]+)&quot;&gt;", r'<a href="\1">', text)
    text = re.sub(r"&lt;/a&gt;", "</a>", text)
    return text


def split_telegram_message(text: str) -> list[str]:
    if len(text) <= TELEGRAM_CHUNK_LIMIT:
        return [text]

    chunks: list[str] = []
    remaining = text

    while len(remaining) > TELEGRAM_CHUNK_LIMIT:
        split_at = max(
            remaining.rfind("\n\n", 0, TELEGRAM_CHUNK_LIMIT),
            remaining.rfind("\n", 0, TELEGRAM_CHUNK_LIMIT),
            remaining.rfind(" ", 0, TELEGRAM_CHUNK_LIMIT),
        )

        if split_at <= 0:
            split_at = TELEGRAM_CHUNK_LIMIT

        candidate = remaining[:split_at]
        if candidate.rfind("<") > candidate.rfind(">"):
            tag_start = candidate.rfind("<")
            if tag_start > 0:
                candidate = candidate[:tag_start]
                split_at = tag_start

        if not candidate:
            candidate = remaining[:TELEGRAM_CHUNK_LIMIT]
            split_at = TELEGRAM_CHUNK_LIMIT

        chunks.append(candidate)
        remaining = remaining[split_at:]

    if remaining:
        chunks.append(remaining)

    return chunks


class TelegramSender:
    def __init__(self, bot_token: str, logger: Logger) -> None:
        self._url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self._logger = logger

    async def send(self, chat_id: int, text: str) -> bool:
        chunks = split_telegram_message(text)
        if len(chunks) > 1:
            self._logger.info(
                "Sending %s Telegram message chunks to chat %s",
                len(chunks),
                chat_id,
            )

        async with httpx.AsyncClient() as client:
            for chunk in chunks:
                sent = await self._send_chunk(client, chat_id, chunk)
                if not sent:
                    return False

        return True

    async def _send_chunk(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
        text: str,
    ) -> bool:
        sanitized_text = sanitize_telegram_html(text)

        if not sanitized_text.strip():
            self._logger.error(
                "Message chunk is empty after sanitization, original text was: %s",
                text[:500],
            )
            sanitized_text = text

        payload = {
            "chat_id": chat_id,
            "text": sanitized_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        response = await client.post(self._url, json=payload, timeout=30)

        if response.status_code == 200:
            return True

        self._logger.error(
            "Telegram API error (HTML): %s - %s",
            response.status_code,
            response.text,
        )

        payload_plain = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        response = await client.post(self._url, json=payload_plain, timeout=30)

        if response.status_code == 200:
            self._logger.info("Message sent successfully with plain text fallback")
            return True

        self._logger.error(
            "Telegram API error (plain): %s - %s",
            response.status_code,
            response.text,
        )
        return False
