import re

from lib.core.constants import MAX_INTERESTS_PER_USER


class InterestValidationError(ValueError):
    pass


def normalize_interest(interest: str) -> str:
    return re.sub(r"\s+", " ", interest.strip())


def validate_interest(interest: str) -> None:
    if not interest:
        raise InterestValidationError("empty_interest")

    if len(interest) > 100:
        raise InterestValidationError("invalid_interest")


def parse_interest_list(raw_text: str) -> list[str]:
    parts = re.split(r"[,\n]+", raw_text.strip())
    interests: list[str] = []
    seen: set[str] = set()

    for part in parts:
        interest = normalize_interest(part)
        if not interest:
            continue

        validate_interest(interest)

        key = interest.casefold()
        if key in seen:
            continue

        seen.add(key)
        interests.append(interest)

    if not interests:
        raise InterestValidationError("empty_interests")

    if len(interests) > MAX_INTERESTS_PER_USER:
        raise InterestValidationError("too_many_interests")

    return interests
