"""Asynchronous Telegram application and its initial command handler."""

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from mcwl_tg_manager.config import Settings
from mcwl_tg_manager.middleware import AllowedChatsMiddleware

START_MESSAGE = "Hello! Minecraft whitelist management is coming soon."


async def handle_start(message: Message) -> None:
    await message.answer(START_MESSAGE)


def create_dispatcher(allowed_chat_ids: frozenset[int]) -> Dispatcher:
    router = Router(name="start")
    router.message.register(handle_start, CommandStart())
    dispatcher = Dispatcher()
    dispatcher.message.outer_middleware(AllowedChatsMiddleware(allowed_chat_ids))
    dispatcher.include_router(router)
    return dispatcher


async def run(settings: Settings) -> None:
    dispatcher = create_dispatcher(settings.allowed_chat_ids)
    async with Bot(token=settings.telegram_bot_token) as bot:
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
            close_bot_session=False,
        )
