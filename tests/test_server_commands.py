"""Verify both chat and chat authorization before any host-helper request."""

import unittest
from unittest.mock import AsyncMock, patch

from aiogram import Bot
from aiogram.types import Update, User

from mcwl_tg_manager.bot import create_dispatcher
from mcwl_tg_manager.server import ServerControlError

TOKEN = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"


class ServerCommandTests(unittest.IsolatedAsyncioTestCase):
    async def dispatch(self, text, *, chat_id=-42, sender_id=42, anonymous=False, is_bot=False,
                       error=None):
        controller = AsyncMock()
        controller.change_state.return_value = "Operation completed."
        controller.change_state.side_effect = error
        bot = Bot(TOKEN)
        bot._me = User(id=123456789, is_bot=True, first_name="Test", username="mcwl_test_bot")
        message = {"message_id": 1, "date": 0,
                   "chat": {"id": chat_id, "type": "supergroup"}, "text": text,
                   "entities": [{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}]}
        if sender_id is not None:
            message["from"] = {"id": sender_id, "is_bot": is_bot, "first_name": "Tester"}
        if anonymous:
            message["sender_chat"] = {"id": -42, "type": "supergroup"}
        update = Update.model_validate({"update_id": 1, "message": message})
        request = AsyncMock()
        try:
            with patch.object(bot.session, "make_request", request):
                await create_dispatcher(frozenset({-42}), controller).feed_update(bot, update)
        finally:
            await bot.session.close()
        return controller, [call.args[1].text for call in request.call_args_list]

    async def test_authorized_start_and_stop_including_bot_mentions(self):
        for text, action in (("/server_start", "start"), ("/server_stop@mcwl_test_bot", "stop")):
            with self.subTest(text=text):
                controller, replies = await self.dispatch(text)
                controller.change_state.assert_awaited_once_with(action)
                self.assertEqual(replies[-1], "Operation completed.")

    async def test_other_chats_are_silently_ignored(self):
        controller, replies = await self.dispatch("/server_stop", chat_id=-99)
        controller.change_state.assert_not_awaited()
        self.assertEqual(replies, [])

    async def test_chat_members_and_anonymous_senders_need_no_user_allowlist(self):
        for options in ({"sender_id": 99}, {"anonymous": True}, {"sender_id": None}, {"is_bot": True}):
            with self.subTest(options=options):
                controller, replies = await self.dispatch("/server_stop", **options)
                controller.change_state.assert_awaited_once_with("stop")
                self.assertEqual(replies[-1], "Operation completed.")

    async def test_arguments_and_other_bot_mentions_never_reach_docker(self):
        for text in ("/server_start other-container", "/server_stop --force", "/server_start@another_bot"):
            with self.subTest(text=text):
                controller, replies = await self.dispatch(text)
                controller.change_state.assert_not_awaited()
                if "another_bot" not in text:
                    self.assertTrue(replies[0].startswith("Usage:"))

    async def test_docker_failures_are_reported(self):
        controller, replies = await self.dispatch("/server_stop", error=ServerControlError("Docker is unavailable."))
        controller.change_state.assert_awaited_once_with("stop")
        self.assertEqual(replies[-1], "Docker is unavailable.")
