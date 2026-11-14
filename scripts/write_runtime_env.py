"""Atomically write Docker's runtime environment file without logging secrets."""

import os
import sys
import tempfile
from pathlib import Path


def write_runtime_env(destination: Path) -> None:
    values = {}
    for name in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_CHAT_IDS"):
        value = os.environ.get(name, "").strip()
        if not value or any(char in value for char in ("\r", "\n", "\x00")):
            raise ValueError(f"{name} must be a nonempty single-line value.")
        values[name] = value
    descriptor, temporary = tempfile.mkstemp(dir=destination.parent, prefix=".bot-env-")
    try:
        with os.fdopen(descriptor, "w") as output:
            for name, value in values.items():
                output.write(f"{name}={value}\n")
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        write_runtime_env(Path(sys.argv[1]))
    except ValueError as error:
        raise SystemExit(str(error)) from None
