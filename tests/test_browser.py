"""Unit test offline untuk modul browser dan readiness check."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from toolost_uploader.browser import (
    check_and_clean_stale_lock,
    check_auth_identity,
    ensure_cdp_ready,
    find_chrome_binary,
    is_cdp_available,
    launch_chrome,
    resolve_profile_dir,
)


class BrowserModuleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_find_chrome_binary_custom(self):
        dummy = self.root / "chrome"
        dummy.touch(mode=0o755)
        self.assertEqual(find_chrome_binary(dummy), dummy.resolve())
        self.assertIsNone(find_chrome_binary(self.root / "nonexistent"))

    def test_resolve_profile_dir(self):
        pdir = resolve_profile_dir("test-prof", root=self.root)
        self.assertEqual(pdir, self.root / "test-prof")
        self.assertTrue(pdir.is_dir())

    def test_check_and_clean_stale_lock(self):
        pdir = self.root / "profile"
        pdir.mkdir(parents=True)
        # 1. No lock
        locked, msg = check_and_clean_stale_lock(pdir)
        self.assertFalse(locked)

        # 2. Stale symlink lock with dead PID
        dead_pid = 99999999
        lock_file = pdir / "SingletonLock"
        cookie_file = pdir / "SingletonCookie"
        cookie_file.touch()
        target = f"{os.uname().nodename}-{dead_pid}"
        lock_file.symlink_to(target)

        locked, msg = check_and_clean_stale_lock(pdir)
        self.assertFalse(locked)
        self.assertIn("berhasil dibersihkan", msg)
        self.assertFalse(lock_file.exists())
        self.assertFalse(cookie_file.exists())

    def test_is_cdp_available_mock(self):
        with patch("urllib.request.urlopen") as mock_open:
            mock_resp = Mock()
            mock_resp.status = 200
            mock_resp.read.return_value = json.dumps({"Browser": "Chrome/120.0"}).encode("utf-8")
            mock_open.return_value.__enter__.return_value = mock_resp
            self.assertTrue(is_cdp_available("http://127.0.0.1:9437"))

        with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
            self.assertFalse(is_cdp_available("http://127.0.0.1:9437"))

    def test_ensure_cdp_ready_already_up(self):
        with patch("toolost_uploader.browser.is_cdp_available", return_value=True):
            self.assertTrue(ensure_cdp_ready())

    def test_ensure_cdp_ready_boots_and_waits(self):
        side_effects = [False, False, True]
        with patch("toolost_uploader.browser.is_cdp_available", side_effect=side_effects), \
             patch("toolost_uploader.browser.launch_chrome") as mock_launch:
            self.assertTrue(ensure_cdp_ready(timeout=2.0))
            mock_launch.assert_called_once()

    def test_check_auth_identity_authenticated(self):
        mock_page = Mock()
        mock_page.is_closed.return_value = False
        mock_response = Mock()
        mock_response.url = "https://toolost.com/api/auth/me"
        mock_response.status = 200
        mock_response.json.return_value = {"user": {"id": 422512}}

        mock_context = Mock()
        mock_context.pages = [mock_page]
        mock_browser = Mock()
        mock_browser.contexts = [mock_context]

        def fake_goto(*args, **kwargs):
            # Simulasi pemicu listener on_response
            for call in mock_page.on.call_args_list:
                if call.args and call.args[0] == "response":
                    callback = call.args[1]
                    callback(mock_response)

        mock_page.goto.side_effect = fake_goto
        mock_page.url = "https://toolost.com/user-portal/releases/manage/1"

        with patch("playwright.sync_api.sync_playwright") as mock_pw:
            mock_pw.return_value.__enter__.return_value.chromium.connect_over_cdp.return_value = mock_browser
            res = check_auth_identity()
            self.assertEqual(res["status"], "authenticated")
            self.assertEqual(res["account_id"], "422512")


if __name__ == "__main__":
    unittest.main()
