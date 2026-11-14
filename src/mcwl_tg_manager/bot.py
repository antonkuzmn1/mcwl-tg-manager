"""Asynchronous Telegram application and authorized command handlers."""

import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import BotCommand, BotCommandScopeChat, Message

from mcwl_tg_manager.config import Settings
from mcwl_tg_manager.messages import COMMAND_DESCRIPTIONS, HELP_MESSAGE
from mcwl_tg_manager.middleware import AllowedChatsMiddleware
from mcwl_tg_manager.server import ServerController, ServerControlError

logger = logging.getLogger(__name__)


async def handle_help(message: Message) -> None:
    await message.answer(HELP_MESSAGE)


async def register_commands(bot: Bot, allowed_chat_ids: frozenset[int]) -> None:
    commands = [BotCommand(command=name, description=text) for name, text in COMMAND_DESCRIPTIONS]
    for chat_id in sorted(allowed_chat_ids):
        try:
            await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=chat_id))
        except TelegramAPIError:
            logger.warning("Could not register command menu for chat %s; continuing startup.", chat_id)


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

    router = Router(name="commands")
    router.message.register(handle_help, CommandStart())
    router.message.register(handle_help, Command("help"))
    router.message.register(handle_server, Command("server_start", "server_stop"))
    dispatcher = Dispatcher()
    dispatcher.message.outer_middleware(AllowedChatsMiddleware(allowed_chat_ids))
    dispatcher.include_router(router)

    async def on_startup(bot: Bot) -> None:
        await register_commands(bot, allowed_chat_ids)

    dispatcher.startup.register(on_startup)
    return dispatcher


async def run(settings: Settings) -> None:
    dispatcher = create_dispatcher(settings.allowed_chat_ids)
    async with Bot(token=settings.telegram_bot_token) as bot:
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
            close_bot_session=False,
        )
