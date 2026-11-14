#!/usr/bin/python3 -I
"""Root-installed updater: accept helper source on stdin, never a path or command."""

import fcntl
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

DESTINATION = Path('/opt/mcwl-control/server_control.py')
SOCKET = '/var/lib/mcwl-control/control.sock'
MAX_SOURCE = 1024 * 1024


def replace_file(destination: Path, source: bytes) -> None:
    descriptor, name = tempfile.mkstemp(prefix='.helper-', dir=destination.parent)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(source)
            output.flush()
            os.fchmod(output.fileno(), 0o755)
            os.fsync(output.fileno())
        os.replace(name, destination)
    finally:
        Path(name).unlink(missing_ok=True)


def wait_ready() -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        active = subprocess.run(
            ['/usr/bin/systemctl', 'is-active', '--quiet', 'mcwl-control.service'],
            check=False, timeout=5,
        )
        if active.returncode == 0:
            try:
                with socket.socket(socket.AF_UNIX) as client:
                    client.settimeout(1)
                    client.connect(SOCKET)
                return
            except OSError:
                pass
        time.sleep(0.5)
    raise RuntimeError('Helper did not become ready.')


def restart() -> None:
    subprocess.run(['/usr/bin/systemctl', 'restart', 'mcwl-control.service'],
                   check=True, timeout=200)
    wait_ready()


def update(source: bytes) -> None:
    if not source or len(source) > MAX_SOURCE:
        raise ValueError('Helper source must be nonempty and at most 1 MiB.')
    # Compile without executing any submitted code, including imports.
    compile(source, str(DESTINATION), 'exec')
    previous = DESTINATION.read_bytes()
    if previous == source:
        wait_ready()
        print('Host helper unchanged and ready.')
        return
    replace_file(DESTINATION, source)
    try:
        restart()
    except Exception:
        replace_file(DESTINATION, previous)
        try:
            restart()
        except Exception:
            raise RuntimeError('Helper update and recovery failed; inspect mcwl-control on the VM.') from None
        raise RuntimeError('Helper update failed; previous helper restored.') from None
    print('Host helper updated and ready.')


def main() -> None:
    if len(sys.argv) != 1 or os.geteuid() != 0:
        raise ValueError('Run the installed updater as root without arguments.')
    # Fixed root-owned directory; serialize even calls made outside the pipeline.
    with open('/opt/mcwl-control/update.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        update(sys.stdin.buffer.read(MAX_SOURCE + 1))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Do not echo submitted source or arbitrary subprocess diagnostics.
        print('Host helper update failed. Inspect the service and installed helper on the VM.', file=sys.stderr)
        sys.exit(1)
