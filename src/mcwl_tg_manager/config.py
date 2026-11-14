"""Runtime configuration supplied by the deployment environment."""

import os
import re
from dataclasses import dataclass, field

from aiogram.utils.token import TokenValidationError, validate_token


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str = field(repr=False)
    allowed_chat_ids: frozenset[int]

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required.")
        try:
            validate_token(token)
        except TokenValidationError:
            raise ValueError("TELEGRAM_BOT_TOKEN has an invalid format.") from None
        raw_chat_ids = os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "")
        if not raw_chat_ids.strip():
            raise ValueError("TELEGRAM_ALLOWED_CHAT_IDS must contain at least one chat ID.")
        chat_ids = set()
        for item in raw_chat_ids.split(","):
            value = item.strip()
            if not re.fullmatch(r"-?[0-9]{1,16}", value):
                raise ValueError("TELEGRAM_ALLOWED_CHAT_IDS must be comma-separated integer chat IDs.")
            chat_id = int(value)
            if chat_id == 0 or abs(chat_id) >= 2**52:
                raise ValueError("TELEGRAM_ALLOWED_CHAT_IDS contains an out-of-range chat ID.")
            chat_ids.add(chat_id)
        return cls(
            telegram_bot_token=token,
            allowed_chat_ids=frozenset(chat_ids),
        )
