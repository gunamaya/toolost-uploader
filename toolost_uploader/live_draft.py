"""Executor Playwright draft-only bounded; tidak menyediakan aksi Publish."""

import re
from pathlib import Path
from urllib.parse import urlsplit

from .storage import _atomic_write, profile
from .validation import file_reference, load_manifest, validate_manifest


class DraftError(Exception):
    pass


def preflight(path):
    path = Path(path).absolute()
    manifest = load_manifest(path)
    validate_manifest(manifest, path.parent)
    required = {'schema_version', 'release_id', 'release_type', 'title', 'release_date', 'artwork', 'tracks'}
    if set(manifest) != required or manifest['release_type'] != 'single' or len(manifest['tracks']) != 1:
        raise DraftError('unsupported_live_manifest')
    if set(manifest['tracks'][0]) != {'track_id', 'title', 'audio', 'ai_assisted'}:
        raise DraftError('unsupported_live_track_fields')
    # Tanggal wajib manifest belum diterapkan: hanya smoke draft dengan opt-in terpisah.
    return manifest, path.parent


class DraftUI:
    def __init__(self, page, manifest, base, expected_account, record):
        self.page, self.manifest, self.base = page, manifest, base
        self.expected_account, self.record = expected_account, record
        self.remote_id = None

    def guard(self):
        u = urlsplit(self.page.url)
        if u.scheme != 'https' or u.netloc != 'toolost.com' or any(x in u.path.lower() for x in ('login', 'signin', 'auth')):
            raise DraftError('login_required_or_wrong_origin')
        if self.page.locator('input[type=password]:visible,input[autocomplete=one-time-code]:visible').count():
            raise DraftError('login_required')

    def action(self, name, operation):
        self.guard()
        if self.remote_id and urlsplit(self.page.url).path != '/uploader/edit/' + self.remote_id:
            raise DraftError('draft_target_changed')
        self.record(name, 'unknown', self.remote_id)
        operation()
        self.record(name, 'observed', self.remote_id)

    def verify_account(self):
        self.guard()
        if not urlsplit(self.page.url).path.startswith('/user-portal'):
            raise DraftError('start_from_portal_required')
        if self.page.locator('[role=dialog]:visible,[aria-modal=true]:visible').count():
            raise DraftError('existing_dialog_requires_review')
        ids = []
        def response(r):
            u = urlsplit(r.url)
            if u.netloc == 'toolost.com' and u.path == '/api/auth/me' and r.status == 200:
                try:
                    value = r.json().get('user', {}).get('id')
                    if type(value) is int:
                        ids.append(str(value))
                except Exception:
                    pass
        self.page.on('response', response)
        try:
            self.page.goto('https://toolost.com/user-portal/releases/manage/1', wait_until='domcontentloaded', timeout=30000)
            self.page.get_by_role('button', name='Create New Release', exact=True).wait_for(state='visible', timeout=30000)
            for _ in range(20):
                if ids:
                    break
                self.page.wait_for_timeout(250)
            self.guard()
            if not ids or any(value != self.expected_account for value in ids):
                raise DraftError('account_mismatch_or_unobserved')
        finally:
            self.page.remove_listener('response', response)
            ids.clear()

    def create(self):
        page = self.page
        page.locator('a[href="/uploader"]:visible').click()
        dialog = page.get_by_role('dialog').filter(has=page.get_by_role('heading', name='Select release type', exact=True))
        dialog.wait_for(state='visible', timeout=30000)
        dialog.get_by_role('button', name=re.compile(r'^Single\s+1–3 tracks$')).click()
        dialog.get_by_role('button', name='Continue', exact=True).click()
        name_dialog = page.get_by_role('dialog').filter(has_text='Name your release')
        name_dialog.get_by_role('textbox').fill(self.manifest['title'])
        name_dialog.get_by_role('button', name='Create Release', exact=True).click()
        page.wait_for_url(re.compile(r'https://toolost\.com/uploader/edit/[0-9]+$'), timeout=30000)
        self.remote_id = urlsplit(page.url).path.rsplit('/', 1)[1]
        page.get_by_role('button', name='Artwork', exact=True).wait_for(state='visible')

    def asset(self, reference):
        file_reference(reference, self.base)
        path = Path(reference['path'])
        return str(path if path.is_absolute() else self.base / path)

    def artwork(self):
        page = self.page
        page.get_by_role('button', name='Artwork', exact=True).click()
        page.get_by_role('button', name='Upload Artwork', exact=True).click()
        dialog = page.get_by_role('dialog').filter(has_text=re.compile('Upload artwork', re.I))
        with page.expect_file_chooser(timeout=10000) as chooser:
            dialog.get_by_text('browse files', exact=True).click()
        chooser.value.set_files(self.asset(self.manifest['artwork']))
        page.get_by_text('Artwork selected', exact=True).wait_for(state='visible', timeout=180000)

    def audio(self):
        page = self.page
        page.get_by_role('button', name='Manage Tracks', exact=True).click()
        if page.locator('.track-item:visible').count() != 0:
            raise DraftError('unexpected_existing_tracks')
        page.get_by_role('button', name='Upload tracks', exact=True).click()
        dialog = page.get_by_role('dialog').filter(has_text='browse files')
        with page.expect_file_chooser(timeout=10000) as chooser:
            dialog.get_by_text('browse files', exact=True).click()
        chooser.value.set_files(self.asset(self.manifest['tracks'][0]['audio']))
        dialog.get_by_role('button', name=re.compile(r'^Upload\s+1\s+file$')).click()
        page.locator('.track-item:visible').first.wait_for(state='visible', timeout=240000)
        if page.locator('.track-item:visible').count() != 1:
            raise DraftError('track_identity_ambiguous')
        page.get_by_role('dialog').filter(has_text='browse files').wait_for(state='hidden', timeout=30000)

    def editor(self):
        self.page.locator('.track-item:visible').get_by_role('button', name='Edit', exact=True).click()
        self.page.get_by_role('textbox', name='Track name', exact=True).wait_for(state='visible')

    def ai_switch(self):
        # Scope by the observed AI label, never the first unnamed switch on the page.
        section = self.page.get_by_text('AI-assisted content', exact=True).locator('..')
        switches = section.get_by_role('switch').filter(visible=True)
        if switches.count() != 1:
            raise DraftError('ai_selector_unverified')
        return switches

    def metadata(self):
        track = self.manifest['tracks'][0]
        self.editor()
        self.page.get_by_role('textbox', name='Track name', exact=True).fill(track['title'])
        switch = self.ai_switch()
        value = switch.get_attribute('aria-checked')
        if value not in ('true', 'false'):
            raise DraftError('ai_semantics_unavailable')
        if (value == 'true') != track['ai_assisted']:
            switch.click()
        if switch.get_attribute('aria-checked') != str(track['ai_assisted']).lower():
            raise DraftError('ai_readback_mismatch')
        self.page.get_by_role('button', name='Done', exact=True).click()

    def save(self):
        page = self.page
        page.get_by_role('button', name='Save Changes', exact=True).click()
        dialog = page.get_by_role('dialog').filter(has=page.get_by_role('button', name='Save', exact=True))
        # Either confirmation or navigation; never retry Save Changes.
        for _ in range(60):
            if dialog.is_visible():
                dialog.get_by_role('button', name='Save', exact=True).click()
                break
            if '/releases/manage/' in page.url:
                return
            page.wait_for_timeout(250)
        else:
            raise DraftError('save_outcome_unknown')
        page.get_by_text('Saving your release', exact=False).wait_for(state='hidden', timeout=60000)
        if page.get_by_text('Something went wrong while saving your release.', exact=False).is_visible():
            raise DraftError('save_outcome_unknown')

    def readback(self):
        page = self.page
        page.goto('https://toolost.com/uploader/edit/' + self.remote_id, wait_until='domcontentloaded', timeout=30000)
        self.guard()
        page.get_by_role('heading', name=self.manifest['title'], exact=True).wait_for(state='visible', timeout=30000)
        title = page.get_by_role('textbox', name='Single name', exact=True)
        page.get_by_role('button', name='Basic Information', exact=True).click()
        title.wait_for(state='visible')
        if title.input_value() != self.manifest['title']:
            raise DraftError('release_title_or_type_mismatch')
        page.get_by_role('button', name='Artwork', exact=True).click()
        page.get_by_text('Artwork selected', exact=True).wait_for(state='visible', timeout=30000)
        page.get_by_role('button', name='Manage Tracks', exact=True).click()
        page.locator('.track-item:visible').first.wait_for(state='visible')
        if page.locator('.track-item:visible').count() != 1:
            raise DraftError('track_readback_mismatch')
        self.editor()
        track = self.manifest['tracks'][0]
        if page.get_by_role('textbox', name='Track name', exact=True).input_value() != track['title']:
            raise DraftError('title_readback_mismatch')
        if self.ai_switch().get_attribute('aria-checked') != str(track['ai_assisted']).lower():
            raise DraftError('ai_readback_mismatch')
        page.get_by_role('button', name='Done', exact=True).click()


