"""Asynchronous Telegram application and authorized command handlers."""

import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import BotCommand, BotCommandScopeChat, Message

from mcwl_tg_manager.config import Settings
from mcwl_tg_manager.messages import (
    COMMAND_DESCRIPTIONS, COMMAND_USAGE, HELP_MESSAGE, READINESS_ERRORS,
    SERVER_ALREADY_STOPPED, SERVER_READY, SERVER_STARTING, SERVER_STOP_FAILED,
    SERVER_STOPPED, SERVER_STOPPING,
    WHITELIST_EMPTY, WHITELIST_HEADER, WHITELIST_INVALID_NAME, WHITELIST_USAGE,
    WHITELIST_RESULTS, WHITELIST_FAILED, WHITELIST_ERRORS,
)
from mcwl_tg_manager.middleware import AllowedChatsMiddleware
from mcwl_tg_manager.server import PLAYER_NAME, ServerController, ServerControlError

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
            await message.answer(COMMAND_USAGE.format(command=command.command))
            return
        action = "start" if command.command == "server_start" else "stop"
        await message.answer(SERVER_STARTING if action == "start" else SERVER_STOPPING)
        try:
            result = await server.change_state(action)
            if action == "start":
                await server.wait_until_ready()
                result = SERVER_READY
            else:
                result = SERVER_ALREADY_STOPPED if result == "The server container is already stopped." else SERVER_STOPPED
        except ServerControlError as error:
            if action == "stop":
                logger.warning("Server stop operation failed: %s", error)
                await message.answer(SERVER_STOP_FAILED)
            else:
                await message.answer(READINESS_ERRORS.get(error.code, str(error)))
            return
        await message.answer(result)

    async def handle_whitelist(message: Message, command: CommandObject) -> None:
        action = command.command.removeprefix("wl_")
        player = (command.args or "").strip()
        if action == "list" and player:
            await message.answer(WHITELIST_USAGE[action])
            return
        if action != "list" and not PLAYER_NAME.fullmatch(player):
            await message.answer(WHITELIST_USAGE[action] + "\n" + WHITELIST_INVALID_NAME)
            return
        try:
            result = await server.whitelist(action, player if action != "list" else None)
        except ServerControlError as error:
            logger.warning("Whitelist operation failed: %s", error)
            await message.answer(WHITELIST_ERRORS.get(error.code, WHITELIST_FAILED))
            return
        if action == "list":
            if not result.players:
                await message.answer(WHITELIST_EMPTY)
                return
            chunk = WHITELIST_HEADER.format(count=len(result.players))
            for name in result.players:
                if len(chunk) + len(name) + 1 > 4000:
                    await message.answer(chunk)
                    chunk = name
                else:
                    chunk += "\n" + name
            await message.answer(chunk)
        else:
            await message.answer(WHITELIST_RESULTS[result.status].format(player=result.players[0]))

    router = Router(name="commands")
    router.message.register(handle_help, CommandStart())
    router.message.register(handle_help, Command("help"))
    router.message.register(handle_server, Command("server_start", "server_stop"))
    router.message.register(handle_whitelist, Command("wl_list", "wl_add", "wl_remove"))
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
