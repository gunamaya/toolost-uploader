"""Unit test offline untuk modul browser dan readiness check."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from toolost_uploader.browser import (
    acquire_active_page,
    check_and_clean_stale_lock,
    check_auth_identity,
    ensure_cdp_ready,
    find_chrome_binary,
    is_cdp_available,
    is_local_endpoint,
    launch_chrome,
    resolve_profile_dir,
)


class BrowserModuleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_is_local_endpoint(self):
        self.assertTrue(is_local_endpoint("http://127.0.0.1:9437"))
        self.assertTrue(is_local_endpoint("http://localhost:9222"))
        self.assertTrue(is_local_endpoint("127.0.0.1:9437"))
        self.assertTrue(is_local_endpoint("http://[::1]:9437"))
        self.assertFalse(is_local_endpoint("http://192.168.1.100:9222"))
        self.assertFalse(is_local_endpoint("http://remote-cdp.internal:9222"))

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

    def test_acquire_active_page_reuses_single_active_tab(self):
        mock_page = Mock()
        mock_page.url = "https://toolost.com/user-portal/releases/manage/1"
        mock_page.is_closed.return_value = False

        mock_context = Mock()
        mock_context.pages = [mock_page]
        mock_browser = Mock()
        mock_browser.contexts = [mock_context]

        page = acquire_active_page(mock_browser, domain="toolost.com")
        self.assertIs(page, mock_page)
        mock_context.new_page.assert_not_called()
        mock_page.close.assert_not_called()

    def test_acquire_active_page_multiple_tabs_closes_redundant(self):
        p1 = Mock()
        p1.url = "https://toolost.com/user-portal/releases/manage/1"
        p1.is_closed.return_value = False

        p2 = Mock()
        p2.url = "https://toolost.com/uploader/edit/12345"
        p2.is_closed.return_value = False

        p3 = Mock()
        p3.url = "about:blank"
        p3.is_closed.return_value = False

        mock_context = Mock()
        mock_context.pages = [p1, p2, p3]
        mock_browser = Mock()
        mock_browser.contexts = [mock_context]

        selected = acquire_active_page(mock_browser, domain="toolost.com")
        self.assertIs(selected, p1)
        # Tab lain harus ditutup untuk menghemat memori
        p2.close.assert_called_once()
        p3.close.assert_called_once()
        p1.close.assert_not_called()
        mock_context.new_page.assert_not_called()

    def test_acquire_active_page_reuses_non_domain_tab_when_no_match(self):
        p1 = Mock()
        p1.url = "about:blank"
        p1.is_closed.return_value = False

        p2 = Mock()
        p2.url = "https://google.com"
        p2.is_closed.return_value = False

        mock_context = Mock()
        mock_context.pages = [p1, p2]
        mock_browser = Mock()
        mock_browser.contexts = [mock_context]

        selected = acquire_active_page(mock_browser, domain="toolost.com", default_url="https://toolost.com/portal")
        self.assertIs(selected, p1)
        # Tab kedua ditutup
        p2.close.assert_called_once()
        p1.close.assert_not_called()
        # Tab pertama diarahkan ke default_url
        p1.goto.assert_called_once_with("https://toolost.com/portal", wait_until="domcontentloaded")
        mock_context.new_page.assert_not_called()

    def test_acquire_active_page_opens_new_tab_only_when_empty(self):
        new_tab = Mock()
        new_tab.url = ""
        mock_context = Mock()
        mock_context.pages = []
        mock_context.new_page.return_value = new_tab
        mock_browser = Mock()
        mock_browser.contexts = [mock_context]

        selected = acquire_active_page(mock_browser, domain="toolost.com", default_url="https://toolost.com/portal")
        self.assertIs(selected, new_tab)
        mock_context.new_page.assert_called_once()
        new_tab.goto.assert_called_once_with("https://toolost.com/portal", wait_until="domcontentloaded")


if __name__ == "__main__":
    unittest.main()
