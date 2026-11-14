"""Host-only helper: expose mc lifecycle and readiness, never the full Docker API."""

import asyncio
import json
import os
import re
from contextlib import suppress
from pathlib import Path

SOCKET = Path("/var/lib/mcwl-control/control.sock")
DOCKER = ("/usr/bin/docker", "--host=unix:///var/run/docker.sock",
          "--config=/var/lib/mcwl-control/docker-config")


READY_PATTERN = re.compile(rb'Done \(\d+(?:\.\d+)?s\)! For help, type ["\']help["\']')
ANSI_PATTERN = re.compile(rb"\x1b\[[0-?]*[ -/]*[@-~]")


class ControlError(Exception):
    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


async def kill_cli(process: asyncio.subprocess.Process) -> None:
    with suppress(ProcessLookupError):
        process.kill()
    await process.communicate()


class HostController:
    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.stopping = False

    async def docker(self, *arguments: str, timeout: int = 30) -> str:
        process = await asyncio.create_subprocess_exec(
            *DOCKER, *arguments,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            output, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.CancelledError:
            await kill_cli(process)
            raise
        except asyncio.TimeoutError:
            await kill_cli(process)
            raise ControlError("Docker timed out. The operation may still complete; ask the operator to check its state.") from None
        if process.returncode != 0:
            raise ControlError("Docker could not operate on container mc. Ask the operator to check that it exists and Docker is available.")
        return output.decode("utf-8", errors="replace").strip()

    async def change_state(self, action: str) -> str:
        if action not in ("start", "stop"):
            raise ControlError("Unsupported server action.")
        if self.lock.locked():
            raise ControlError("Another server operation is in progress. Please try again shortly.")
        async with self.lock:
            self.stopping = action == "stop"
            state = await self.docker("inspect", "--format", "{{.State.Status}}", "mc", timeout=10)
            if action == "start" and state == "running":
                return "The server container is already running."
            if action == "stop" and state in ("exited", "created"):
                return "The server container is already stopped."
            if state not in ("running", "exited", "created"):
                raise ControlError("The server container is not in a controllable state. Contact the operator.")
            if action == "start":
                await self.docker("start", "mc")
                return "Server container started. Minecraft may take some time to become ready."
            await self.docker("stop", "--time", "120", "mc", timeout=150)
            return "Server container stopped."

    async def snapshot(self) -> tuple[str, str, str]:
        value = await self.docker(
            "inspect", "--format", "{{.Id}} {{.State.Status}} {{.State.StartedAt}}", "mc", timeout=10
        )
        parts = value.split()
        if (len(parts) != 3 or not re.fullmatch(r"[0-9a-f]{64}", parts[0])
                or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T[0-9:.]+Z", parts[2])):
            raise ControlError("Docker returned invalid container state.")
        return parts[0], parts[1], parts[2]

    async def ready_in_logs(self, started_at: str) -> bool:
        # Stream history from this run only; never expose raw logs or buffer all history.
        process = await asyncio.create_subprocess_exec(
            *DOCKER, "logs", "--since", started_at, "mc",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        try:
            async def scan() -> bool:
                buffer = b""
                while chunk := await process.stdout.read(16384):
                    buffer = ANSI_PATTERN.sub(b"", buffer + chunk)
                    if READY_PATTERN.search(buffer):
                        return True
                    buffer = buffer[-4096:]
                await process.wait()
                if process.returncode != 0:
                    raise ControlError("Cannot read Minecraft startup logs. Contact the operator.")
                return False

            return await asyncio.wait_for(scan(), timeout=15)
        except asyncio.TimeoutError:
            raise ControlError("Reading Minecraft logs timed out. Contact the operator.", "readiness_check_failed") from None
        finally:
            # Killing this read-only CLI does not stop the Minecraft container.
            await kill_cli(process)

    async def wait_until_ready(self, timeout: float = 300, interval: float = 3) -> str:
        async def wait() -> str:
            original = await self.snapshot()
            current = original
            while True:
                if (current[0], current[2]) != (original[0], original[2]):
                    raise ControlError("Minecraft restarted while loading. Run /server_start again.", "readiness_restarted")
                if self.stopping or current[1] != "running":
                    raise ControlError("Minecraft stopped before becoming ready.", "readiness_stopped")
                ready = await self.ready_in_logs(original[2])
                # Re-check after reading: a previous run's marker must never confirm a replacement.
                current = await self.snapshot()
                if (current[0], current[2]) != (original[0], original[2]):
                    raise ControlError("Minecraft restarted while loading. Run /server_start again.", "readiness_restarted")
                if self.stopping or current[1] != "running":
                    raise ControlError("Minecraft stopped before becoming ready.", "readiness_stopped")
                if ready:
                    return "Minecraft is ready."
                await asyncio.sleep(interval)
                current = await self.snapshot()

        try:
            # No lifecycle lock: /server_stop stays available during loading.
            return await asyncio.wait_for(wait(), timeout=timeout)
        except asyncio.TimeoutError:
            raise ControlError("Minecraft did not become ready within five minutes.", "readiness_timeout") from None

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            line = await asyncio.wait_for(reader.readline(), timeout=5)
            if line not in (b"start\n", b"stop\n", b"wait_ready\n"):
                raise ControlError("Unsupported server action.")
            action = line.decode("ascii").strip()
            message = await self.wait_until_ready() if action == "wait_ready" else await self.change_state(action)
            result = {"ok": True, "message": message}
        except (ControlError, OSError, ValueError, asyncio.TimeoutError) as error:
            message = str(error) if isinstance(error, ControlError) else "Server control service is unavailable. Contact the operator."
            result = {"ok": False, "message": message, "code": getattr(error, "code", None)}
        try:
            writer.write(json.dumps(result).encode("utf-8") + b"\n")
            await writer.drain()
        except (OSError, ConnectionError):
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass


async def main() -> None:
    SOCKET.unlink(missing_ok=True)
    controller = HostController()
    server = await asyncio.start_unix_server(controller.handle, path=SOCKET, limit=64)
    os.chmod(SOCKET, 0o660)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
