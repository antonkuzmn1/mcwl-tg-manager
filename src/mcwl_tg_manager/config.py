"""Runtime configuration supplied by the deployment environment."""

import os
from dataclasses import dataclass, field

from aiogram.utils.token import TokenValidationError, validate_token


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str = field(repr=False)

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required.")
        try:
            validate_token(token)
        except TokenValidationError:
            raise ValueError("TELEGRAM_BOT_TOKEN has an invalid format.") from None
        return cls(telegram_bot_token=token)
