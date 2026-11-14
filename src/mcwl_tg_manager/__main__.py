"""Application entry point."""

import asyncio
import logging

from mcwl_tg_manager.bot import run
from mcwl_tg_manager.config import Settings


def main() -> None:
    try:
        settings = Settings.from_env()
    except ValueError as error:
        raise SystemExit(str(error)) from None
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        asyncio.run(run(settings))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
