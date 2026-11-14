"""Offline tests for the privileged updater; no system service is contacted."""

import importlib.util
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location(
    'update_control', Path(__file__).resolve().parents[1] / 'deploy/update_control.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ControlUpdateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.destination = Path(self.directory.name) / 'server_control.py'
        self.destination.write_bytes(b'old = True\n')
        self.patch = patch.object(module, 'DESTINATION', self.destination)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_valid_source_installed_atomically_without_execution(self):
        source = b'raise RuntimeError("never execute submitted code as root")\n'
        with patch.object(module, 'restart') as restart:
            module.update(source)
        restart.assert_called_once_with()
        self.assertEqual(self.destination.read_bytes(), source)
        self.assertEqual(stat.S_IMODE(self.destination.stat().st_mode), 0o755)
        self.assertEqual(list(self.destination.parent.iterdir()), [self.destination])

    def test_invalid_source_preserves_file_and_service(self):
        for source in (b'', b'x' * (module.MAX_SOURCE + 1), b'def :'):
            with self.subTest(size=len(source)), patch.object(module, 'restart') as restart:
                with self.assertRaises((ValueError, SyntaxError)):
                    module.update(source)
                restart.assert_not_called()
                self.assertEqual(self.destination.read_bytes(), b'old = True\n')

    def test_unchanged_source_checks_health_without_restart(self):
        with patch.object(module, 'restart') as restart, patch.object(module, 'wait_ready') as ready:
            module.update(self.destination.read_bytes())
        ready.assert_called_once_with()
        restart.assert_not_called()

    def test_restart_failure_restores_old_file_and_restarts(self):
        with patch.object(module, 'restart', side_effect=[RuntimeError(), None]) as restart:
            with self.assertRaisesRegex(RuntimeError, 'previous helper restored'):
                module.update(b'new = True\n')
        self.assertEqual(restart.call_count, 2)
        self.assertEqual(self.destination.read_bytes(), b'old = True\n')

    def test_failed_recovery_is_reported(self):
        with patch.object(module, 'restart', side_effect=RuntimeError()):
            with self.assertRaisesRegex(RuntimeError, 'recovery failed'):
                module.update(b'new = True\n')
        self.assertEqual(self.destination.read_bytes(), b'old = True\n')

    def test_arguments_and_nonroot_rejected_before_reading_source(self):
        for argv, uid in ((['updater', 'arbitrary-path'], 0), (['updater'], 1000)):
            with patch.object(module.sys, 'argv', argv), patch.object(module.os, 'geteuid', return_value=uid):
                with self.assertRaises(ValueError):
                    module.main()

    def test_restart_uses_only_fixed_service_and_waits_for_socket(self):
        with patch.object(module.subprocess, 'run') as run, patch.object(module, 'wait_ready') as ready:
            module.restart()
        run.assert_called_once_with(['/usr/bin/systemctl', 'restart', 'mcwl-control.service'],
                                    check=True, timeout=200)
        ready.assert_called_once_with()

    def test_active_service_requires_connectable_socket(self):
        client = Mock()
        client.__enter__ = Mock(return_value=client)
        client.__exit__ = Mock(return_value=False)
        with patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), \
                patch.object(module.socket, 'socket', return_value=client):
            module.wait_ready()
        client.connect.assert_called_once_with(module.SOCKET)

    def test_unready_service_times_out(self):
        with patch.object(module.time, 'monotonic', side_effect=[0, 0, 16]), \
                patch.object(module.time, 'sleep'), \
                patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)):
            with self.assertRaisesRegex(RuntimeError, 'did not become ready'):
                module.wait_ready()

    def test_active_service_with_stale_socket_times_out(self):
        client = Mock()
        client.__enter__ = Mock(return_value=client)
        client.__exit__ = Mock(return_value=False)
        client.connect.side_effect = ConnectionRefusedError()
        with patch.object(module.time, 'monotonic', side_effect=[0, 0, 16]), \
                patch.object(module.time, 'sleep'), \
                patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), \
                patch.object(module.socket, 'socket', return_value=client):
            with self.assertRaisesRegex(RuntimeError, 'did not become ready'):
                module.wait_ready()

    def test_atomic_replace_failure_preserves_old_source(self):
        with patch.object(module.os, 'replace', side_effect=OSError()), \
                patch.object(module, 'restart') as restart:
            with self.assertRaises(OSError):
                module.update(b'new = True\n')
        self.assertEqual(self.destination.read_bytes(), b'old = True\n')
        self.assertEqual(list(self.destination.parent.iterdir()), [self.destination])
        restart.assert_not_called()
