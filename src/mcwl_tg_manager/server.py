"""Async client for the narrow, local Minecraft lifecycle helper."""

import asyncio
import json
from typing import Literal


class ServerControlError(Exception):
    """An operator-facing server-control failure."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class ServerController:
    def __init__(self, socket_path: str = "/var/lib/mcwl-control/control.sock", timeout: float = 170) -> None:
        self.socket_path = socket_path
        self.timeout = timeout

    async def change_state(self, action: Literal["start", "stop"]) -> str:
        if action not in ("start", "stop"):
            raise ValueError("Unsupported server action.")
        return await self._request(action, self.timeout)

    async def wait_until_ready(self) -> None:
        await self._request("wait_ready", 330)

    async def _request(self, action: str, timeout: float) -> str:
        writer = None
        try:
            async with asyncio.timeout(timeout):
                reader, writer = await asyncio.open_unix_connection(self.socket_path, limit=4096)
                writer.write(action.encode("ascii") + b"\n")
                await writer.drain()
                result = json.loads(await reader.readline())
                if (not isinstance(result, dict) or type(result.get("ok")) is not bool
                        or not isinstance(result.get("message"), str) or not result["message"]):
                    raise ValueError("Invalid helper response.")
                if result.get("code") is not None and not isinstance(result["code"], str):
                    raise ValueError("Invalid helper response code.")
                if not result["ok"]:
                    raise ServerControlError(result["message"], result.get("code"))
                return result["message"]
        except TimeoutError:
            raise ServerControlError(
                "Server control timed out. The operation may still complete; ask the operator to check its state."
            ) from None
        except (OSError, ValueError):
            raise ServerControlError("Cannot communicate with the server control service. Contact the operator.") from None
        finally:
            if writer is not None:
                writer.close()
                try:
                    await writer.wait_closed()
                except OSError:
                    pass
