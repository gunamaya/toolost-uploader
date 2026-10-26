"""Pengelolaan proses Google Chrome, profil lokal, dan koneksi CDP."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.parse import urlsplit
import urllib.request

DEFAULT_CDP_PORT = 9437
DEFAULT_CDP_ENDPOINT = f"http://127.0.0.1:{DEFAULT_CDP_PORT}"
DEFAULT_PORTAL_URL = "https://toolost.com/user-portal/releases/manage/1"
DEFAULT_LOGIN_URL = "https://toolost.com/login"


def find_chrome_binary(custom_path: str | Path | None = None) -> Path | None:
    """Temukan lokasi executable Google Chrome."""
    if custom_path:
        p = Path(custom_path).expanduser().resolve()
        if p.is_file() and os.access(p, os.X_OK):
            return p
        return None

    env_path = os.environ.get("CHROME_BIN")
    if env_path:
        p = Path(env_path).expanduser().resolve()
        if p.is_file() and os.access(p, os.X_OK):
            return p

    if sys.platform == "darwin":
        mac_default = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        if mac_default.is_file() and os.access(mac_default, os.X_OK):
            return mac_default

    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        found = shutil.which(name)
        if found:
            p = Path(found).resolve()
            if p.is_file() and os.access(p, os.X_OK):
                return p

    return None


def resolve_profile_dir(alias: str | None = None, root: Path | None = None) -> Path:
    """Tentukan direktori profil browser terisolasi."""
    if alias:
        candidate = Path(alias).expanduser()
        if candidate.is_absolute() or "/" in alias or "\\" in alias:
            candidate.mkdir(parents=True, mode=0o700, exist_ok=True)
            return candidate

    if root is not None:
        base = root
    else:
        # Tentukan base direktori user standar
        data_home = os.environ.get("XDG_DATA_HOME")
        if data_home:
            user_base = Path(data_home) / "toolost-uploader" / "chrome-profiles"
        elif sys.platform == "darwin":
            user_base = Path.home() / "Library" / "Application Support" / "toolost-uploader" / "chrome-profiles"
        else:
            user_base = Path.home() / ".local" / "share" / "toolost-uploader" / "chrome-profiles"

        # Jika direktori profil dengan alias tersebut sudah ada di user_base, gunakan langsung
        if alias and (user_base / alias).is_dir():
            return user_base / alias

        # Cek jika berjalan di repository workspace lokal dengan direktori .local
        repo_local = Path(__file__).resolve().parents[1] / ".local"
        if repo_local.is_dir():
            if not alias or alias == "default":
                return repo_local / "chrome-profile"
            return repo_local / "profiles" / alias

        base = user_base

    target = base / (alias or "default")
    target.mkdir(parents=True, mode=0o700, exist_ok=True)
    return target


def check_and_clean_stale_lock(profile_dir: Path) -> tuple[bool, str]:
    """Periksa apakah profil sedang digunakan; bersihkan stale lock bila PID sudah mati."""
    lock = profile_dir / "SingletonLock"
    if not lock.exists() and not lock.is_symlink():
        return False, "Profil bebas (tidak ada lock)."

    if not lock.is_symlink():
        return True, "Profil memiliki non-symlink lock."

    try:
        owner = os.readlink(lock)
    except OSError:
        return True, "Tidak dapat membaca symlink lock."

    host, separator, pid_str = owner.rpartition("-")
    if not separator or not pid_str.isdigit():
        return True, f"Format lock tidak dikenal: {owner}"

    # Hanya bersihkan jika hostname cocok dengan host saat ini
    if host != socket.gethostname():
        return True, f"Lock dimiliki oleh host lain: {host}"

    pid = int(pid_str)
    try:
        os.kill(pid, 0)
        return True, f"Profil sedang aktif digunakan oleh proses PID {pid}."
    except ProcessLookupError:
        # Proses sudah mati; aman untuk membersihkan stale locks
        try:
            lock.unlink(missing_ok=True)
            (profile_dir / "SingletonCookie").unlink(missing_ok=True)
            (profile_dir / "SingletonSocket").unlink(missing_ok=True)
            return False, f"Stale lock dari PID {pid} yang sudah mati berhasil dibersihkan."
        except OSError as e:
            return True, f"Gagal menghapus stale lock: {e}"
    except PermissionError:
        return True, f"Proses PID {pid} masih berjalan (izin terbatas)."


def is_local_endpoint(endpoint: str) -> bool:
    """Periksa apakah endpoint CDP mengarah ke host loopback lokal.

    Ketika browser berjalan di host lokal yang sama, Playwright dapat mengaktifkan
    is_local=True untuk mengizinkan unggahan berkas audio berukuran besar (>50MB)
    langsung dari filesystem lokal tanpa batasan transfer WebSocket remote.
    """
    try:
        raw = endpoint if "://" in endpoint else f"http://{endpoint}"
        parsed = urlsplit(raw)
        hostname = (parsed.hostname or "").lower()
        if hostname in ("127.0.0.1", "localhost", "::1", "0.0.0.0"):
            return True
        if hostname.startswith("127."):
            return True
    except Exception:
        pass
    return False


def is_cdp_available(endpoint: str = DEFAULT_CDP_ENDPOINT, timeout: float = 1.0) -> bool:
    """Periksa apakah endpoint CDP browser loopback aktif dan merespons."""
    url = f"{endpoint.rstrip('/')}/json/version"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "toolost-readiness-check"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return isinstance(data, dict) and "Browser" in data
    except (URLError, OSError, ValueError, TimeoutError):
        pass
    return False


def launch_chrome(
    profile_dir: Path,
    *,
    mode: str = "cdp",
    port: int = DEFAULT_CDP_PORT,
    chrome_path: str | Path | None = None,
    url: str | None = None,
) -> subprocess.Popen:
    """Jalankan proses Google Chrome dalam mode setup manual atau background CDP."""
    chrome_bin = find_chrome_binary(chrome_path)
    if not chrome_bin:
        raise FileNotFoundError("Google Chrome executable tidak ditemukan di sistem.")

    check_and_clean_stale_lock(profile_dir)

    target_url = url or (DEFAULT_LOGIN_URL if mode == "setup" else DEFAULT_PORTAL_URL)
    args = [
        str(chrome_bin),
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
    ]

    if mode == "cdp":
        args.extend([
            "--remote-debugging-address=127.0.0.1",
            f"--remote-debugging-port={port}",
        ])
        # Background process mandiri
        proc = subprocess.Popen(
            [*args, target_url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return proc

    # Setup mode: interaktif di depan pengguna
    return subprocess.Popen([*args, target_url])


def ensure_cdp_ready(
    endpoint: str = DEFAULT_CDP_ENDPOINT,
    profile_dir: Path | None = None,
    timeout: float = 12.0,
    log=None,
    chrome_path: str | Path | None = None,
) -> bool:
    """Pastikan browser CDP aktif; luncurkan otomatis jika belum menyala."""
    if is_cdp_available(endpoint):
        return True

    u = urlsplit(endpoint)
    port = u.port or DEFAULT_CDP_PORT
    pdir = profile_dir or resolve_profile_dir()

    if log:
        log(f"Browser CDP di port {port} belum aktif; melakukan auto-bootup Chrome...")

    launch_chrome(pdir, mode="cdp", port=port, chrome_path=chrome_path)

    start_time = time.monotonic()
    while time.monotonic() - start_time < timeout:
        if is_cdp_available(endpoint):
            if log:
                log(f"Browser CDP di port {port} berhasil aktif dan siap.")
            return True
        time.sleep(0.3)

    return False


def acquire_active_page(
    browser,
    domain: str = "toolost.com",
    default_url: str | None = None,
    log=None,
):
    """Dapatkan satu tab aktif dari browser CDP untuk menghemat memori.

    1. Periksa apakah sudah ada tab aktif di semua konteks browser.
    2. Prioritaskan tab yang URL-nya mengandung domain target (misal toolost.com).
    3. Jika ada beberapa tab aktif, pilih satu tab utama dan tutup tab lainnya.
    4. Hanya buka tab baru (new_page) jika tidak ada tab aktif sama sekali.
    """
    def _is_closed(p) -> bool:
        try:
            fn = getattr(p, "is_closed", None)
            return fn() if callable(fn) else bool(fn)
        except Exception:
            return False

    context = browser.contexts[0] if getattr(browser, "contexts", None) else browser.new_context()
    all_pages = [
        p for ctx in getattr(browser, "contexts", [])
        for p in getattr(ctx, "pages", [])
        if not _is_closed(p)
    ]

    target_page = None
    if all_pages:
        matching = []
        for p in all_pages:
            p_url = getattr(p, "url", "") or ""
            if domain in urlsplit(p_url).netloc or domain in p_url:
                matching.append(p)

        if matching:
            # Prioritaskan tab yang sudah berada di portal/uploader rilis
            portal_matches = [
                p for p in matching
                if any(k in (getattr(p, "url", "") or "") for k in ("/user-portal", "/uploader"))
            ]
            target_page = portal_matches[0] if portal_matches else matching[0]
        else:
            target_page = all_pages[0]

        # Tutup tab lainnya yang tidak digunakan untuk menghemat konsumsi memori
        for p in all_pages:
            if p is not target_page:
                try:
                    p_url = getattr(p, "url", "") or ""
                    if log:
                        log(f"Menutup tab redundan ({p_url}) untuk menghemat memori...")
                    p.close()
                except Exception:
                    pass
    else:
        if log:
            log("Tidak ada tab aktif; membuka tab baru...")
        target_page = context.new_page()

    if default_url:
        p_url = getattr(target_page, "url", "") or ""
        if domain not in p_url:
            try:
                target_page.goto(default_url, wait_until="domcontentloaded")
            except Exception:
                pass

    return target_page


def check_auth_identity(endpoint: str = DEFAULT_CDP_ENDPOINT, timeout: float = 15.0) -> dict:
    """Periksa status autentikasi aktif pada browser CDP Too Lost dengan mengamati navigasi portal."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(endpoint, is_local=is_local_endpoint(endpoint))
            try:
                page = acquire_active_page(browser, domain="toolost.com")

                user_ids = []
                http_statuses = []

                def on_response(r):
                    u = urlsplit(r.url)
                    if u.scheme == "https" and u.netloc in ("toolost.com", "www.toolost.com") and u.path == "/api/auth/me":
                        http_statuses.append(r.status)
                        if r.status == 200:
                            try:
                                d = r.json()
                                uid = d.get("user", {}).get("id") or d.get("id")
                                if uid is not None:
                                    user_ids.append(str(uid))
                            except Exception:
                                pass

                page.on("response", on_response)
                try:
                    page.goto(DEFAULT_PORTAL_URL, wait_until="domcontentloaded", timeout=timeout * 1000)
                    start_wait = time.monotonic()
                    while time.monotonic() - start_wait < 6.0:
                        if user_ids or any(s in (401, 403) for s in http_statuses):
                            break
                        page.wait_for_timeout(250)
                finally:
                    page.remove_listener("response", on_response)

                u = urlsplit(page.url)
                if any(x in u.path.lower() for x in ("login", "signin", "auth")):
                    return {"status": "unauthorized", "http_code": 401}

                if user_ids:
                    return {"status": "authenticated", "account_id": user_ids[0]}
                if 401 in http_statuses:
                    return {"status": "unauthorized", "http_code": 401}
                return {"status": "unknown", "http_statuses": http_statuses}
            finally:
                browser.close()
    except Exception as e:
        return {"status": "error", "message": type(e).__name__}
