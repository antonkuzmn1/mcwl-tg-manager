"""Offline checks for deployment secret-file handling."""

import importlib.util
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "write_runtime_env", Path(__file__).resolve().parents[1] / "scripts/write_runtime_env.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RuntimeEnvironmentTests(unittest.TestCase):
    def test_file_is_private_and_replaced_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "bot.env"
            destination.write_text("old content")
            with patch.dict(os.environ, {
                "TELEGRAM_BOT_TOKEN": "123:test-token",
                "TELEGRAM_ALLOWED_CHAT_IDS": "-42, 123",
            }, clear=True):
                module.write_runtime_env(destination)
            self.assertEqual(destination.read_text(),
                             "TELEGRAM_BOT_TOKEN=123:test-token\nTELEGRAM_ALLOWED_CHAT_IDS=-42, 123\nTELEGRAM_ADMIN_USER_IDS=\n")
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)
            self.assertEqual(list(Path(directory).iterdir()), [destination])

    def test_admin_ids_are_included_and_multiline_values_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "bot.env"
            env = {"TELEGRAM_BOT_TOKEN": "123:test-token", "TELEGRAM_ALLOWED_CHAT_IDS": "42",
                   "TELEGRAM_ADMIN_USER_IDS": "42,99"}
            with patch.dict(os.environ, env, clear=True):
                module.write_runtime_env(destination)
            self.assertIn("TELEGRAM_ADMIN_USER_IDS=42,99\n", destination.read_text())
            previous = destination.read_text()
            with patch.dict(os.environ, dict(env, TELEGRAM_ADMIN_USER_IDS="42\nINJECTED=value"), clear=True):
                with self.assertRaisesRegex(ValueError, "TELEGRAM_ADMIN_USER_IDS"):
                    module.write_runtime_env(destination)
            self.assertEqual(destination.read_text(), previous)

    def test_invalid_values_do_not_overwrite_existing_file_or_leak(self):
        for value in ("", "secret\nINJECTED=value", "secret\rvalue", None):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                destination = Path(directory) / "bot.env"
                destination.write_text("previous configuration")
                env = {"TELEGRAM_ALLOWED_CHAT_IDS": "42"}
                if value is not None:
                    env["TELEGRAM_BOT_TOKEN"] = value
                with patch.dict(os.environ, env, clear=True):
                    with self.assertRaises(ValueError) as error:
                        module.write_runtime_env(destination)
                self.assertNotIn("secret", str(error.exception))
                self.assertEqual(destination.read_text(), "previous configuration")


class DeploymentFlowTests(unittest.TestCase):
    def run_deploy(self, directory, validation_status=0):
        import subprocess
        import sys

        root = Path(directory)
        binaries = root / "bin"
        binaries.mkdir()
        docker = binaries / "docker"
        docker.write_text('''#!/bin/sh
if [ "$1" = run ]; then
  exit "${VALIDATION_STATUS:-0}"
fi
if [ "$1" = inspect ]; then
  echo 'true 0'
fi
if [ "$1" = compose ]; then
  case "$*" in
    *'ps -q bot'*) echo test-container ;;
  esac
fi
''')
        docker.chmod(0o755)
        for command in ("flock", "sleep"):
            path = binaries / command
            path.write_text("#!/bin/sh\nexit 0\n")
            path.chmod(0o755)
        python = binaries / "python3"
        python.symlink_to(sys.executable)
        env = dict(os.environ, HOME=str(root), PATH=f"{binaries}:{os.environ['PATH']}",
                   MCWL_IMAGE="mcwl-tg-manager:new", TELEGRAM_BOT_TOKEN="123:test-token",
                   TELEGRAM_ALLOWED_CHAT_IDS="42", TELEGRAM_ADMIN_USER_IDS="42", CONTROL_GID="999", VALIDATION_STATUS=str(validation_status))
        return subprocess.run(["bash", "scripts/deploy.sh"], env=env,
                              cwd=Path(__file__).resolve().parents[1],
                              capture_output=True, text=True)

    def test_validation_failure_preserves_current_deployment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "apps/mcwl-tg-manager"
            root.mkdir(parents=True)
            (root / "bot.env").write_text("unchanged")
            (root / "current-image").write_text("old-image")
            result = self.run_deploy(directory, validation_status=1)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((root / "bot.env").read_text(), "unchanged")
            self.assertEqual((root / "current-image").read_text(), "old-image")
            self.assertFalse((root / "previous-image").exists())

    def test_success_backs_up_last_successful_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "apps/mcwl-tg-manager"
            root.mkdir(parents=True)
            (root / "current-image").write_text("old-image")
            (root / "current-compose.yml").write_text("old-compose")
            (root / "current-bot.env").write_text("last-successful-env")
            (root / "bot.env").write_text("failed-attempt-env")
            result = self.run_deploy(directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / "previous-bot.env").read_text(), "last-successful-env")
            self.assertEqual((root / "previous-image").read_text(), "old-image")
            self.assertEqual((root / "current-image").read_text().strip(), "mcwl-tg-manager:new")
            self.assertEqual((root / "current-bot.env").read_text(), (root / "bot.env").read_text())
            self.assertNotIn("test-token", result.stdout + result.stderr)
