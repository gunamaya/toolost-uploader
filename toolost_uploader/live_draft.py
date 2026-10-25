"""Executor Playwright draft-only bounded; tidak menyediakan aksi Publish."""

import re
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit

from .storage import _atomic_write, _read, profile
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
        page.get_by_role('button', name=re.compile(r'^Upload Artwork(?:\s|$)')).click()
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
        page.get_by_role('button', name=re.compile(r'^Upload tracks(?:\s|$)')).click()
        dialog = page.locator('[role=dialog]:visible').filter(has=page.get_by_role('button', name='Cancel', exact=True))
        with page.expect_file_chooser(timeout=10000) as chooser:
            dialog.get_by_text('browse files', exact=True).click()
        chooser.value.set_files(self.asset(self.manifest['tracks'][0]['audio']))
        dialog.get_by_role('button', name=re.compile(r'^Upload\s+1\s+file$')).click()
        page.locator('.track-item:visible').first.wait_for(state='visible', timeout=240000)
        if page.locator('.track-item:visible').count() != 1:
            raise DraftError('track_identity_ambiguous')
        dialog.wait_for(state='hidden', timeout=30000)

    def audio_selected(self):
        page = self.page
        dialog = page.locator('[role=dialog]:visible').filter(has=page.get_by_role('button', name='Upload 1 file', exact=True))
        if dialog.count() != 1 or page.locator('.track-item:visible').count():
            raise DraftError('audio_selection_requires_review')
        filename = Path(self.manifest['tracks'][0]['audio']['path']).name
        dialog.get_by_text(filename, exact=True).wait_for(state='visible')
        self.asset(self.manifest['tracks'][0]['audio'])
        dialog.get_by_role('button', name='Upload 1 file', exact=True).click()
        dialog.wait_for(state='hidden', timeout=240000)
        page.locator('.track-item:visible').first.wait_for(state='visible', timeout=240000)
        if page.locator('.track-item:visible').count() != 1:
            raise DraftError('track_identity_ambiguous')

    def editor(self):
        self.page.locator('.track-item:visible').get_by_role('button', name='Edit', exact=True).click()
        self.page.get_by_role('textbox', name='Track name', exact=True).wait_for(state='visible')

    def ai_switch(self):
        # Scope by the observed AI label, never the first unnamed switch on the page.
        section = self.page.locator('.ted__ai-toggle').filter(has=self.page.get_by_text('AI-assisted content', exact=True))
        switches = section.get_by_role('switch')
        if switches.count() != 1:
            raise DraftError('ai_selector_unverified')
        return switches

    def metadata(self):
        track = self.manifest['tracks'][0]
        self.editor()
        self.metadata_open()

    def metadata_open(self):
        track = self.manifest['tracks'][0]
        title = self.page.get_by_role('textbox', name='Track name', exact=True)
        if not title.is_editable():
            if title.input_value() != track['title']:
                raise DraftError('track_title_locked_mismatch')
        else:
            self.record('metadata_title', 'unknown', self.remote_id)
            title.fill(track['title'])
            self.record('metadata_title', 'observed', self.remote_id)
        switch = self.ai_switch()
        value = switch.get_attribute('aria-checked')
        if value not in ('true', 'false'):
            raise DraftError('ai_semantics_unavailable')
        if (value == 'true') != track['ai_assisted']:
            switch.locator('..').click()
        if switch.get_attribute('aria-checked') != str(track['ai_assisted']).lower():
            raise DraftError('ai_readback_mismatch')
        self.page.get_by_role('button', name='Done', exact=True).click()

    def amend_release_title(self):
        self.page.get_by_role('button', name='Done', exact=True).click()
        self.page.get_by_role('button', name='Basic Information', exact=True).click()
        title = self.page.get_by_role('textbox', name='Single name', exact=True)
        title.fill(self.manifest['tracks'][0]['title'])
        self.manifest = deepcopy(self.manifest)
        self.manifest['title'] = self.manifest['tracks'][0]['title']
        self.page.get_by_role('button', name='Manage Tracks', exact=True).click()
        self.editor()

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
        page.get_by_role('button', name='Basic Information', exact=True).wait_for(state='visible', timeout=30000)
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


