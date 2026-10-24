import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile
import socket
import os

spec = importlib.util.spec_from_file_location('gather', Path(__file__).resolve().parents[1] / 'scripts/gather.py')
gather = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gather)


class GatherTests(unittest.TestCase):
    def test_profile_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory)
            with patch.object(gather, 'PROFILE', profile):
                self.assertFalse(gather.profile_in_use())
                lock = profile / 'SingletonLock'
                lock.symlink_to(f'{socket.gethostname()}-{os.getpid()}')
                self.assertTrue(gather.profile_in_use())
                with patch.object(gather.os, 'kill', side_effect=ProcessLookupError):
                    self.assertFalse(gather.profile_in_use())
                lock.unlink()
                lock.symlink_to('another-host-123')
                self.assertTrue(gather.profile_in_use())

    def test_login_has_no_debugging_flags(self):
        args = gather.chrome_command('login', 9437)
        self.assertFalse(any('debugging' in arg or 'automation' in arg for arg in args))
        self.assertIn(f'--user-data-dir={gather.PROFILE}', args)

    def test_observe_uses_same_profile_and_loopback(self):
        args = gather.chrome_command('observe', 9437)
        self.assertIn(f'--user-data-dir={gather.PROFILE}', args)
        self.assertIn('--remote-debugging-address=127.0.0.1', args)
        self.assertIn('--remote-debugging-port=9437', args)

    def test_capture_scope(self):
        self.assertTrue(gather.capture_allowed('https://www.toolost.com/releases'))
        for url in ['https://accounts.google.com/', 'https://www.toolost.com/login',
                    'https://toolost.com/auth/callback', 'https://toolost.com.evil.test/',
                    'http://toolost.com/releases', 'about:blank']:
            with self.subTest(url=url):
                self.assertFalse(gather.capture_allowed(url))


if __name__ == '__main__':
    unittest.main()
