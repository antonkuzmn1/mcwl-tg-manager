"""Asynchronous Telegram application and authorized command handlers."""

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message

from mcwl_tg_manager.config import Settings
from mcwl_tg_manager.middleware import AllowedChatsMiddleware
from mcwl_tg_manager.server import ServerController, ServerControlError

START_MESSAGE = "Hello! Minecraft whitelist management is coming soon."


async def handle_start(message: Message) -> None:
    await message.answer(START_MESSAGE)


def create_dispatcher(
    allowed_chat_ids: frozenset[int],
    controller: ServerController | None = None,
) -> Dispatcher:
    server = controller if controller is not None else ServerController()

    async def handle_server(message: Message, command: CommandObject) -> None:
        if command.args:
            await message.answer(f"Usage: /{command.command}")
            return
        action = "start" if command.command == "server_start" else "stop"
        await message.answer("Starting server container..." if action == "start" else "Stopping server container...")
        try:
            result = await server.change_state(action)
        except ServerControlError as error:
            await message.answer(str(error))
            return
        await message.answer(result)

    router = Router(name="start")
    router.message.register(handle_start, CommandStart())
    router.message.register(handle_server, Command("server_start", "server_stop"))
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
