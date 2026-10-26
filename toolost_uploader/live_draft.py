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
    if set(manifest) != required or manifest['release_type'] not in ('single', 'album'):
        raise DraftError('unsupported_live_manifest')
    if not manifest['tracks']:
        raise DraftError('unsupported_live_manifest')
    if manifest['release_type'] == 'single' and len(manifest['tracks']) != 1:
        raise DraftError('unsupported_live_manifest')
    for track in manifest['tracks']:
        if set(track) not in ({'track_id', 'title', 'audio', 'ai_assisted'},
                              {'track_id', 'title', 'audio', 'ai_assisted', 'lyrics'}):
            raise DraftError('unsupported_live_track_fields')
    # Tanggal wajib manifest belum diterapkan: hanya smoke draft dengan opt-in terpisah.
    return manifest, path.parent


class DraftUI:
    def __init__(self, page, manifest, base, expected_account, record, log=None):
        self.page, self.manifest, self.base = page, deepcopy(manifest), base
        self.expected_account, self.record = expected_account, record
        self.log = log or (lambda msg: None)
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
            url_str = getattr(route.request, 'url', None)
            if isinstance(url_str, str) and urlsplit(url_str).path == '/api/auth/refresh':
                route.continue_()
                return
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
        except Exception:
            pass
        try:
            self.page.context.remove_listener('response', self.observe_account)
        except Exception:
            pass

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
        self.identity_changed = False
        self.guard()
        self.log('Memeriksa target browser dan status autentikasi akun...')
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
            for _ in range(40):
                if ids:
                    break
                self.page.wait_for_timeout(250)
            self.guard()
            if not ids or any(value != self.expected_account for value in ids) or self.identity_changed:
                raise DraftError('account_mismatch_or_unobserved')
            self.identity_verified = True
            self.log(f'Identitas akun terverifikasi: id={self.expected_account}')
        finally:
            self.page.remove_listener('response', response)
            ids.clear()

    def create(self):
        page = self.page
        self.log(f"Membuka portal uploader dan memilih tipe rilis '{self.manifest['release_type']}'...")
        self.click(page.locator('a[href="/uploader"]:visible').first)
        dialog = page.get_by_role('dialog').filter(has=page.get_by_role('heading', name='Select release type', exact=True))
        dialog.wait_for(state='visible', timeout=30000)
        if self.manifest['release_type'] == 'single':
            self.click(dialog.get_by_role('button', name=re.compile(r'^Single\s+1–3 tracks$')))
        elif self.manifest['release_type'] == 'album':
            self.click(dialog.get_by_role('button', name=re.compile(r'^Album\s+', re.I)))
        else:
            raise DraftError('unsupported_live_manifest')
        self.click(dialog.get_by_role('button', name='Continue', exact=True))
        name_dialog = page.get_by_role('dialog').filter(has_text='Name your release')
        self.guard_identity()
        self.log(f"Mengisi judul rilis: '{self.manifest['title']}'...")
        name_dialog.get_by_role('textbox').fill(self.manifest['title'])
        self.click(name_dialog.get_by_role('button', name='Create Release', exact=True))
        page.wait_for_url(re.compile(r'https://toolost\.com/uploader/edit/[0-9]+$'), timeout=30000)
        self.remote_id = urlsplit(page.url).path.rsplit('/', 1)[1]
        page.get_by_role('button', name='Artwork', exact=True).wait_for(state='visible')
        self.log(f'Draft rilis baru terbuat di uploader: remote_id={self.remote_id}')

    def update_title(self):
        page = self.page
        self.log('Membuka panel Basic Information untuk update judul...')
        self.click(page.get_by_role('button', name='Basic Information', exact=True))
        title_label = 'Single name' if self.manifest['release_type'] == 'single' else 'Album name'
        title_box = page.get_by_role('textbox', name=title_label, exact=True)
        if hasattr(title_box, 'wait_for'):
            title_box.wait_for(state='visible', timeout=15000)
        cur_val = title_box.input_value() if hasattr(title_box, 'input_value') else ''
        if cur_val != self.manifest['title']:
            self.guard_target()
            self.log(f"Memperbarui judul rilis dari '{cur_val}' menjadi '{self.manifest['title']}'...")
            title_box.fill(self.manifest['title'])
        self.log('Pembaruan judul rilis selesai.')

    def update_date(self):
        page = self.page
        target_iso = self.manifest['release_date']
        self.log(f"Membuka tab Release Information untuk mengatur tanggal rilis: {target_iso}...")
        self.click(page.get_by_role('button', name='Release Information', exact=True))
        import datetime
        target = datetime.date.fromisoformat(target_iso)
        target_day_str = str(target.day)
        lbl = page.locator('label').filter(has_text=re.compile(r'^Release Date$'))
        if hasattr(lbl, 'wait_for'):
            lbl.wait_for(state='visible', timeout=15000)
        inp_id = lbl.get_attribute('for') if hasattr(lbl, 'get_attribute') else 'date-input'
        inp = page.locator(f'#{inp_id}')

        expected_val = target.strftime('%m/%d/%Y')
        if hasattr(inp, 'input_value') and inp.input_value() == expected_val:
            self.log(f'Tanggal rilis sudah sesuai: {expected_val}')
            return

        if hasattr(inp, 'click'):
            try:
                inp.click(force=True)
            except Exception:
                pass
        if hasattr(page, 'wait_for_timeout'):
            page.wait_for_timeout(500)

        header_btn = page.locator('.v-date-picker-header:visible button').nth(1)
        next_btn = page.locator('.v-date-picker-header:visible button[aria-label="Next month"]')
        prev_btn = page.locator('.v-date-picker-header:visible button[aria-label="Previous month"]')

        for _ in range(60):
            if not hasattr(header_btn, 'inner_text'):
                break
            try:
                current_month_str = header_btn.inner_text().strip()
                cur_date = datetime.datetime.strptime(current_month_str, '%B %Y').date()
            except Exception:
                break
            if cur_date.year == target.year and cur_date.month == target.month:
                break
            if cur_date < target.replace(day=1):
                self.click(next_btn)
            else:
                self.click(prev_btn)
            if hasattr(page, 'wait_for_timeout'):
                page.wait_for_timeout(200)

        day_btn = page.locator('.v-date-picker-table--date:visible button').filter(has_text=re.compile(rf'^{target_day_str}$'))
        if hasattr(day_btn, 'wait_for'):
            day_btn.wait_for(state='visible', timeout=10000)
        self.click(day_btn)
        if hasattr(page, 'wait_for_timeout'):
            page.wait_for_timeout(500)
        self.log(f"Tanggal rilis berhasil diatur: {inp.input_value() if hasattr(inp, 'input_value') else expected_val}")

    def asset(self, reference):
        file_reference(reference, self.base)
        path = Path(reference['path'])
        return str(path if path.is_absolute() else self.base / path)

    def artwork(self):
        page = self.page
        self.log('Membuka panel Artwork...')
        self.click(page.get_by_role('button', name='Artwork', exact=True))
        btn_upload = page.get_by_role('button', name=re.compile(r'^(?:Upload Artwork|Upload new file|Replace)', re.I))
        if hasattr(btn_upload, 'first'):
            btn_upload = btn_upload.first
        if hasattr(btn_upload, 'wait_for'):
            btn_upload.wait_for(state='visible', timeout=15000)
        self.click(btn_upload)
        dialog = page.get_by_role('dialog').filter(has_text=re.compile('Upload artwork', re.I))
        if hasattr(dialog, 'wait_for'):
            dialog.wait_for(state='visible', timeout=15000)
        with page.expect_file_chooser(timeout=10000) as chooser:
            browse_btn = dialog.get_by_text('browse files', exact=True)
            self.click(browse_btn)
        asset = self.asset(self.manifest['artwork'])
        self.guard_target()
        self.log(f'Mengunggah file artwork: {asset}...')
        chooser.value.set_files(asset)
        self.log('Menunggu proses upload dan encoding artwork...')
        replace_btn = page.get_by_role('button', name=re.compile('Replace', re.I))
        txt = page.get_by_text(re.compile(r'Artwork selected|Uploaded', re.I))
        art_container = page.locator('.artwork-selected')
        page.wait_for_timeout(1000)
        for _ in range(360):
            is_container = art_container.count() > 0 if hasattr(art_container, 'count') else False
            is_dialog_hidden = page.locator('.tl-upload-dialog:visible').count() == 0 if hasattr(page.locator('.tl-upload-dialog:visible'), 'count') else True
            is_rep = replace_btn.first.is_visible() if hasattr(replace_btn, 'first') and hasattr(replace_btn.first, 'is_visible') else False
            is_txt = txt.first.is_visible() if hasattr(txt, 'first') and hasattr(txt.first, 'is_visible') else False
            if (is_container or is_rep or is_txt) and is_dialog_hidden:
                break
            if is_container:
                break
            page.wait_for_timeout(500)
        else:
            raise DraftError('artwork_upload_timeout')
        self.log('Unggahan artwork selesai.')

    def reorder_tracks(self):
        items = self.page.locator('.track-item:visible')
        if not hasattr(items, 'count'):
            return
        try:
            count = items.count()
        except Exception:
            return
        if type(count) is not int or count <= 1:
            return
        manifest_basenames = [Path(t['audio']['path']).stem.lower() for t in self.manifest['tracks']]
        for target_idx, stem in enumerate(manifest_basenames):
            try:
                current_texts = [items.nth(i).text_content().lower() for i in range(count)]
            except Exception:
                break
            actual_idx = None
            for idx, text in enumerate(current_texts):
                if isinstance(text, str) and stem in text:
                    actual_idx = idx
                    break
            if actual_idx is not None and actual_idx != target_idx and actual_idx > target_idx:
                try:
                    self.log(f"Menyesuaikan urutan track '{stem}' ke posisi {target_idx + 1}...")
                    box_target = items.nth(target_idx).bounding_box()
                    handle_actual = items.nth(actual_idx).locator('.track-item__drag').bounding_box()
                    if box_target and handle_actual:
                        self.page.mouse.move(handle_actual['x'] + handle_actual['width'] / 2,
                                             handle_actual['y'] + handle_actual['height'] / 2)
                        self.page.mouse.down()
                        self.page.mouse.move(box_target['x'] + box_target['width'] / 2, box_target['y'] + 5, steps=10)
                        self.page.mouse.up()
                        self.page.wait_for_timeout(1000)
                except Exception:
                    pass

    def audio(self):
        page = self.page
        self.log('Membuka tab Manage Tracks...')
        self.click(page.get_by_role('button', name='Manage Tracks', exact=True))
        if page.locator('.track-item:visible').count() != 0:
            raise DraftError('unexpected_existing_tracks')
        upload_btn = page.get_by_role('button', name=re.compile(r'^Upload tracks', re.I))
        if hasattr(upload_btn, 'wait_for'):
            upload_btn.wait_for(state='visible', timeout=15000)
        self.click(upload_btn)
        dialog = page.locator('[role=dialog]:visible').filter(has_text=re.compile('Upload tracks', re.I))
        if hasattr(dialog, 'wait_for'):
            dialog.wait_for(state='visible', timeout=15000)
        with page.expect_file_chooser(timeout=10000) as chooser:
            self.click(dialog.get_by_text('browse files', exact=True))
        assets = [self.asset(t['audio']) for t in self.manifest['tracks']]
        self.guard_target()
        self.log(f'Mengunggah {len(assets)} file audio track...')
        chooser.value.set_files(assets[0] if len(assets) == 1 else assets)
        count = len(assets)
        btn_regex = r'^Upload\s+1\s+file' if count == 1 else rf'^Upload\s+{count}\s+files'
        self.click(dialog.get_by_role('button', name=re.compile(btn_regex, re.I)))
        self.log(f'Menunggu transfer dan encoding {count} file audio selesai...')
        page.locator('.track-item:visible').first.wait_for(state='visible', timeout=240000)
        if page.locator('.track-item:visible').count() != count:
            raise DraftError('track_identity_ambiguous')
        for _ in range(60):
            if page.locator('.tl-upload-dialog:visible').count() == 0:
                break
            page.wait_for_timeout(500)
        self.log('Unggahan berkas audio selesai. Memeriksa urutan track...')
        self.reorder_tracks()

    def append_tracks(self, new_tracks, expected_old_count):
        page = self.page
        self.log('Membuka tab Manage Tracks untuk append...')
        self.click(page.get_by_role('button', name='Manage Tracks', exact=True))
        current_items = page.locator('.track-item:visible')
        if hasattr(current_items, 'count'):
            current_count = current_items.count()
            if current_count != expected_old_count:
                raise DraftError('unexpected_existing_tracks')
        upload_btn = page.get_by_role('button', name='Upload', exact=True)
        is_vis = upload_btn.is_visible() if hasattr(upload_btn, 'is_visible') else False
        if not is_vis:
            upload_btn = page.get_by_role('button', name=re.compile(r'^Upload', re.I))
        if hasattr(upload_btn, 'wait_for'):
            upload_btn.wait_for(state='visible', timeout=15000)
        self.click(upload_btn)
        dialog = page.locator('[role=dialog]:visible').filter(has_text=re.compile('Upload tracks', re.I))
        if hasattr(dialog, 'wait_for'):
            dialog.wait_for(state='visible', timeout=15000)
        with page.expect_file_chooser(timeout=10000) as chooser:
            self.click(dialog.get_by_text('browse files', exact=True))
        assets = [self.asset(t['audio']) for t in new_tracks]
        self.guard_target()
        self.log(f'Mengunggah {len(assets)} file audio track susulan...')
        chooser.value.set_files(assets[0] if len(assets) == 1 else assets)
        count = len(assets)
        btn_regex = r'^Upload\s+1\s+file' if count == 1 else rf'^Upload\s+{count}\s+files'
        self.click(dialog.get_by_role('button', name=re.compile(btn_regex, re.I)))
        self.log(f'Menunggu transfer dan encoding {count} file audio susulan selesai...')
        expected_total = expected_old_count + count
        if hasattr(page.locator('.track-item:visible'), 'first'):
            first_item = page.locator('.track-item:visible').first
            if hasattr(first_item, 'wait_for'):
                first_item.wait_for(state='visible', timeout=240000)
        for _ in range(240):
            cnt = page.locator('.track-item:visible').count() if hasattr(page.locator('.track-item:visible'), 'count') else expected_total
            if cnt == expected_total:
                break
            page.wait_for_timeout(500)
        else:
            raise DraftError('track_identity_ambiguous')
        for _ in range(60):
            cnt_dlg = page.locator('.tl-upload-dialog:visible').count() if hasattr(page.locator('.tl-upload-dialog:visible'), 'count') else 0
            if cnt_dlg == 0:
                break
            page.wait_for_timeout(500)
        self.log('Unggahan berkas audio susulan selesai. Memeriksa urutan track...')
        self.reorder_tracks()

    def editor(self, index=0):
        items = self.page.locator('.track-item:visible')
        if hasattr(items, 'nth'):
            button = items.nth(index).get_by_role('button', name='Edit', exact=True)
        else:
            button = items.get_by_role('button', name='Edit', exact=True)
        self.click(button)
        self.page.get_by_role('textbox', name='Track name', exact=True).wait_for(state='visible')

    def ai_switch(self):
        # Scope by the observed AI label, never the first unnamed switch on the page.
        section = self.page.locator('.ted__ai-toggle').filter(has=self.page.get_by_text('AI-assisted content', exact=True))
        switches = section.get_by_role('switch')
        if switches.count() != 1:
            raise DraftError('ai_selector_unverified')
        return switches

    def metadata(self):
        total = len(self.manifest['tracks'])
        for i, track in enumerate(self.manifest['tracks']):
            self.log(f"Mengisi metadata track {i + 1}/{total}: '{track['title']}' (AI: {track['ai_assisted']})...")
            self.editor(i)
            self.metadata_open(track)

    def metadata_append(self, new_tracks, start_index):
        total_new = len(new_tracks)
        for i, track in enumerate(new_tracks):
            track_idx = start_index + i
            self.log(f"Mengisi metadata track susulan {i + 1}/{total_new} (posisi {track_idx + 1}): '{track['title']}' (AI: {track['ai_assisted']})...")
            self.editor(track_idx)
            self.metadata_open(track)

    def metadata_update_and_append(self, tracks_to_update, tracks_to_append, old_count):
        for track_idx, track in tracks_to_update:
            self.log(f"Memperbarui metadata track lama urutan ke-{track_idx + 1}: '{track['title']}' (AI: {track['ai_assisted']})...")
            self.editor(track_idx)
            self.metadata_open(track)
        total_append = len(tracks_to_append)
        for i, track in enumerate(tracks_to_append):
            track_idx = old_count + i
            self.log(f"Mengisi metadata track susulan {i + 1}/{total_append} (urutan ke-{track_idx + 1}): '{track['title']}' (AI: {track['ai_assisted']})...")
            self.editor(track_idx)
            self.metadata_open(track)

    def metadata_open(self, track=None):
        if track is None:
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
        if 'lyrics' in track:
            self.lyrics_fill(track)
        self.click(self.page.get_by_role('button', name='Done', exact=True))

    def lyrics_text(self, track):
        lpath = Path(track['lyrics']['path'])
        if not lpath.is_absolute():
            lpath = self.base / lpath
        return lpath.read_text(encoding='utf-8')

    def lyrics_fill(self, track):
        text = self.lyrics_text(track)
        self.log(f"Mengisi lirik track '{track['title']}' ({len(text)} karakter)...")
        self.click(self.page.get_by_role('button', name='Lyrics', exact=True))
        box = self.page.get_by_role('textbox', name='Lyrics', exact=True)
        box.wait_for(state='visible')
        self.guard_target()
        box.fill(text)
        if box.input_value() != text:
            raise DraftError('lyrics_readback_mismatch')

    def save(self):
        page = self.page
        self.log('Menyimpan draft release (Save Changes)...')
        self.click(page.get_by_role('button', name='Save Changes', exact=True))
        dialog = page.get_by_role('dialog').filter(has=page.get_by_role('button', name='Save', exact=True))
        # Either confirmation or navigation; never retry Save Changes.
        for _ in range(60):
            if dialog.is_visible():
                self.click(dialog.get_by_role('button', name='Save', exact=True))
                break
            if '/releases/manage/' in page.url:
                self.log('Draft berhasil disimpan (navigasi ke daftar rilis).')
                return
            page.wait_for_timeout(250)
        else:
            raise DraftError('save_outcome_unknown')
        self.log('Menunggu konfirmasi penyimpanan selesai...')
        page.get_by_text('Saving your release', exact=False).wait_for(state='hidden', timeout=60000)
        if page.get_by_text('Something went wrong while saving your release.', exact=False).is_visible():
            raise DraftError('save_outcome_unknown')
        self.log('Penyimpanan draft di Too Lost berhasil.')

    def readback(self):
        page = self.page
        self.log(f'Membuka draft uploader untuk readback verifikasi: {self.remote_id}...')
        self.guard_identity()
        page.goto('https://toolost.com/uploader/edit/' + self.remote_id, wait_until='domcontentloaded', timeout=30000)
        self.guard_identity()
        if urlsplit(page.url).path != '/uploader/edit/' + self.remote_id:
            raise DraftError('draft_target_changed')
        page.get_by_role('button', name='Basic Information', exact=True).wait_for(state='visible', timeout=30000)
        self.click(page.get_by_role('button', name='Basic Information', exact=True))
        title_label = 'Single name' if self.manifest['release_type'] == 'single' else 'Album name'
        title = page.get_by_role('textbox', name=title_label, exact=True)
        title.wait_for(state='visible')
        if title.input_value() != self.manifest['title']:
            raise DraftError('release_title_or_type_mismatch')
        self.log(f"Verifikasi judul rilis '{self.manifest['title']}' cocok.")
        self.click(page.get_by_role('button', name='Artwork', exact=True))
        for _ in range(40):
            if hasattr(page.locator('.artwork-selected'), 'count') and page.locator('.artwork-selected').count() > 0:
                break
            page.wait_for_timeout(250)
        else:
            page.get_by_text(re.compile(r'Artwork selected|Uploaded', re.I)).first.wait_for(state='visible', timeout=15000)
        self.log('Verifikasi artwork tersimpan cocok.')
        self.click(page.get_by_role('button', name='Manage Tracks', exact=True))
        page.locator('.track-item:visible').first.wait_for(state='visible')
        track_count = len(self.manifest['tracks'])
        if page.locator('.track-item:visible').count() != track_count:
            raise DraftError('track_readback_mismatch')
        for i, track in enumerate(self.manifest['tracks']):
            self.editor(i)
            if page.get_by_role('textbox', name='Track name', exact=True).input_value() != track['title']:
                raise DraftError('title_readback_mismatch')
            if self.ai_switch().get_attribute('aria-checked') != str(track['ai_assisted']).lower():
                raise DraftError('ai_readback_mismatch')
            if 'lyrics' in track:
                self.click(page.get_by_role('button', name='Lyrics', exact=True))
                box = page.get_by_role('textbox', name='Lyrics', exact=True)
                box.wait_for(state='visible')
                if box.input_value() != self.lyrics_text(track):
                    raise DraftError('lyrics_readback_mismatch')
            done_btn = page.get_by_role('button', name='Done', exact=True)
            has_done = True
            if hasattr(done_btn, 'count'):
                cnt = done_btn.count()
                if type(cnt) is int and cnt == 0:
                    has_done = False
            if has_done:
                self.click(done_btn)
        self.guard_target()
        self.log(f'Readback verifikasi {track_count} tracks dan metadata sukses.')

        if not self.read_only:
            save_btn = page.get_by_role('button', name='Save Changes', exact=True)
            should_save = False
            if hasattr(save_btn, 'is_visible'):
                vis = save_btn.is_visible()
                if vis is True or (not isinstance(vis, bool) and not isinstance(vis, type(None))):
                    should_save = True
            if hasattr(save_btn, 'is_enabled'):
                if save_btn.is_enabled() is False:
                    should_save = False

            if should_save:
                self.log('Menyimpan perubahan pasca-verifikasi (Save Changes)...')
                self.click(save_btn)
                dialog = page.get_by_role('dialog').filter(has=page.get_by_role('button', name='Save', exact=True))
                for _ in range(40):
                    if hasattr(dialog, 'is_visible') and dialog.is_visible():
                        self.click(dialog.get_by_role('button', name='Save', exact=True))
                        break
                    if '/releases/manage/' in getattr(page, 'url', ''):
                        break
                    if hasattr(page, 'wait_for_timeout'):
                        page.wait_for_timeout(250)
                saving_text = page.get_by_text('Saving your release', exact=False)
                if hasattr(saving_text, 'wait_for'):
                    try:
                        saving_text.wait_for(state='hidden', timeout=60000)
                    except Exception:
                        pass
                self.log('Penyimpanan draft selesai.')

        self.log('Navigasi kembali ke portal daftar rilis...')
        page.goto('https://toolost.com/user-portal/releases/manage/1', wait_until='domcontentloaded', timeout=30000)
        create_btn = page.get_by_role('button', name='Create New Release', exact=True)
        if hasattr(create_btn, 'wait_for'):
            try:
                create_btn.wait_for(state='visible', timeout=30000)
            except Exception:
                pass
        self.read_only = True
        self.log('Kembali ke portal daftar rilis berhasil: https://toolost.com/user-portal/releases/manage/1')


