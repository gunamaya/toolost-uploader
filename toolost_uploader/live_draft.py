"""Executor Playwright draft-only bounded; tidak menyediakan aksi Publish."""

import re
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit

from .storage import profile
from .live_journal import DraftError, LiveJournal
from .validation import file_reference, load_manifest, validate_manifest, validate_manifest_structure


def preflight(path, *, verify_assets=True):
    path = Path(path).absolute()
    manifest = load_manifest(path)
    if verify_assets:
        validate_manifest(manifest, path.parent)
    else:
        validate_manifest_structure(manifest)
    required = {'schema_version', 'release_id', 'release_type', 'title', 'release_date', 'artwork', 'tracks'}
    if set(manifest) != required or manifest['release_type'] != 'single' or len(manifest['tracks']) != 1:
        raise DraftError('unsupported_live_manifest')
    if set(manifest['tracks'][0]) != {'track_id', 'title', 'audio', 'ai_assisted'}:
        raise DraftError('unsupported_live_track_fields')
    # Tanggal wajib manifest belum diterapkan: hanya smoke draft dengan opt-in terpisah.
    return manifest, path.parent


class DraftUI:
    def __init__(self, page, manifest, base, expected_account, record):
        self.page, self.manifest, self.base = page, deepcopy(manifest), base
        self.expected_account, self.record = expected_account, record
        self.remote_id = None
        self.identity_verified = False
        self.identity_changed = False
        self.attempted = set()
        self.read_only = False
        self.page.context.on('response', self.observe_account)
        self.page.context.route('https://toolost.com/**', self.guard_request)

    def guard_request(self, route):
        # Tidak membaca header/body. Guard ini juga berlaku selama auto-wait klik.
        if route.request.method not in ('GET', 'HEAD', 'OPTIONS'):
            u = urlsplit(self.page.url)
            if (self.read_only or not self.identity_verified or self.identity_changed or self.page.is_closed() or
                    u.scheme != 'https' or u.netloc != 'toolost.com' or
                    any(x in u.path.lower() for x in ('login', 'signin', 'auth')) or
                    (self.remote_id and u.path != '/uploader/edit/' + self.remote_id)):
                route.abort()
                return
        route.continue_()

    def observe_account(self, response):
        u = urlsplit(response.url)
        if u.scheme != 'https' or u.netloc != 'toolost.com' or u.path != '/api/auth/me':
            return
        try:
            value = response.json().get('user', {}).get('id') if response.status == 200 else None
        except Exception:
            value = None
        if type(value) is not int or str(value) != self.expected_account:
            self.identity_changed = True

    def close(self):
        try:
            self.page.context.unroute('https://toolost.com/**', self.guard_request)
        finally:
            self.page.context.remove_listener('response', self.observe_account)

    def guard_identity(self):
        self.guard()
        if not self.identity_verified or self.identity_changed:
            raise DraftError('identity_preflight_required_or_changed')

    def guard_target(self):
        self.guard_identity()
        if self.remote_id and urlsplit(self.page.url).path != '/uploader/edit/' + self.remote_id:
            raise DraftError('draft_target_changed')

    def click(self, locator):
        self.guard_target()
        locator.click()

    def guard(self):
        if self.page.is_closed():
            raise DraftError('browser_target_closed')
        u = urlsplit(self.page.url)
        if u.scheme != 'https' or u.netloc != 'toolost.com' or any(x in u.path.lower() for x in ('login', 'signin', 'auth')):
            raise DraftError('login_required_or_wrong_origin')
        if self.page.locator('input[type=password]:visible,input[autocomplete=one-time-code]:visible').count():
            raise DraftError('login_required')

    def action(self, name, operation):
        self.guard_identity()
        if self.remote_id and urlsplit(self.page.url).path != '/uploader/edit/' + self.remote_id:
            raise DraftError('draft_target_changed')
        if name in self.attempted:
            raise DraftError('duplicate_action_requires_reconciliation')
        self.attempted.add(name)
        self.record(name, 'unknown', self.remote_id)
        operation()
        if name == 'save':
            self.guard_identity()
        else:
            self.guard_target()
        self.record(name, 'observed', self.remote_id)

    def verify_account(self):
        self.identity_verified = False
        self.guard()
        if not urlsplit(self.page.url).path.startswith('/user-portal'):
            raise DraftError('start_from_portal_required')
        if self.page.locator('[role=dialog]:visible,[aria-modal=true]:visible').count():
            raise DraftError('existing_dialog_requires_review')
        ids = []
        def response(r):
            u = urlsplit(r.url)
            if u.scheme == 'https' and u.netloc == 'toolost.com' and u.path == '/api/auth/me' and r.status == 200:
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
            if not ids or any(value != self.expected_account for value in ids) or self.identity_changed:
                raise DraftError('account_mismatch_or_unobserved')
            self.identity_verified = True
        finally:
            self.page.remove_listener('response', response)
            ids.clear()

    def create(self):
        page = self.page
        self.click(page.locator('a[href="/uploader"]:visible'))
        dialog = page.get_by_role('dialog').filter(has=page.get_by_role('heading', name='Select release type', exact=True))
        dialog.wait_for(state='visible', timeout=30000)
        self.click(dialog.get_by_role('button', name=re.compile(r'^Single\s+1–3 tracks$')))
        self.click(dialog.get_by_role('button', name='Continue', exact=True))
        name_dialog = page.get_by_role('dialog').filter(has_text='Name your release')
        self.guard_identity()
        name_dialog.get_by_role('textbox').fill(self.manifest['title'])
        self.click(name_dialog.get_by_role('button', name='Create Release', exact=True))
        page.wait_for_url(re.compile(r'https://toolost\.com/uploader/edit/[0-9]+$'), timeout=30000)
        self.remote_id = urlsplit(page.url).path.rsplit('/', 1)[1]
        page.get_by_role('button', name='Artwork', exact=True).wait_for(state='visible')

    def asset(self, reference):
        file_reference(reference, self.base)
        path = Path(reference['path'])
        return str(path if path.is_absolute() else self.base / path)

    def artwork(self):
        page = self.page
        self.click(page.get_by_role('button', name='Artwork', exact=True))
        self.click(page.get_by_role('button', name=re.compile(r'^Upload Artwork(?:\s|$)')))
        dialog = page.get_by_role('dialog').filter(has_text=re.compile('Upload artwork', re.I))
        with page.expect_file_chooser(timeout=10000) as chooser:
            self.click(dialog.get_by_text('browse files', exact=True))
        asset = self.asset(self.manifest['artwork'])
        self.guard_target()
        chooser.value.set_files(asset)
        page.get_by_text('Artwork selected', exact=True).wait_for(state='visible', timeout=180000)

    def audio(self):
        page = self.page
        self.click(page.get_by_role('button', name='Manage Tracks', exact=True))
        if page.locator('.track-item:visible').count() != 0:
            raise DraftError('unexpected_existing_tracks')
        self.click(page.get_by_role('button', name=re.compile(r'^Upload tracks(?:\s|$)')))
        dialog = page.locator('[role=dialog]:visible').filter(has=page.get_by_role('button', name='Cancel', exact=True))
        with page.expect_file_chooser(timeout=10000) as chooser:
            self.click(dialog.get_by_text('browse files', exact=True))
        asset = self.asset(self.manifest['tracks'][0]['audio'])
        self.guard_target()
        chooser.value.set_files(asset)
        self.click(dialog.get_by_role('button', name=re.compile(r'^Upload\s+1\s+file$')))
        page.locator('.track-item:visible').first.wait_for(state='visible', timeout=240000)
        if page.locator('.track-item:visible').count() != 1:
            raise DraftError('track_identity_ambiguous')
        dialog.wait_for(state='hidden', timeout=30000)

    def editor(self):
        self.click(self.page.locator('.track-item:visible').get_by_role('button', name='Edit', exact=True))
        self.page.get_by_role('textbox', name='Track name', exact=True).wait_for(state='visible')

    def ai_switch(self):
        # Scope by the observed AI label, never the first unnamed switch on the page.
        section = self.page.locator('.ted__ai-toggle').filter(has=self.page.get_by_text('AI-assisted content', exact=True))
        switches = section.get_by_role('switch')
        if switches.count() != 1:
            raise DraftError('ai_selector_unverified')
        return switches

    def metadata(self):
        self.editor()
        self.metadata_open()

    def metadata_open(self):
        track = self.manifest['tracks'][0]
        title = self.page.get_by_role('textbox', name='Track name', exact=True)
        if not title.is_editable():
            if title.input_value() != track['title']:
                raise DraftError('track_title_locked_mismatch')
        else:
            self.guard_target()
            title.fill(track['title'])
        switch = self.ai_switch()
        value = switch.get_attribute('aria-checked')
        if value not in ('true', 'false'):
            raise DraftError('ai_semantics_unavailable')
        if (value == 'true') != track['ai_assisted']:
            self.click(switch.locator('..'))
        if switch.get_attribute('aria-checked') != str(track['ai_assisted']).lower():
            raise DraftError('ai_readback_mismatch')
        self.click(self.page.get_by_role('button', name='Done', exact=True))

    def save(self):
        page = self.page
        self.click(page.get_by_role('button', name='Save Changes', exact=True))
        dialog = page.get_by_role('dialog').filter(has=page.get_by_role('button', name='Save', exact=True))
        # Either confirmation or navigation; never retry Save Changes.
        for _ in range(60):
            if dialog.is_visible():
                self.click(dialog.get_by_role('button', name='Save', exact=True))
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
        self.read_only = True
        self.guard_identity()
        page.goto('https://toolost.com/uploader/edit/' + self.remote_id, wait_until='domcontentloaded', timeout=30000)
        self.guard_identity()
        if urlsplit(page.url).path != '/uploader/edit/' + self.remote_id:
            raise DraftError('draft_target_changed')
        page.get_by_role('button', name='Basic Information', exact=True).wait_for(state='visible', timeout=30000)
        title = page.get_by_role('textbox', name='Single name', exact=True)
        self.click(page.get_by_role('button', name='Basic Information', exact=True))
        title.wait_for(state='visible')
        if title.input_value() != self.manifest['title']:
            raise DraftError('release_title_or_type_mismatch')
        self.click(page.get_by_role('button', name='Artwork', exact=True))
        page.get_by_text('Artwork selected', exact=True).wait_for(state='visible', timeout=30000)
        self.click(page.get_by_role('button', name='Manage Tracks', exact=True))
        page.locator('.track-item:visible').first.wait_for(state='visible')
        if page.locator('.track-item:visible').count() != 1:
            raise DraftError('track_readback_mismatch')
        self.editor()
        track = self.manifest['tracks'][0]
        if page.get_by_role('textbox', name='Track name', exact=True).input_value() != track['title']:
            raise DraftError('title_readback_mismatch')
        if self.ai_switch().get_attribute('aria-checked') != str(track['ai_assisted']).lower():
            raise DraftError('ai_readback_mismatch')
        self.guard_target()


