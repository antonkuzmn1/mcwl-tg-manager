"""Offline checks for configuration, routing, and application lifecycle."""

import os
import unittest
from unittest.mock import AsyncMock, patch

from aiogram import Bot
from aiogram.methods import SendMessage
from aiogram.types import Update, User

from mcwl_tg_manager.bot import START_MESSAGE, create_dispatcher, run
from mcwl_tg_manager.config import Settings

TOKEN = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"


class ConfigurationTests(unittest.TestCase):
    def test_valid_token_is_loaded_and_hidden_from_repr(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": TOKEN}, clear=True):
            settings = Settings.from_env()
        self.assertEqual(settings.telegram_bot_token, TOKEN)
        self.assertNotIn(TOKEN, repr(settings))

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
    async def check_message(self, text, chat_type="private"):
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
                await create_dispatcher().feed_update(bot, update)
        finally:
            await bot.session.close()
        return request

    async def test_start_in_private_and_group_chats(self):
        for text, chat_type in (("/start", "private"), ("/start", "group"),
                                ("/start@mcwl_test_bot", "supergroup")):
            with self.subTest(text=text, chat_type=chat_type):
                request = await self.check_message(text, chat_type)
                request.assert_awaited_once()
                method = request.call_args.args[1]
                self.assertIsInstance(method, SendMessage)
                self.assertEqual(method.text, START_MESSAGE)

    async def test_unrelated_messages_and_commands_are_ignored(self):
        for text in ("hello", "/help", "/wl_add Steve", "/start@another_bot"):
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
                                await run(Settings(TOKEN))
                        else:
                            await run(Settings(TOKEN))
                        close.assert_awaited_once()
                        self.assertEqual(polling.call_args.kwargs["allowed_updates"], ["message"])
