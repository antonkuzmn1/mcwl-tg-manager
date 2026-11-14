"""Offline checks for configuration, routing, and application lifecycle."""

import os
import unittest
from unittest.mock import AsyncMock, patch

from aiogram import Bot
from aiogram.methods import SendMessage
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Update, User

from mcwl_tg_manager.bot import create_dispatcher, run
from mcwl_tg_manager.messages import HELP_MESSAGE
from mcwl_tg_manager.config import Settings

TOKEN = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"


class ConfigurationTests(unittest.TestCase):
    def test_valid_token_is_loaded_and_hidden_from_repr(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": TOKEN, "TELEGRAM_ALLOWED_CHAT_IDS": "42, -42"}, clear=True):
            settings = Settings.from_env()
        self.assertEqual(settings.telegram_bot_token, TOKEN)
        self.assertNotIn(TOKEN, repr(settings))

    def test_chat_ids_support_whitespace_duplicates_and_signed_ids(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": TOKEN,
                                     "TELEGRAM_ALLOWED_CHAT_IDS": " 42, -42, -1001234567890, 42 "}, clear=True):
            settings = Settings.from_env()
        self.assertEqual(settings.allowed_chat_ids, frozenset({42, -42, -1001234567890}))

    def test_missing_or_invalid_chat_ids_fail_closed(self):
        for value in (None, "", " ", "42,", ",42", "42,,43", "abc", "1.5", "0", "-0",
                      "42 43", "42,invalid", "4503599627370496", "-4503599627370496"):
            with self.subTest(value=value):
                env = {"TELEGRAM_BOT_TOKEN": TOKEN}
                if value is not None:
                    env["TELEGRAM_ALLOWED_CHAT_IDS"] = value
                with patch.dict(os.environ, env, clear=True):
                    with self.assertRaisesRegex(ValueError, "TELEGRAM_ALLOWED_CHAT_IDS"):
                        Settings.from_env()

    def test_missing_empty_and_invalid_tokens_fail_without_leaking(self):
        for token in ("", "   ", "secret-invalid-token"):
            with self.subTest(token=token):
                with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": token}, clear=True):
                    with self.assertRaises(ValueError) as error:
                        Settings.from_env()
                if token.strip():
                    self.assertNotIn(token, str(error.exception))
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "required"):
                Settings.from_env()


class RoutingTests(unittest.IsolatedAsyncioTestCase):
    async def check_message(self, text, chat_type="private", allowed_chat_ids=frozenset({42, -42})):
        bot = Bot(TOKEN)
        bot._me = User(id=123456789, is_bot=True, first_name="Test", username="mcwl_test_bot")
        request = AsyncMock()
        update = Update.model_validate({
            "update_id": 1,
            "message": {
                "message_id": 1, "date": 0,
                "chat": {"id": 42 if chat_type == "private" else -42, "type": chat_type},
                "from": {"id": 42, "is_bot": False, "first_name": "Tester"},
                "text": text,
                "entities": ([{"type": "bot_command", "offset": 0,
                               "length": len(text.split()[0])}] if text.startswith("/") else []),
            },
        })
        try:
            with patch.object(bot.session, "make_request", request):
                await create_dispatcher(allowed_chat_ids).feed_update(bot, update)
        finally:
            await bot.session.close()
        return request

    async def test_help_and_start_in_private_and_group_chats(self):
        for text, chat_type in (("/start", "private"), ("/start", "group"),
                                ("/start@mcwl_test_bot", "supergroup"), ("/help", "private"),
                                ("/help", "group"), ("/help@mcwl_test_bot", "supergroup")):
            with self.subTest(text=text, chat_type=chat_type):
                request = await self.check_message(text, chat_type)
                request.assert_awaited_once()
                method = request.call_args.args[1]
                self.assertIsInstance(method, SendMessage)
                self.assertEqual(method.text, HELP_MESSAGE)

    async def test_disallowed_chats_never_reach_the_handler(self):
        for chat_type in ("private", "group", "supergroup"):
            with self.subTest(chat_type=chat_type):
                with patch("mcwl_tg_manager.bot.handle_help", new_callable=AsyncMock) as handler:
                    handler.aiogram_flag = {}
                    for text in ("/start", "/help"):
                        request = await self.check_message(text, chat_type, frozenset({999}))
                        request.assert_not_awaited()
                    handler.assert_not_awaited()
                    request.assert_not_awaited()

    async def test_empty_allowlist_denies_all_messages(self):
        request = await self.check_message("/start", allowed_chat_ids=frozenset())
        request.assert_not_awaited()

    async def test_unrelated_messages_and_commands_are_ignored(self):
        for text in ("hello", "/unknown", "/wl_add Steve", "/start@another_bot", "/help@another_bot"):
            with self.subTest(text=text):
                request = await self.check_message(text)
                request.assert_not_awaited()


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_session_closes_after_polling_and_failure(self):
        for failure in (None, RuntimeError("Polling failed")):
            with self.subTest(failure=failure):
                with patch("mcwl_tg_manager.bot.Dispatcher.start_polling", new_callable=AsyncMock) as polling:
                    with patch("aiogram.client.session.aiohttp.AiohttpSession.close", new_callable=AsyncMock) as close:
                        polling.side_effect = failure
                        if failure:
                            with self.assertRaisesRegex(RuntimeError, "Polling failed"):
                                await run(Settings(TOKEN, frozenset({42})))
                        else:
                            await run(Settings(TOKEN, frozenset({42})))
                        close.assert_awaited_once()
                        self.assertEqual(polling.call_args.kwargs["allowed_updates"], ["message"])


class CommandMenuTests(unittest.IsolatedAsyncioTestCase):
    async def test_startup_registers_commands_only_for_allowed_chats(self):
        bot = AsyncMock()
        await create_dispatcher(frozenset({-42, 99})).emit_startup(bot=bot)
        self.assertEqual(bot.set_my_commands.await_count, 2)
        self.assertEqual({call.kwargs["scope"].chat_id for call in bot.set_my_commands.await_args_list}, {-42, 99})
        for call in bot.set_my_commands.await_args_list:
            self.assertEqual([command.command for command in call.args[0]],
                             ["help", "start", "server_start", "server_stop"])
            self.assertTrue(all(command.description for command in call.args[0]))

    async def test_menu_failure_is_logged_and_remaining_chats_are_attempted(self):
        from aiogram.methods import SetMyCommands
        bot = AsyncMock()
        bot.set_my_commands.side_effect = [
            TelegramBadRequest(method=SetMyCommands(commands=[]), message="Chat not found"), True,
        ]
        with self.assertLogs("mcwl_tg_manager.bot", level="WARNING"):
            await create_dispatcher(frozenset({-42, 99})).emit_startup(bot=bot)
        self.assertEqual(bot.set_my_commands.await_count, 2)