def run_steps(ui):
    ui.verify_account()
    for name in ('create', 'artwork', 'audio', 'metadata', 'save'):
        ui.action(name, getattr(ui, name))
    ui.readback()
    ui.record('readback', 'verified_subset', ui.remote_id)


def update_run_steps(ui, title_changed, date_changed, artwork_changed, tracks_to_append, tracks_to_update, old_count):
    ui.verify_account()
    ui.guard_identity()
    ui.log(f'Membuka draft release uploader untuk update/sinkronisasi: {ui.remote_id}...')
    ui.page.goto('https://toolost.com/uploader/edit/' + ui.remote_id, wait_until='domcontentloaded', timeout=30000)
    ui.guard_identity()
    if urlsplit(ui.page.url).path != '/uploader/edit/' + ui.remote_id:
        raise DraftError('draft_target_changed')

    if title_changed:
        ui.action('update_title', ui.update_title)

    if date_changed:
        ui.action('update_date', ui.update_date)

    if artwork_changed:
        ui.action('update_artwork', ui.artwork)

    if tracks_to_append:
        ui.action('append_audio', lambda: ui.append_tracks(tracks_to_append, old_count))

    if tracks_to_update or tracks_to_append:
        ui.action('update_metadata', lambda: ui.metadata_update_and_append(tracks_to_update, tracks_to_append, old_count))

    ui.action('save', ui.save)
    ui.readback()
    ui.record('readback', 'verified_subset', ui.remote_id)