def run_steps(ui):
    ui.verify_account()
    for name in ('create', 'artwork', 'audio', 'metadata', 'save'):
        ui.action(name, getattr(ui, name))
    ui.readback()
    ui.record('readback', 'verified_subset', ui.remote_id)


def execute(path, *, alias, expected_account, endpoint, approve_draft, accept_ui_date, root=None):
    if approve_draft is not True or accept_ui_date is not True:
        raise DraftError('confirmation_required')
    if not re.fullmatch(r'[1-9][0-9]*', expected_account):
        raise DraftError('invalid_expected_account')
    if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{1,5}', endpoint) or not 1024 <= int(endpoint.rsplit(':', 1)[1]) <= 65535:
        raise DraftError('loopback_endpoint_required')
    manifest, base = preflight(path)
    from playwright.sync_api import sync_playwright
    with profile(alias, root=root) as session:
        checkpoint = session.create_checkpoint(manifest, base)
        events = []
        def record(operation, outcome, remote_id):
            events.append(dict(operation=operation, outcome=outcome))
            _atomic_write(session.directory, manifest['release_id'] + '.live.json',
                          dict(run_id=checkpoint['run_id'], remote_draft_id=remote_id, events=events))
        record('preflight', 'validated', None)
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(endpoint)
            pages = [page for context in browser.contexts for page in context.pages
                     if not page.is_closed() and urlsplit(page.url).scheme == 'https'
                     and urlsplit(page.url).netloc == 'toolost.com']
            if len(pages) != 1:
                raise DraftError('ambiguous_browser_target')
            ui = DraftUI(pages[0], manifest, base, expected_account, record)
            run_steps(ui)
        return dict(status='draft_saved_subset', run_id=checkpoint['run_id'], draft_id=ui.remote_id,
                    warnings=['Tanggal UI diwarisi; bukan release_date manifest terverifikasi.',
                              'Remote track identity dan rights/services belum diverifikasi; bukan siap distribusi.'])