def execute(path, *, alias, expected_account, endpoint, approve_draft, accept_ui_date, root=None,
            resume_before_artwork=False, resume_before_audio=False, resume_selected_audio=False,
            resume_open_metadata=False, approve_release_title_amendment=False):
    if approve_draft is not True or accept_ui_date is not True:
        raise DraftError('confirmation_required')
    if not re.fullmatch(r'[1-9][0-9]*', expected_account):
        raise DraftError('invalid_expected_account')
    if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{1,5}', endpoint) or not 1024 <= int(endpoint.rsplit(':', 1)[1]) <= 65535:
        raise DraftError('loopback_endpoint_required')
    manifest, base = preflight(path)
    from playwright.sync_api import sync_playwright
    with profile(alias, root=root) as session:
        recovery = resume_before_artwork or resume_before_audio or resume_selected_audio or resume_open_metadata
        if sum((resume_before_artwork, resume_before_audio, resume_selected_audio, resume_open_metadata)) > 1:
            raise DraftError('ambiguous_recovery_stage')
        if recovery:
            checkpoint = session.read_checkpoint(manifest['release_id'])
            if checkpoint['manifest'] != manifest or checkpoint['manifest_dir'] != str(base):
                raise DraftError('resume_manifest_mismatch')
            previous = _read(session.directory, manifest['release_id'] + '.live.json')
            expected = [('preflight', 'validated'), ('create', 'unknown'), ('create', 'observed'), ('artwork', 'unknown')]
            if resume_before_audio or resume_selected_audio or resume_open_metadata:
                expected += [('artwork_reconciled', 'not_selected_operator_review'),
                             ('artwork', 'unknown'), ('artwork', 'observed'), ('audio', 'unknown')]
            if resume_selected_audio or resume_open_metadata:
                expected += [('audio_reconciled', 'not_selected_operator_review'), ('audio', 'unknown')]
            if resume_open_metadata:
                expected += [('audio_selected', 'unknown'), ('audio_selected', 'observed'), ('metadata', 'unknown')]
                actual = [(e.get('operation'), e.get('outcome')) for e in previous.get('events', [])]
                suffix = actual[len(expected):]
                if suffix and all(e in (('metadata_reconciled', 'unknown'), ('metadata_title', 'unknown')) for e in suffix):
                    expected += suffix
            if (previous.get('run_id') != checkpoint['run_id'] or
                    [(e.get('operation'), e.get('outcome')) for e in previous.get('events', [])] != expected or
                    not re.fullmatch(r'[0-9]+', str(previous.get('remote_draft_id', '')))):
                raise DraftError('resume_requires_manual_reconciliation')
            events = previous['events'][:]
        else:
            checkpoint = session.create_checkpoint(manifest, base)
            events = []
        def record(operation, outcome, remote_id):
            events.append(dict(operation=operation, outcome=outcome))
            _atomic_write(session.directory, manifest['release_id'] + '.live.json',
                          dict(run_id=checkpoint['run_id'], remote_draft_id=remote_id, events=events))
        if not recovery:
            record('preflight', 'validated', None)
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(endpoint)
            pages = [page for context in browser.contexts for page in context.pages
                     if not page.is_closed() and urlsplit(page.url).scheme == 'https'
                     and urlsplit(page.url).netloc == 'toolost.com']
            if len(pages) != 1:
                raise DraftError('ambiguous_browser_target')
            ui = DraftUI(pages[0], manifest, base, expected_account, record)
            if recovery:
                # Explicit operator reconciliation only: first run stopped before file selection.
                ui.remote_id = previous['remote_draft_id']
                if urlsplit(ui.page.url).path != '/uploader/edit/' + ui.remote_id:
                    raise DraftError('draft_target_changed')
                ui.guard()
                if resume_open_metadata:
                    if not ui.page.get_by_role('textbox', name='Track name', exact=True).is_visible():
                        raise DraftError('track_editor_not_open')
                    if approve_release_title_amendment:
                        record('title_amendment', 'approved_release_equals_track', ui.remote_id)
                        ui.action('amend_release_title', ui.amend_release_title)
                    ui.action('metadata_reconciled', ui.metadata_open)
                    ui.action('save', ui.save)
                    ui.readback()
                    ui.record('readback', 'verified_subset', ui.remote_id)
                    return dict(status='draft_saved_subset', run_id=checkpoint['run_id'], draft_id=ui.remote_id,
                                warnings=['Smoke subset only; UI date inherited, remote track ID and rights unverified.'])
                if resume_selected_audio:
                    ui.action('audio_selected', ui.audio_selected)
                    for name in ('metadata', 'save'):
                        ui.action(name, getattr(ui, name))
                    ui.readback()
                    ui.record('readback', 'verified_subset', ui.remote_id)
                    return dict(status='draft_saved_subset', run_id=checkpoint['run_id'], draft_id=ui.remote_id,
                                warnings=['Smoke subset only; UI date inherited, remote track ID and rights unverified.'])
                if ui.page.locator('[role=dialog]:visible').count() and not resume_before_audio:
                    raise DraftError('unexpected_dialog')
                ui.page.get_by_role('button', name='Basic Information', exact=True).click()
                title = ui.page.get_by_role('textbox', name='Single name', exact=True)
                title.wait_for(state='visible')
                if title.input_value() != manifest['title']:
                    raise DraftError('draft_target_changed')
                if resume_before_artwork:
                    ui.page.get_by_role('button', name='Artwork', exact=True).click()
                    ui.page.get_by_role('button', name=re.compile(r'^Upload Artwork(?:\s|$)')).wait_for(state='visible')
                    if ui.page.get_by_text('Artwork selected', exact=True).is_visible():
                        raise DraftError('existing_artwork_requires_review')
                    record('artwork_reconciled', 'not_selected_operator_review', ui.remote_id)
                    stages = ('artwork', 'audio', 'metadata', 'save')
                else:
                    ui.page.get_by_role('button', name='Manage Tracks', exact=True).click()
                    ui.page.get_by_role('button', name=re.compile(r'^Upload tracks(?:\s|$)')).wait_for(state='visible')
                    if ui.page.locator('.track-item:visible').count():
                        raise DraftError('existing_audio_requires_review')
                    record('audio_reconciled', 'not_selected_operator_review', ui.remote_id)
                    stages = ('audio', 'metadata', 'save')
                for name in stages:
                    ui.action(name, getattr(ui, name))
                ui.readback()
                ui.record('readback', 'verified_subset', ui.remote_id)
            else:
                run_steps(ui)
        return dict(status='draft_saved_subset', run_id=checkpoint['run_id'], draft_id=ui.remote_id,
                    warnings=['Tanggal UI diwarisi; bukan release_date manifest terverifikasi.',
                              'Remote track identity dan rights/services belum diverifikasi; bukan siap distribusi.'])
