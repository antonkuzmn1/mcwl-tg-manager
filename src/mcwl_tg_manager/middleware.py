"""Chat-level access control for incoming Telegram messages."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message


class AllowedChatsMiddleware(BaseMiddleware):
    def __init__(self, allowed_chat_ids: frozenset[int]) -> None:
        self.allowed_chat_ids = allowed_chat_ids

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if event.chat.id not in self.allowed_chat_ids:
            return None
        return await handler(event, data)
