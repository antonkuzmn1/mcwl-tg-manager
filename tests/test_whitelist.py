"""Offline coverage of the narrow whitelist protocol and Telegram handlers."""

import asyncio
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import test_server_commands as command_tests
from mcwl_tg_manager.messages import (
    WHITELIST_EMPTY, WHITELIST_ERRORS, WHITELIST_FAILED, WHITELIST_RESULTS,
    WHITELIST_USAGE, WHITELIST_INVALID_NAME,
)
from mcwl_tg_manager.server import ServerController, ServerControlError, WhitelistResult

spec = importlib.util.spec_from_file_location(
    "whitelist_helper", Path(__file__).resolve().parents[1] / "deploy/server_control.py"
)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class WhitelistProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory(dir="/tmp")
        self.socket = str(Path(self.directory.name) / "control.sock")
        self.host = helper.HostController()
        self.host.docker = AsyncMock()
        self.server = await asyncio.start_unix_server(self.host.handle, path=self.socket, limit=64)
        self.client = ServerController(self.socket)

    async def asyncTearDown(self):
        self.server.close()
        await self.server.wait_closed()
        self.directory.cleanup()

    async def test_list_sorted_and_empty_list(self):
        for output, players in (
            ("There are 2 whitelisted player(s): Steve, Alex", ("Alex", "Steve")),
            ("There are 0 whitelisted player(s): ", ()),
        ):
            with self.subTest(output=output):
                self.host.docker.side_effect = ["running", output]
                self.assertEqual(await self.client.whitelist("list"), WhitelistResult("listed", players))
                self.host.docker.assert_awaited_with("exec", "mc", "rcon-cli", "whitelist", "list", timeout=20)

    async def test_native_empty_list_after_removing_last_player(self):
        self.host.docker.side_effect = [
            "running", "Removed Anton13yo from the whitelist",
            "running", "There are no whitelisted players",
        ]
        self.assertEqual(await self.client.whitelist("remove", "Anton13yo"),
                         WhitelistResult("removed", ("Anton13yo",)))
        self.assertEqual(await self.client.whitelist("list"), WhitelistResult("listed", ()))

    async def test_native_empty_list_with_rcon_formatting(self):
        for output in ("There are no whitelisted players\n",
                       "\x1b[32mThere are no whitelisted players\x1b[0m",
                       "\u00a7aThere are no whitelisted players\u00a7r"):
            with self.subTest(output=output):
                self.host.docker.side_effect = ["running", output]
                self.assertEqual(await self.client.whitelist("list"), WhitelistResult("listed", ()))

    async def test_empty_list_lookalikes_are_not_accepted(self):
        for output in ("", "There are no whitelisted", "There are no whitelisted players: Steve",
                       "There are no whitelisted players\nUnexpected diagnostic",
                       "There are 1 whitelisted player(s):"):
            with self.subTest(output=output):
                self.host.docker.side_effect = ["running", output]
                with self.assertRaises(ServerControlError) as error:
                    await self.client.whitelist("list")
                self.assertEqual(error.exception.code, "whitelist_unexpected_response")

    async def test_add_remove_and_idempotent_results(self):
        for action, output, status in (
            ("add", "Added Steve to the whitelist", "added"),
            ("add", "Player is already whitelisted", "already_listed"),
            ("remove", "Removed Steve from the whitelist", "removed"),
            ("remove", "Player is not whitelisted", "not_listed"),
        ):
            with self.subTest(action=action, status=status):
                self.host.docker.side_effect = ["running", output]
                self.assertEqual(await self.client.whitelist(action, "Steve"), WhitelistResult(status, ("Steve",)))
                self.host.docker.assert_awaited_with("exec", "mc", "rcon-cli", "whitelist", action, "Steve", timeout=20)

    async def test_short_offline_names_and_maximum_length_names_preserve_case(self):
        for name in ("A", "Abc_123456789012"):
            with self.subTest(name=name):
                self.host.docker.side_effect = ["running", f"Added {name} to the whitelist"]
                self.assertEqual((await self.client.whitelist("add", name)).players, (name,))
                self.host.docker.assert_awaited_with("exec", "mc", "rcon-cli", "whitelist", "add", name, timeout=20)

    async def test_color_codes_and_canonical_name_are_supported(self):
        self.host.docker.side_effect = ["running", "\x1b[32mAdded Steve to the whitelist\x1b[0m"]
        self.assertEqual((await self.client.whitelist("add", "steve")).players, ("Steve",))

    async def test_unknown_or_unexpected_replies_never_claim_success(self):
        for output, code in (
            ("That player does not exist", "whitelist_unknown_player"),
            ("Unknown command; private diagnostics", "whitelist_unexpected_response"),
            ("Added SomeoneElse to the whitelist", "whitelist_unexpected_response"),
        ):
            with self.subTest(output=output):
                self.host.docker.side_effect = ["running", output]
                with self.assertRaises(ServerControlError) as error:
                    await self.client.whitelist("add", "Steve")
                self.assertEqual(error.exception.code, code)
                self.assertNotIn("private", str(error.exception))

    async def test_incomplete_player_list_is_rejected(self):
        self.host.docker.side_effect = ["running", "There are 2 whitelisted player(s): Steve"]
        with self.assertRaises(ServerControlError) as error:
            await self.client.whitelist("list")
        self.assertEqual(error.exception.code, "whitelist_unexpected_response")

    async def test_non_running_server_does_not_receive_rcon_commands(self):
        for state in ("exited", "created", "paused", "restarting"):
            with self.subTest(state=state):
                self.host.docker.reset_mock()
                self.host.docker.return_value = state
                with self.assertRaises(ServerControlError) as error:
                    await self.client.whitelist("list")
                self.assertEqual(error.exception.code, "whitelist_not_running")
                self.host.docker.assert_awaited_once()

    async def test_external_start_is_not_blocked_by_a_historical_stop_flag(self):
        self.host.stopping = True
        self.host.docker.side_effect = ["running", "There are 0 whitelisted player(s):"]
        self.assertEqual(await self.client.whitelist("list"), WhitelistResult("listed", ()))

    async def test_busy_helper_and_rcon_failure_release_the_lock(self):
        await self.host.lock.acquire()
        try:
            with self.assertRaises(ServerControlError) as error:
                await self.client.whitelist("list")
            self.assertEqual(error.exception.code, "whitelist_busy")
            self.host.docker.assert_not_awaited()
        finally:
            self.host.lock.release()
        self.host.docker.side_effect = ["running", helper.ControlError("Private password/auth failure")]
        with self.assertRaises(ServerControlError) as error:
            await self.client.whitelist("add", "Steve")
        self.assertEqual(error.exception.code, "whitelist_unavailable")
        self.assertNotIn("Private", str(error.exception))
        self.assertFalse(self.host.lock.locked())

    async def test_names_and_arbitrary_actions_are_rejected_before_io(self):
        for player in ("", "x" * 17, "Steve;op", "Steve\nstop", "@a", "--help", "two names", "n\u0430me"):
            with self.subTest(player=player):
                with self.assertRaises(ValueError):
                    await self.client.whitelist("add", player)
                with self.assertRaises(helper.ControlError):
                    await self.host.whitelist("remove", player)
        with self.assertRaises(ValueError):
            await self.client.whitelist("op", "Steve")
        with self.assertRaises(helper.ControlError):
            await self.host.whitelist("op", "Steve")
        self.host.docker.assert_not_awaited()

    async def test_protocol_cannot_be_used_for_arbitrary_console_commands(self):
        for request in (b"wl_add Steve;op Alex\n", b"wl_list Steve\n", b"wl_add\n", b"wl_op Steve\n"):
            with self.subTest(request=request):
                reader, writer = await asyncio.open_unix_connection(self.socket)
                writer.write(request)
                await writer.drain()
                response = json.loads(await reader.readline())
                self.assertFalse(response["ok"])
                writer.close()
                await writer.wait_closed()
        self.host.docker.assert_not_awaited()

    async def test_large_list_can_cross_the_old_protocol_size_limit(self):
        players = tuple(f"Player{i:05d}" for i in range(1000))
        self.host.docker.side_effect = ["running", "There are 1000 whitelisted player(s): " + ", ".join(players)]
        self.assertEqual((await self.client.whitelist("list")).players, players)

    async def test_invalid_structured_response_is_rejected(self):
        for data in (None, {"status": {}, "players": []}, {"status": "added", "players": []},
                     {"status": "listed", "players": ["bad name"]}):
            with self.subTest(data=data):
                with patch.object(self.client, "_exchange", return_value={"whitelist": data}):
                    with self.assertRaises(ServerControlError):
                        await self.client.whitelist("list")


