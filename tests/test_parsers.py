import pytest

from lib.services.channels import ChannelValidationError, parse_channel_list
from lib.services.interests import InterestValidationError, parse_interest_list


def test_parse_channel_list_normalizes_and_deduplicates() -> None:
    assert parse_channel_list("@channel_one, channel_two @channel_one") == [
        "channel_one",
        "channel_two",
    ]


def test_parse_channel_list_rejects_more_than_five_channels() -> None:
    with pytest.raises(ChannelValidationError, match="too_many_channels"):
        parse_channel_list(
            "@channel1 @channel2 @channel3 @channel4 @channel5 @channel6"
        )


def test_parse_interest_list_normalizes_and_deduplicates() -> None:
    assert parse_interest_list("финансы, технологии\nФинансы") == [
        "финансы",
        "технологии",
    ]


def test_parse_interest_list_rejects_more_than_five_interests() -> None:
    with pytest.raises(InterestValidationError, match="too_many_interests"):
        parse_interest_list("one, two, three, four, five, six")