def run_steps(ui):
    ui.verify_account()
    for name in ('create', 'artwork', 'audio', 'metadata', 'save'):
        ui.action(name, getattr(ui, name))
    ui.readback()
    ui.record('readback', 'verified_subset', ui.remote_id)


def execute(path, *, alias, expected_account, endpoint, approve_draft, accept_ui_date, root=None,
            resume_before_artwork=False, resume_before_audio=False, resume_selected_audio=False,
            resume_open_metadata=False, approve_release_title_amendment=False, reconcile_only=False):
    if approve_draft is not True or accept_ui_date is not True:
        raise DraftError('confirmation_required')
    if not re.fullmatch(r'[1-9][0-9]*', expected_account):
        raise DraftError('invalid_expected_account')
    if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{1,5}', endpoint) or not 1024 <= int(endpoint.rsplit(':', 1)[1]) <= 65535:
        raise DraftError('loopback_endpoint_required')
    recovery = any((resume_before_artwork, resume_before_audio, resume_selected_audio, resume_open_metadata))
    if recovery:
        raise DraftError('debug_recovery_requires_readback_only')
    if reconcile_only and approve_release_title_amendment:
        raise DraftError('title_amendment_immutable')
    manifest, base = preflight(path, verify_assets=not reconcile_only)
    with profile(alias, root=root) as session:
        if reconcile_only:
            checkpoint = session.read_checkpoint(manifest['release_id'])
            if checkpoint['manifest'] != manifest or checkpoint['manifest_dir'] != str(base):
                raise DraftError('resume_manifest_mismatch')
            journal = LiveJournal(session, checkpoint, expected_account, endpoint, existing=True)
            remote_id = journal.require_reconciliation()
        else:
            checkpoint = session.create_checkpoint(manifest, base)
            journal = LiveJournal(session, checkpoint, expected_account, endpoint)
            if approve_release_title_amendment:
                journal.approve_title()
        def record(operation, outcome, remote_id):
            journal.record(operation, outcome, remote_id)
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(endpoint)
            pages = [page for context in browser.contexts for page in context.pages
                     if not page.is_closed() and urlsplit(page.url).scheme == 'https'
                     and urlsplit(page.url).netloc == 'toolost.com']
            if len(pages) != 1:
                raise DraftError('ambiguous_browser_target')
            ui = DraftUI(pages[0], journal.effective_manifest(), base, expected_account, record)
            ui.read_only = reconcile_only
            try:
                if reconcile_only:
                    ui.verify_account()
                    ui.remote_id = remote_id
                    ui.readback()
                    journal.verify_readback()
                else:
                    run_steps(ui)
            finally:
                ui.close()
        return dict(status='draft_readback_subset' if reconcile_only else 'draft_saved_subset',
                    run_id=checkpoint['run_id'], draft_id=ui.remote_id,
                    warnings=['Tanggal UI diwarisi; bukan release_date manifest terverifikasi.',
                              'Remote track identity dan rights/services belum diverifikasi; bukan siap distribusi.'])
