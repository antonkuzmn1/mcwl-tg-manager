"""Offline tests for the restricted host helper and its async socket client."""

import asyncio
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from mcwl_tg_manager.server import ServerController, ServerControlError

spec = importlib.util.spec_from_file_location(
    "server_control", Path(__file__).resolve().parents[1] / "deploy/server_control.py"
)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class ServerControllerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory(dir="/tmp")
        self.socket = str(Path(self.directory.name) / "control.sock")
        self.host = helper.HostController()
        self.host.docker = AsyncMock(return_value="exited")
        self.server = await asyncio.start_unix_server(self.host.handle, path=self.socket, limit=64)
        self.client = ServerController(self.socket)

    async def asyncTearDown(self):
        self.server.close()
        await self.server.wait_closed()
        self.directory.cleanup()

    async def test_start_targets_only_mc(self):
        result = await self.client.change_state("start")
        self.assertIn("may take some time", result)
        self.assertEqual(self.host.docker.await_args_list[0].args,
                         ("inspect", "--format", "{{.State.Status}}", "mc"))
        self.assertEqual(self.host.docker.await_args_list[1].args, ("start", "mc"))

    async def test_stop_allows_120_seconds_to_save(self):
        self.host.docker.return_value = "running"
        self.assertEqual(await self.client.change_state("stop"), "Server container stopped.")
        self.host.docker.assert_awaited_with("stop", "--time", "120", "mc", timeout=150)

    async def test_already_running_or_stopped_does_not_change_state(self):
        for state, action, text in (("running", "start", "already running"),
                                    ("exited", "stop", "already stopped"),
                                    ("created", "stop", "already stopped")):
            with self.subTest(state=state):
                self.host.docker.reset_mock()
                self.host.docker.return_value = state
                self.assertIn(text, await self.client.change_state(action))
                self.host.docker.assert_awaited_once()

    async def test_missing_container_or_docker_failure_is_reported(self):
        self.host.docker.side_effect = helper.ControlError("Docker could not operate on container mc.")
        with self.assertRaisesRegex(ServerControlError, "could not operate"):
            await self.client.change_state("start")

    async def test_paused_container_is_not_force_stopped(self):
        self.host.docker.return_value = "paused"
        with self.assertRaisesRegex(ServerControlError, "not in a controllable state"):
            await self.client.change_state("stop")
        self.host.docker.assert_awaited_once()

    async def test_connection_failure(self):
        with self.assertRaisesRegex(ServerControlError, "Cannot communicate"):
            await ServerController(self.socket + ".missing").change_state("start")

    async def test_client_timeout_reports_uncertain_state(self):
        async def delayed_response(*args, **kwargs):
            await asyncio.sleep(0.03)
            return "exited"
        self.host.docker.side_effect = delayed_response
        with self.assertRaisesRegex(ServerControlError, "may still complete"):
            await ServerController(self.socket, timeout=0.005).change_state("start")
        await asyncio.sleep(0.1)

    async def test_concurrent_operation_is_rejected_and_lock_releases(self):
        entered = asyncio.Event()
        release = asyncio.Event()
        async def blocked(*args, **kwargs):
            entered.set()
            await release.wait()
            return "exited"
        self.host.docker.side_effect = blocked
        task = asyncio.create_task(self.client.change_state("start"))
        try:
            await entered.wait()
            with self.assertRaisesRegex(ServerControlError, "in progress"):
                await self.client.change_state("stop")
        finally:
            release.set()
            await task
        self.host.docker.side_effect = None
        await self.client.change_state("start")

    async def test_arbitrary_actions_are_rejected_by_client_and_helper(self):
        with self.assertRaises(ValueError):
            await self.client.change_state("remove")
        reader, writer = await asyncio.open_unix_connection(self.socket)
        writer.write(b"start other-container\n")
        await writer.drain()
        self.assertIn(b'"ok": false', await reader.readline())
        writer.close()
        await writer.wait_closed()
        self.host.docker.assert_not_awaited()


class DockerProcessTests(unittest.IsolatedAsyncioTestCase):
    async def test_fixed_docker_host_and_no_shell(self):
        process = AsyncMock()
        process.returncode = 0
        process.communicate.return_value = (b"running\n", None)
        with patch.object(helper.asyncio, "create_subprocess_exec", return_value=process) as spawn:
            self.assertEqual(await helper.HostController().docker("inspect", "mc"), "running")
        self.assertEqual(spawn.call_args.args, (*helper.DOCKER, "inspect", "mc"))

    async def test_process_error_does_not_expose_output(self):
        process = AsyncMock()
        process.returncode = 1
        process.communicate.return_value = (b"private Docker error", None)
        with patch.object(helper.asyncio, "create_subprocess_exec", return_value=process):
            with self.assertRaises(helper.ControlError) as error:
                await helper.HostController().docker("start", "mc")
        self.assertNotIn("private", str(error.exception))

    async def test_process_timeout_kills_cli_and_reports_uncertainty(self):
        from unittest.mock import Mock
        process = AsyncMock()
        process.kill = Mock()
        process.communicate.side_effect = TimeoutError
        with patch.object(helper.asyncio, "create_subprocess_exec", return_value=process):
            with self.assertRaisesRegex(helper.ControlError, "may still complete"):
                await helper.HostController().docker("stop", "--time", "120", "mc")
        process.kill.assert_called_once()
        process.wait.assert_awaited_once()
