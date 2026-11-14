"""Host-only helper: expose start/stop for mc, never the full Docker API."""

import asyncio
import json
import os
from pathlib import Path

SOCKET = Path("/var/lib/mcwl-control/control.sock")
DOCKER = ("/usr/bin/docker", "--host=unix:///var/run/docker.sock",
          "--config=/var/lib/mcwl-control/docker-config")


class ControlError(Exception):
    pass


class HostController:
    def __init__(self) -> None:
        self.lock = asyncio.Lock()

    async def docker(self, *arguments: str, timeout: int = 30) -> str:
        process = await asyncio.create_subprocess_exec(
            *DOCKER, *arguments,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            output, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except TimeoutError:
            process.kill()
            await process.wait()
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

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            line = await asyncio.wait_for(reader.readline(), timeout=5)
            if line not in (b"start\n", b"stop\n"):
                raise ControlError("Unsupported server action.")
            message = await self.change_state(line.decode("ascii").strip())
            result = {"ok": True, "message": message}
        except (ControlError, OSError, ValueError, TimeoutError) as error:
            message = str(error) if isinstance(error, ControlError) else "Server control service is unavailable. Contact the operator."
            result = {"ok": False, "message": message}
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
