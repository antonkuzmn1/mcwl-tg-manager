"""Async client for the narrow, local Minecraft control helper."""

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Literal


PLAYER_NAME = re.compile(r"[A-Za-z0-9_]{1,16}")


@dataclass(frozen=True)
class WhitelistResult:
    status: str
    players: tuple[str, ...]


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

    async def whitelist(self, action: Literal["list", "add", "remove"], player: str | None = None) -> WhitelistResult:
        if action not in ("list", "add", "remove"):
            raise ValueError("Unsupported whitelist action.")
        if action == "list":
            if player is not None:
                raise ValueError("Whitelist list does not accept a player.")
        elif not isinstance(player, str) or not PLAYER_NAME.fullmatch(player):
            raise ValueError("Invalid Minecraft player name.")
        request = f"wl_{action}" + (f" {player}" if player is not None else "")
        response = await self._exchange(request, 40)
        data = response.get("whitelist")
        expected = {"list": {"listed"}, "add": {"added", "already_listed"}, "remove": {"removed", "not_listed"}}
        if (not isinstance(data, dict) or not isinstance(data.get("status"), str)
                or data["status"] not in expected[action]
                or not isinstance(data.get("players"), list)
                or any(not isinstance(name, str) or not PLAYER_NAME.fullmatch(name) for name in data["players"])):
            raise ServerControlError("Invalid whitelist response.", "whitelist_unexpected_response")
        if action != "list" and (len(data["players"]) != 1 or data["players"][0].casefold() != player.casefold()):
            raise ServerControlError("Invalid whitelist response.", "whitelist_unexpected_response")
        return WhitelistResult(data["status"], tuple(data["players"]))

    async def _request(self, action: str, timeout: float) -> str:
        return (await self._exchange(action, timeout))["message"]

    async def _exchange(self, action: str, timeout: float) -> dict:
        writer = None
        try:
            async with asyncio.timeout(timeout):
                reader, writer = await asyncio.open_unix_connection(self.socket_path, limit=1048576)
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
                return result
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