class WhitelistCommandTests(unittest.IsolatedAsyncioTestCase):
    dispatch = command_tests.ServerCommandTests.dispatch

    async def test_list_and_empty_list(self):
        for players in ((), ("Alex", "Steve")):
            with self.subTest(players=players):
                controller, replies = await self.dispatch("/wl_list", whitelist_result=WhitelistResult("listed", players))
                controller.whitelist.assert_awaited_once_with("list", None)
                self.assertEqual(len(replies), 1)
                if players:
                    self.assertTrue(all(name in replies[0] for name in players))
                else:
                    self.assertEqual(replies, [WHITELIST_EMPTY])

    async def test_add_remove_and_idempotent_replies(self):
        for action, status in (("add", "added"), ("add", "already_listed"),
                               ("remove", "removed"), ("remove", "not_listed")):
            with self.subTest(action=action, status=status):
                controller, replies = await self.dispatch(
                    f"/wl_{action}@mcwl_test_bot Steve", whitelist_result=WhitelistResult(status, ("Steve",))
                )
                controller.whitelist.assert_awaited_once_with(action, "Steve")
                self.assertEqual(replies, [WHITELIST_RESULTS[status].format(player="Steve")])

    async def test_disallowed_chats_and_other_bot_mentions_never_reach_helper(self):
        for text, chat in (("/wl_add Steve", -99), ("/wl_list", -99), ("/wl_remove@other_bot Steve", -42)):
            with self.subTest(text=text, chat=chat):
                controller, replies = await self.dispatch(text, chat_id=chat)
                controller.whitelist.assert_not_awaited()
                self.assertEqual(replies, [])

    async def test_any_member_and_anonymous_sender_in_allowed_chat_can_modify(self):
        for options in ({"sender_id": 999}, {"anonymous": True}, {"sender_id": None}):
            with self.subTest(options=options):
                controller, _ = await self.dispatch("/wl_add Steve", whitelist_result=WhitelistResult("added", ("Steve",)), **options)
                controller.whitelist.assert_awaited_once_with("add", "Steve")

    async def test_missing_or_invalid_arguments_are_rejected(self):
        for text in ("/wl_add", "/wl_remove", "/wl_add Steve other", "/wl_add Steve\nstop",
                     "/wl_remove --help", "/wl_add " + "a" * 17, "/wl_list Steve"):
            with self.subTest(text=text):
                controller, replies = await self.dispatch(text)
                controller.whitelist.assert_not_awaited()
                action = text.split()[0].removeprefix("/wl_")
                self.assertTrue(replies[0].startswith(WHITELIST_USAGE[action]))
                if action != "list":
                    self.assertIn(WHITELIST_INVALID_NAME, replies[0])

    async def test_failures_are_localized_without_leaking_diagnostics(self):
        for code in (None, "whitelist_not_running", "whitelist_unavailable", "whitelist_unknown_player", "whitelist_busy"):
            with self.subTest(code=code):
                with self.assertLogs("mcwl_tg_manager.bot", level="WARNING"):
                    _, replies = await self.dispatch("/wl_add Steve", whitelist_error=ServerControlError("private diagnostics", code))
                self.assertEqual(replies, [WHITELIST_ERRORS.get(code, WHITELIST_FAILED)])
                self.assertNotIn("private", replies[0])

    async def test_long_list_is_split_without_losing_names(self):
        players = tuple(f"Player{i:05d}" for i in range(1000))
        _, replies = await self.dispatch("/wl_list", whitelist_result=WhitelistResult("listed", players))
        self.assertGreater(len(replies), 1)
        self.assertTrue(all(len(reply) <= 4000 for reply in replies))
        self.assertEqual(tuple("\n".join(replies).splitlines()[1:]), players)