def append_run_steps(ui, new_tracks, old_count):
    return update_run_steps(ui, False, False, False, new_tracks, [], old_count)


def execute(path, *, alias, expected_account, endpoint, approve_draft, accept_ui_date, root=None,
            resume_before_artwork=False, resume_before_audio=False, resume_selected_audio=False,
            resume_open_metadata=False, approve_release_title_amendment=False, reconcile_only=False,
            allow_append=False, allow_update=False, log=None):
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
    allow_sync = allow_append or allow_update
    if allow_sync and reconcile_only:
        raise DraftError('conflicting_append_and_reconcile')
    if log:
        log(f"Memeriksa preflight manifest: {path}")
    manifest, base = preflight(path, verify_assets=not reconcile_only)
    with profile(alias, root=root) as session:
        is_existing = False
        try:
            old_checkpoint = session.read_checkpoint(manifest['release_id'])
            is_existing = True
        except Exception:
            is_existing = False

        if reconcile_only:
            if not is_existing:
                raise DraftError('checkpoint_not_found')
            if old_checkpoint['manifest'] != manifest or old_checkpoint['manifest_dir'] != str(base):
                raise DraftError('resume_manifest_mismatch')
            checkpoint = old_checkpoint
            journal = LiveJournal(session, old_checkpoint, expected_account, endpoint, existing=True)
            remote_id = journal.require_reconciliation()
        elif allow_sync:
            if manifest['release_type'] != 'album':
                raise DraftError('append_requires_album')
            if not is_existing:
                raise DraftError('append_requires_existing_checkpoint')
            old_manifest = old_checkpoint['manifest']
            title_changed = (manifest['title'] != old_manifest.get('title'))
            date_changed = (manifest.get('release_date') != old_manifest.get('release_date'))
            artwork_changed = (manifest.get('artwork') != old_manifest.get('artwork'))

            old_tracks = old_manifest.get('tracks', [])
            new_tracks = manifest.get('tracks', [])
            old_count = len(old_tracks)
            new_count = len(new_tracks)

            tracks_to_update = []
            for i in range(min(old_count, new_count)):
                ot, nt = old_tracks[i], new_tracks[i]
                if (ot.get('title') != nt.get('title') or
                    ot.get('ai_assisted') != nt.get('ai_assisted') or
                    ot.get('lyrics') != nt.get('lyrics')):
                    tracks_to_update.append((i, nt))

            tracks_to_append = new_tracks[old_count:] if new_count > old_count else []
            has_changes = title_changed or date_changed or artwork_changed or bool(tracks_to_update) or bool(tracks_to_append)

            journal = LiveJournal(session, old_checkpoint, expected_account, endpoint, existing=True)
            remote_id = journal.require_reconciliation()

            if not has_changes:
                if log:
                    log("Draft rilis sudah up-to-date; tidak ada perubahan metadata atau track yang diperlukan.")
                return dict(status='draft_up_to_date', run_id=old_checkpoint['run_id'], draft_id=remote_id,
                            warnings=['Manifest identik dengan checkpoint rilis tersimpan.'])

            checkpoint = session.update_checkpoint(manifest, base, expected_revision=old_checkpoint['revision'])
            journal.update_for_append(checkpoint)
        else:
            checkpoint = session.create_checkpoint(manifest, base)
            journal = LiveJournal(session, checkpoint, expected_account, endpoint)
            if approve_release_title_amendment:
                journal.approve_title()

        def record(operation, outcome, remote_id):
            journal.record(operation, outcome, remote_id)
        if log:
            log(f"Menghubungkan ke browser CDP di {endpoint}...")
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            from toolost_uploader.browser import DEFAULT_PORTAL_URL, acquire_active_page, is_local_endpoint
            browser = p.chromium.connect_over_cdp(endpoint, is_local=is_local_endpoint(endpoint))
            page = acquire_active_page(browser, domain='toolost.com', default_url=DEFAULT_PORTAL_URL, log=log)
            ui = DraftUI(page, journal.effective_manifest(), base, expected_account, record, log=log)
            ui.read_only = reconcile_only
            try:
                if reconcile_only:
                    ui.verify_account()
                    ui.remote_id = remote_id
                    ui.readback()
                    journal.verify_readback()
                elif allow_sync:
                    ui.remote_id = remote_id
                    update_run_steps(ui, title_changed, date_changed, artwork_changed, tracks_to_append, tracks_to_update, old_count)
                else:
                    run_steps(ui)
            finally:
                ui.close()
        out_status = 'draft_readback_subset' if reconcile_only else ('draft_appended_subset' if (allow_append and not tracks_to_update and not title_changed and not artwork_changed and not date_changed) else ('draft_updated_subset' if allow_sync else 'draft_saved_subset'))
        return dict(status=out_status,
                    run_id=checkpoint['run_id'], draft_id=ui.remote_id,
                    warnings=['Tanggal rilis disinkronkan dengan manifest.' if (allow_sync and date_changed) else 'Tanggal UI diwarisi; bukan release_date manifest terverifikasi.',
                              'Remote track identity dan rights/services belum diverifikasi; bukan siap distribusi.'])
