"""Manual Chrome login, followed by opt-in Playwright observation on a private profile."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local'
PROFILE = LOCAL / 'chrome-profile'
CHROME = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
URL = 'https://www.toolost.com'


def profile_in_use():
    lock = PROFILE / 'SingletonLock'
    if not lock.is_symlink():
        return lock.exists()
    owner = os.readlink(lock)
    host, separator, pid = owner.rpartition('-')
    if not separator or host != socket.gethostname() or not pid.isdigit():
        return True
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def chrome_command(mode, port):
    args = [str(CHROME), f'--user-data-dir={PROFILE}', '--no-first-run', '--no-default-browser-check']
    if mode == 'observe':
        args += ['--remote-debugging-address=127.0.0.1', f'--remote-debugging-port={port}']
    return [*args, URL]


def capture_allowed(url):
    parsed = urlsplit(url)
    return (parsed.scheme == 'https' and parsed.hostname in {'toolost.com', 'www.toolost.com'}
            and not any(word in parsed.path.lower() for word in ('login', 'signin', 'sign-in', 'auth')))


def capture(page):
    if not capture_allowed(page.url):
        print('Capture refused: not a non-login Too Lost page.', flush=True)
        return
    # Login forms can also appear at the root URL or inside a modal.
    if page.locator('input[type="password"]:visible').count():
        print('Capture refused: visible password input.', flush=True)
        return
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = LOCAL / 'captures' / stamp
    folder.mkdir(parents=True, mode=0o700)
    data = page.evaluate('''() => ({
        url: location.origin + location.pathname,
        title: document.title,
        text: document.body.innerText,
        controls: Array.from(document.querySelectorAll('input,select,textarea,button,a')).map(el => ({
            tag: el.tagName, type: el.getAttribute('type'),
            name: el.getAttribute('name'), id: el.id,
            label: el.getAttribute('aria-label'),
            labels: Array.from(el.labels || []).map(x => x.innerText),
            text: ['INPUT','TEXTAREA'].includes(el.tagName) ? null : el.innerText,
            required: el.required || false, disabled: el.disabled || false,
            accept: el.getAttribute('accept')
        }))
    })''')
    (folder / 'page.json').write_text(json.dumps(data, ensure_ascii=False, indent=2))
    page.screenshot(path=str(folder / 'viewport.png'))
    print(f'Captured locally: {folder}', flush=True)


def observe(process, port):
    from playwright.sync_api import sync_playwright, Error

    capture_request = LOCAL / 'capture.request'
    stop_request = LOCAL / 'stop.request'
    capture_request.unlink(missing_ok=True)
    stop_request.unlink(missing_ok=True)
    deadline = time.monotonic() + 30
    while True:
        if process.poll() is not None:
            raise RuntimeError('Chrome exited before observation started.')
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.5):
                break
        except OSError:
            if time.monotonic() >= deadline:
                raise RuntimeError('Chrome debugging port did not become ready.') from None
            time.sleep(0.2)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f'http://127.0.0.1:{port}')
        print('Observation ready. No automatic captures or account changes.', flush=True)
        print('Capture: .local/capture.request; stop: .local/stop.request.', flush=True)
        try:
            while browser.is_connected() and not stop_request.exists():
                pages = [page for context in browser.contexts for page in context.pages if not page.is_closed()]
                if not pages:
                    break
                if capture_request.exists():
                    capture_request.unlink()
                    capture(pages[-1])
                pages[-1].wait_for_timeout(500)
        except Error:
            if browser.is_connected() and process.poll() is None:
                raise
    print('Observation disconnected.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['login', 'observe'])
    parser.add_argument('--port', type=int, default=9437)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('port must be between 1024 and 65535')
    if not CHROME.is_file():
        parser.error('Google Chrome is not installed in /Applications')
    LOCAL.mkdir(mode=0o700, exist_ok=True)
    LOCAL.chmod(0o700)
    if profile_in_use():
        parser.error('Close Chrome using this project profile before switching modes. Do not delete its lock.')
    if args.mode == 'observe':
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', args.port))
    with (LOCAL / 'chrome.log').open('a') as log:
        process = subprocess.Popen(chrome_command(args.mode, args.port), stdout=log, stderr=log)
        try:
            if args.mode == 'login':
                print('Plain Chrome opened for manual login; no Playwright or debugging connection.', flush=True)
                print('After login, close this Chrome instance before running observe.', flush=True)
                code = process.wait()
                if code:
                    raise RuntimeError(f'Chrome exited with code {code}; see .local/chrome.log')
            else:
                observe(process, args.port)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
