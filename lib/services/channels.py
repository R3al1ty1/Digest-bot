import re
from dataclasses import dataclass

from lib.core.constants import MAX_CHANNELS_PER_USER


CHANNEL_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{5,32}$")


class ChannelValidationError(ValueError):
    pass


@dataclass(frozen=True)
class SkippedChannel:
    channel: str
    reason: str


@dataclass(frozen=True)
class ChannelUpdateResult:
    saved_channels: list[str]
    skipped_channels: list[SkippedChannel]


def normalize_channel_username(channel: str) -> str:
    return channel.strip().lstrip("@")


def validate_channel_username_format(channel: str) -> None:
    if not CHANNEL_USERNAME_RE.fullmatch(channel):
        raise ChannelValidationError("invalid_channel_username")


def parse_channel_list(raw_text: str) -> list[str]:
    parts = re.split(r"[\s,]+", raw_text.strip())
    channels: list[str] = []
    seen: set[str] = set()

    for part in parts:
        if not part:
            continue

        channel = normalize_channel_username(part)
        validate_channel_username_format(channel)

        key = channel.lower()
        if key in seen:
            continue

        seen.add(key)
        channels.append(channel)

    if not channels:
        raise ChannelValidationError("empty_channels")

    if len(channels) > MAX_CHANNELS_PER_USER:
        raise ChannelValidationError("too_many_channels")

    return channels


async def filter_accessible_channels(channels: list[str]) -> ChannelUpdateResult:
    from lib.services.scraper.scraper import test_channel_access

    saved_channels: list[str] = []
    skipped_channels: list[SkippedChannel] = []

    for channel in channels:
        if await test_channel_access(channel):
            saved_channels.append(channel)
        else:
            skipped_channels.append(
                SkippedChannel(
                    channel=channel,
                    reason="channel_not_accessible",
                )
            )

    if not saved_channels:
        raise ChannelValidationError("all_channels_not_accessible")

    return ChannelUpdateResult(
        saved_channels=saved_channels,
        skipped_channels=skipped_channels,
    )
