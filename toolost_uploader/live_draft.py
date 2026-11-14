"""Executor Playwright draft-only bounded; tidak menyediakan aksi Publish."""

import re
import time
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit

from .storage import profile, StorageError
from .live_journal import DraftError, LiveJournal
from .validation import file_reference, load_manifest, validate_manifest, validate_manifest_structure, verified_bytes, BUFFER_LIMIT_BYTES, InvalidInput


def audio_timeout_ms(assets):
    size = sum(len(asset['buffer']) if isinstance(asset, dict) else Path(asset).stat().st_size for asset in assets)
    return min(1800000, max(240000, 120000 + (size * 1000 + 262143) // 262144))


def wait_for_audio(page, expected_total, timeout_ms):
    deadline = time.monotonic() + timeout_ms / 1000
    remaining = timeout_ms
    items = page.locator('.track-item:visible')
    dialog = page.locator('.tl-upload-dialog:visible')
    while True:
        count = items.count()
        if count > expected_total:
            raise DraftError('track_identity_ambiguous')
        dialog_visible = dialog.count() > 0 if count == expected_total else None
        complete = count == expected_total and not dialog_visible
        remaining = min(remaining, int((deadline - time.monotonic()) * 1000))
        if remaining <= 0:
            error = DraftError('audio_upload_timeout')
            error.track_count = count
            error.expected_track_count = expected_total
            error.dialog_visible = dialog_visible
            raise error
        if complete:
            return
        delay = min(500, remaining)
        page.wait_for_timeout(delay)
        remaining -= delay


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


def check_buffer_mode(path, *, serial_audio, bound_buffer, reconcile_only=False):
    if bound_buffer and not serial_audio:
        raise DraftError('bound_buffer_requires_serial_audio')
    if not bound_buffer or reconcile_only:
        return
    manifest, base = preflight(path)
    for reference in [manifest['artwork']] + [t['audio'] for t in manifest['tracks']]:
        candidate = Path(reference['path'])
        if not candidate.is_absolute():
            candidate = base / candidate
        if candidate.stat().st_size > BUFFER_LIMIT_BYTES:
            raise InvalidInput('buffer_limit_exceeded', 'Buffer Playwright dibatasi 50 MiB per aset; tidak memulai browser.')


def track_bindings(tracks):
    return [(t['track_id'], t['audio']['sha256']) for t in tracks]


class DraftUI:
    def __init__(self, page, manifest, base, expected_account, record, log=None, *, serial_audio=False, bound_buffer=False, record_track=None):
        self.page, self.manifest, self.base = page, deepcopy(manifest), base
        self.expected_account, self.record = expected_account, record
        self.log = log or (lambda msg: None)
        self.serial_audio = serial_audio
        self.bound_buffer = bound_buffer
        self.record_track = record_track
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
        try:
            operation()
        except InvalidInput as exc:
            raise DraftError('asset_invalid_after_intent_requires_reconciliation') from exc
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
        self.click(name_dialog.get_by_role('button', name=re.compile(r'^(?:Create Release|Continue)$')))
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
        path = Path(reference['path'])
        if self.bound_buffer:
            mime = {'.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.flac': 'audio/flac',
                    '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}.get(path.suffix.lower())
            if mime is None:
                raise DraftError('unsupported_buffer_format')
            data = verified_bytes(reference, self.base)
            return dict(name=path.name, mimeType=mime, buffer=data)
        file_reference(reference, self.base)
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
        self.log('Mengunggah artwork terverifikasi...')
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
            raise DraftError('track_identity_ambiguous')
        count = items.count()
        if type(count) is not int or count != len(self.manifest['tracks']):
            raise DraftError('track_identity_ambiguous')
        stems = [Path(t['audio']['path']).stem.lower() for t in self.manifest['tracks']]
        if not hasattr(self, 'recovery_labels') and len(set(stems)) != len(stems):
            raise DraftError('track_identity_ambiguous')
        labels = {}
        for index, track in enumerate(self.manifest['tracks']):
            choices = getattr(self, 'recovery_labels', None)
            for label in ((choices[track['track_id']].lower(),) if choices is not None else
                          (stems[index], Path(track['audio']['path']).name.lower())):
                if label in labels and labels[label] != index:
                    raise DraftError('track_identity_ambiguous')
                labels[label] = index

        def read_order():
            if items.count() != count:
                raise DraftError('track_identity_ambiguous')
            order = []
            for i in range(count):
                text = items.nth(i).text_content().lower()
                # Portal text combines ordinal, filename and Edit without whitespace.
                prefix = str(i + 1)
                text = text.lstrip()
                if not text.startswith(prefix):
                    raise DraftError('track_identity_ambiguous')
                label = text[len(prefix):].strip()
                label = re.sub(r'\s*edit\s*$', '', label).strip()
                if label not in labels:
                    raise DraftError('track_identity_ambiguous')
                order.append(labels[label])
            if len(set(order)) != count:
                raise DraftError('track_identity_ambiguous')
            return order

        order = read_order()
        for target in range(count):
            actual = order.index(target)
            while actual > target:
                self.guard_target()
                source = items.nth(actual).locator('.track-item__drag')
                destination = items.nth(actual - 1)
                destination.evaluate("e => e.scrollIntoView({block: 'center', inline: 'nearest', behavior: 'instant'})")
                handle = source.bounding_box()
                box = destination.bounding_box()
                if not handle or not box:
                    raise DraftError('track_reorder_failed')
                safe = self.page.evaluate('''({sx, sy, dx, dy}) => {
                    const usable = (x, y) => x >= 0 && x < innerWidth && y >= 64 && y < innerHeight - 16;
                    const source = document.elementFromPoint(sx, sy);
                    const destination = document.elementFromPoint(dx, dy);
                    return usable(sx, sy) && usable(dx, dy) &&
                        !!source?.closest('.track-item__drag') && !!destination?.closest('.track-item');
                }''', {'sx': handle['x'] + handle['width'] / 2, 'sy': handle['y'] + handle['height'] / 2,
                       'dx': box['x'] + box['width'] / 2, 'dy': box['y'] + 5})
                if safe is not True:
                    raise DraftError('track_reorder_target_not_visible')
                self.page.mouse.move(handle['x'] + handle['width'] / 2, handle['y'] + handle['height'] / 2)
                self.page.mouse.down()
                try:
                    self.page.mouse.move(box['x'] + box['width'] / 2, box['y'] + 5, steps=10)
                finally:
                    self.page.mouse.up()
                self.page.wait_for_timeout(1000)
                expected = order[:]
                expected.insert(actual - 1, expected.pop(actual))
                order = read_order()
                if order != expected:
                    raise DraftError('track_reorder_failed')
                actual -= 1

    def audio(self):
        if not self.serial_audio:
            return self._audio_batch(self.manifest['tracks'])
        self._serial_tracks(self.manifest['tracks'], 0)

    def _serial_tracks(self, tracks, expected_old_count):
        if self.record_track is None:
            raise DraftError('track_journal_required')
        for offset, track in enumerate(tracks):
            count = expected_old_count + offset
            index = next(i for i, item in enumerate(self.manifest['tracks']) if item['track_id'] == track['track_id'])
            self.record_track(track['track_id'], track['audio']['sha256'], index, 'unknown')
            if count == 0:
                self._audio_batch([track], reorder=False)
            else:
                self._append_batch([track], count, reorder=False)
            self.record_track(track['track_id'], track['audio']['sha256'], index, 'observed')
        self.reorder_tracks()

    def _audio_batch(self, tracks, *, reorder=True):
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
        assets = [self.asset(t['audio']) for t in tracks]
        timeout_ms = audio_timeout_ms(assets)
        self.guard_target()
        self.log(f'Mengunggah {len(assets)} file audio track...')
        chooser.value.set_files(assets[0] if len(assets) == 1 else assets, timeout=timeout_ms)
        count = len(assets)
        btn_regex = r'^Upload\s+1\s+file' if count == 1 else rf'^Upload\s+{count}\s+files'
        self.click(dialog.get_by_role('button', name=re.compile(btn_regex, re.I)))
        self.log(f'Menunggu transfer dan encoding {count} file audio selesai...')
        wait_for_audio(page, count, timeout_ms)
        self.log('Unggahan berkas audio selesai. Memeriksa urutan track...')
        if reorder:
            self.reorder_tracks()

    def append_tracks(self, new_tracks, expected_old_count):
        if self.serial_audio:
            return self._serial_tracks(new_tracks, expected_old_count)
        return self._append_batch(new_tracks, expected_old_count)

    def _append_batch(self, new_tracks, expected_old_count, *, reorder=True):
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
        timeout_ms = audio_timeout_ms(assets)
        self.guard_target()
        self.log(f'Mengunggah {len(assets)} file audio track susulan...')
        chooser.value.set_files(assets[0] if len(assets) == 1 else assets, timeout=timeout_ms)
        count = len(assets)
        btn_regex = r'^Upload\s+1\s+file' if count == 1 else rf'^Upload\s+{count}\s+files'
        self.click(dialog.get_by_role('button', name=re.compile(btn_regex, re.I)))
        self.log(f'Menunggu transfer dan encoding {count} file audio susulan selesai...')
        expected_total = expected_old_count + count
        wait_for_audio(page, expected_total, timeout_ms)
        self.log('Unggahan berkas audio susulan selesai. Memeriksa urutan track...')
        if reorder:
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

    def sync_metadata_and_order(self):
        self.reorder_tracks()
        total = len(self.manifest['tracks'])
        for i, track in enumerate(self.manifest['tracks']):
            self.log(f"Menyinkronkan metadata track {i + 1}/{total}: '{track['title']}' (AI: {track['ai_assisted']})...")
            self.editor(i)
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
        return verified_bytes(track['lyrics'], self.base, lyrics=True).decode('utf-8')

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


def normal_upload_audio(ui, journal, observe, *, observe_active=None):
    from .remote_binding import observed_upload_mapping, prepare_binding

    journal.read()
    if journal.value['events']:
        raise DraftError('new_upload_unknown_requires_review')
    if observe_active is not None:
        return _normal_upload_active(ui, journal, observe_active)
    before = observe()
    if before:
        raise DraftError('unexpected_existing_tracks')
    journal.append('new_upload_baseline', 'observed', snapshot=[], mapping={})
    mapping = {}
    groups = [[t] for t in ui.manifest['tracks']] if ui.serial_audio else [ui.manifest['tracks']]
    for selected in groups:
        journal.append('upload', 'unknown')
        if ui.serial_audio:
            track = selected[0]
            index = ui.manifest['tracks'].index(track)
            ui.record_track(track['track_id'], track['audio']['sha256'], index, 'unknown')
        if before:
            ui._append_batch(selected, len(before), reorder=False)
        else:
            ui._audio_batch(selected, reorder=False)
        after = observe()
        retained = [t for t in after if str(t['id']) in mapping.values()]
        prior = prepare_binding(manifest=ui.manifest, account=journal.binding['account'],
                                draft=ui.remote_id, tracks=retained, mapping=mapping)
        if prior['snapshot'] != journal.value['snapshot']:
            raise DraftError('new_upload_binding_requires_review')
        mapping.update(observed_upload_mapping(ui.manifest, before, after, selected))
        review = prepare_binding(manifest=ui.manifest, account=journal.binding['account'],
                                 draft=ui.remote_id, tracks=after, mapping=mapping)
        if review['unmapped_remote_ids']:
            raise DraftError('new_upload_binding_requires_review')
        journal.append('upload', 'observed', snapshot=review['snapshot'], mapping=mapping)
        if ui.serial_audio:
            ui.record_track(track['track_id'], track['audio']['sha256'], index, 'observed')
        before = after
    ui.recovery_labels = {local: next(t['title'] for t in before if str(t['id']) == remote)
                          for local, remote in mapping.items()}
    ui.reorder_tracks()


def _normal_upload_active(ui, journal, observe):
    from .remote_binding import observed_upload_mapping

    before = observe()
    if before:
        raise DraftError('unexpected_existing_tracks')
    journal.append('new_upload_baseline', 'observed', snapshot=[], mapping={})
    groups = [[t] for t in ui.manifest['tracks']] if ui.serial_audio else [ui.manifest['tracks']]
    local = {}
    for selected in groups:
        journal.append('upload', 'unknown')
        if ui.serial_audio:
            track = selected[0]
            index = ui.manifest['tracks'].index(track)
            ui.record_track(track['track_id'], track['audio']['sha256'], index, 'unknown')
        if before:
            ui._append_batch(selected, len(before), reorder=False)
        else:
            ui._audio_batch(selected, reorder=False)
        after = observe()
        by_key = {str(t['editor_key']): t for t in after}
        if any(by_key.get(str(t['editor_key'])) != t for t in before):
            raise DraftError('new_upload_binding_requires_review')
        # These are client keys, never persisted remote IDs or source hashes.
        adapted = lambda rows: [dict(t, id=str(t['editor_key'])) for t in rows]
        delta = observed_upload_mapping(ui.manifest, adapted(before), adapted(after), selected)
        local.update(delta)
        snapshot = [dict(by_key[key], local_track_id=track_id) for track_id, key in local.items()]
        journal.append('new_upload_unsaved_labels', 'observed', snapshot=snapshot, mapping={})
        if ui.serial_audio:
            ui.record_track(track['track_id'], track['audio']['sha256'], index, 'observed')
        before = after
    ui.recovery_labels = {track_id: by_key[key]['title'] for track_id, key in local.items()}
    ui.reorder_tracks()


def finalize_normal_upload(ui, journal, observe):
    from .remote_binding import prepare_binding

    tracks = observe()
    wanted = ui.manifest['tracks']
    ordered = sorted(tracks, key=lambda t: t['track_order'])
    if (len(ordered) != len(wanted)
            or any(t['title'] != w['title'] for t, w in zip(ordered, wanted))):
        raise DraftError('new_upload_saved_binding_requires_review')
    mapping = {w['track_id']: str(t['id']) for t, w in zip(ordered, wanted)}
    review = prepare_binding(manifest=ui.manifest, account=journal.binding['account'],
                             draft=ui.remote_id, tracks=tracks, mapping=mapping)
    if review['unmapped_remote_ids'] or review['missing_track_ids']:
        raise DraftError('new_upload_saved_binding_requires_review')
    journal.append('new_upload_saved_binding', 'observed', snapshot=review['snapshot'], mapping=mapping)


def recover_active_audio_timeout(ui, journal, observe_active):
    """Continue one timed-out upload only when the dirty editor is complete.

    This deliberately stays on the current editor.  Client row keys are used
    only for the in-memory label map; they are never treated as persisted IDs.
    """
    from .remote_binding import observed_upload_mapping
    journal.read()
    events = journal.value['events']
    if (not events or events[0] != dict(operation='new_upload_baseline', outcome='observed', track_id=None)
            or any(e['operation'] not in ('new_upload_baseline', 'upload', 'new_upload_unsaved_labels') for e in events)
            or sum(e['operation'] == 'new_upload_baseline' for e in events) != 1
            or not any(e['operation'] == 'upload' and e['outcome'] == 'unknown' for e in events)):
        raise DraftError('active_recovery_stage_requires_review')
    rows = observe_active()
    wanted = ui.manifest['tracks']
    if len(rows) != len(wanted) or not rows:
        raise DraftError('active_upload_incomplete_requires_review')
    keys, titles = set(), set()
    for row in rows:
        if (row.get('audio_present') is not True or not isinstance(row.get('title'), str)
                or type(row.get('editor_key')) not in (str, int)):
            raise DraftError('active_upload_incomplete_requires_review')
        key, title = str(row['editor_key']), row['title'].strip().casefold()
        if not key or key in keys or not title or title in titles:
            raise DraftError('active_upload_ambiguous_requires_review')
        keys.add(key)
        titles.add(title)
    local_ids = [t['track_id'] for t in wanted]
    if len(set(local_ids)) != len(wanted) or len({t['title'].casefold() for t in wanted}) != len(wanted):
        raise DraftError('active_upload_ambiguous_requires_review')
    by_key = {str(row['editor_key']): row for row in rows}
    for prior in journal.value.get('snapshot') or []:
        actual = by_key.get(str(prior.get('editor_key')))
        if actual != {k: v for k, v in prior.items() if k != 'local_track_id'}:
            raise DraftError('active_upload_snapshot_changed')
    adapted = [dict(row, id=str(row['editor_key'])) for row in rows]
    mapping = observed_upload_mapping(ui.manifest, [], adapted, wanted)
    if observe_active() != rows:
        raise DraftError('active_upload_snapshot_changed')
    snapshot = [dict(by_key[key], local_track_id=local) for local, key in mapping.items()]
    journal.append('new_upload_unsaved_labels', 'observed', snapshot=snapshot, mapping={})
    ui.recovery_labels = {local: by_key[key]['title'] for local, key in mapping.items()}


def run_steps(ui, *, audio_operation=None, before_metadata=None, after_save=None):
    ui.verify_account()
    for name in ('create', 'artwork', 'audio', 'metadata', 'save'):
        if name == 'metadata' and before_metadata is not None:
            before_metadata()
        ui.action(name, audio_operation if name == 'audio' and audio_operation is not None else getattr(ui, name))
        if name == 'save' and after_save is not None:
            after_save()
    ui.readback()
    ui.record('readback', 'verified_subset', ui.remote_id)


def update_run_steps(ui, title_changed, date_changed, artwork_changed, tracks_to_upload, old_count):
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

    if tracks_to_upload:
        ui.action('append_audio', lambda: ui.append_tracks(tracks_to_upload, old_count))

    ui.action('update_metadata', lambda: ui.sync_metadata_and_order())

    ui.action('save', ui.save)
    ui.readback()
    ui.record('readback', 'verified_subset', ui.remote_id)


def append_run_steps(ui, new_tracks, old_count):
    return update_run_steps(ui, False, False, False, new_tracks, old_count)


def execute(path, *, alias, expected_account, endpoint, approve_draft, accept_ui_date, root=None,
            resume_before_artwork=False, resume_before_audio=False, resume_selected_audio=False,
            resume_open_metadata=False, approve_release_title_amendment=False, reconcile_only=False,
            allow_append=False, allow_update=False, log=None, serial_audio=False, bound_buffer=False):
    if bound_buffer and not serial_audio:
        raise DraftError('bound_buffer_requires_serial_audio')
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
    check_buffer_mode(path, serial_audio=serial_audio, bound_buffer=bound_buffer, reconcile_only=reconcile_only)
    # Recovered drafts have their own authoritative ID-bound lifecycle. Do not
    # reinterpret the unresolved legacy journal as permission to replay it.
    if allow_sync:
        from .recovery_state import read_successor
        with profile(alias, root=root) as session:
            successor = read_successor(session, manifest['release_id'], expected_account, endpoint)
        if successor is not None:
            result = recover(path, alias=alias, expected_account=expected_account,
                             draft_id=successor['draft'], endpoint=endpoint,
                             approve_draft=approve_draft, accept_ui_date=accept_ui_date,
                             root=root, log=log)
            result['status'] = 'draft_updated_subset'
            return result
    with profile(alias, root=root) as session:
        is_existing = False
        try:
            old_checkpoint = session.read_checkpoint(manifest['release_id'])
            is_existing = True
        except StorageError as error:
            if str(error) != 'checkpoint_not_found':
                raise DraftError('checkpoint_unreadable_requires_reconciliation') from error
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
            artwork_changed = (manifest['artwork']['sha256'] != old_manifest['artwork']['sha256'])

            old_tracks = old_manifest.get('tracks', [])
            new_tracks = manifest.get('tracks', [])
            old_count = len(old_tracks)
            new_count = len(new_tracks)

            new_hashes = [t['audio']['sha256'] for t in new_tracks]
            if len(new_hashes) != len(set(new_hashes)):
                raise DraftError('duplicate_audio_hash_requires_review')
            old_audio_hashes = {t['audio']['sha256'] for t in old_tracks}
            tracks_to_upload = [t for t in new_tracks if t['audio']['sha256'] not in old_audio_hashes]

            has_changes = (manifest != old_manifest)

            journal = LiveJournal(session, old_checkpoint, expected_account, endpoint, existing=True)
            remote_id = journal.require_reconciliation()

            if not has_changes:
                if log:
                    log("Draft rilis sudah up-to-date; tidak ada perubahan metadata atau track yang diperlukan.")
                return dict(status='draft_up_to_date', run_id=old_checkpoint['run_id'], draft_id=remote_id,
                            warnings=['Manifest identik dengan checkpoint rilis tersimpan.'])

            if journal.value.get('track_events') and track_bindings(manifest['tracks'][:len(old_tracks)]) != track_bindings(old_tracks):
                raise DraftError('serial_checkpoint_reorder_requires_review')
            journal.begin_sync()
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
            ui = DraftUI(page, journal.effective_manifest(), base, expected_account, record, log=log,
                         serial_audio=serial_audio, bound_buffer=bound_buffer, record_track=journal.record_track)
            ui.read_only = reconcile_only
            try:
                if reconcile_only:
                    ui.verify_account()
                    ui.remote_id = remote_id
                    ui.readback()
                    journal.verify_readback()
                elif allow_sync:
                    ui.remote_id = remote_id
                    update_run_steps(ui, title_changed, date_changed, artwork_changed, tracks_to_upload, old_count)
                else:
                    from .live_journal import RecoveryJournal
                    from .remote_binding import observe_release, observe_active_editor
                    upload_journals = []
                    def upload_with_binding():
                        recovery_journal = RecoveryJournal(session, ui.manifest, expected_account, ui.remote_id, endpoint)
                        upload_journals.append(recovery_journal)
                        normal_upload_audio(ui, recovery_journal,
                            lambda: observe_release(page.context, account=expected_account, draft=ui.remote_id),
                            observe_active=lambda: observe_active_editor(page, account=expected_account, draft=ui.remote_id))
                    def before_metadata():
                        if upload_journals:
                            upload_journals[0].append('metadata_save', 'unknown')
                    def after_save():
                        if upload_journals:
                            finalize_normal_upload(ui, upload_journals[0],
                                lambda: observe_release(page.context, account=expected_account, draft=ui.remote_id))
                    run_steps(ui, audio_operation=upload_with_binding,
                              before_metadata=before_metadata, after_save=after_save)
            except Exception as error:
                remote_id = journal.value.get('remote_draft_id') or ui.remote_id
                if remote_id:
                    error.remote_draft_id = remote_id
                raise
            finally:
                ui.close()
        out_status = 'draft_readback_subset' if reconcile_only else ('draft_appended_subset' if (allow_append and not title_changed and not artwork_changed and not date_changed) else ('draft_updated_subset' if allow_sync else 'draft_saved_subset'))
        return dict(status=out_status,
                    run_id=checkpoint['run_id'], draft_id=ui.remote_id,
                    warnings=['Tanggal rilis disinkronkan dengan manifest.' if (allow_sync and date_changed) else 'Tanggal UI diwarisi; bukan release_date manifest terverifikasi.',
                              'Remote track identity dan rights/services belum diverifikasi; bukan siap distribusi.'])


def recovery_steps(ui, journal, receipt, observe):
    """Upload serial dengan ID baru dicatat sebelum metadata, tanpa replay unknown."""
    from .remote_binding import prepare_binding

    def snapshot(tracks, mapping):
        review = prepare_binding(manifest=ui.manifest, account=receipt['account'],
                                 draft=receipt['draft'], tracks=tracks, mapping=mapping)
        if review['unmapped_remote_ids']:
            raise DraftError('remote_binding_unmapped_tracks')
        return review['snapshot']

    journal.read()
    events = journal.value['events']
    if any('editor_key' in t for t in journal.value.get('snapshot') or []):
        raise DraftError('deferred_upload_binding_requires_review')
    pending = bool(events and events[-1]['outcome'] == 'unknown')
    if pending and events[-1]['operation'] == 'upload':
        # Bahkan snapshot kosong tidak membuktikan transfer lama batal di server.
        # Review baru oleh manusia wajib sebelum memulai attempt pengganti.
        if journal.value.get('approval_digest') == receipt['review_digest']:
            raise DraftError('recovery_upload_unknown_requires_review')
    elif pending and journal.value.get('approval_digest') == receipt['review_digest']:
        raise DraftError('recovery_outcome_unknown_requires_review')
    mapping = dict(receipt['mapping'])
    expected = receipt['snapshot']
    if journal.value.get('approval_digest') == receipt['review_digest'] and journal.value['snapshot'] is not None:
        mapping = dict(journal.value['mapping'])
        expected = journal.value['snapshot']
    tracks = observe()
    if snapshot(tracks, mapping) != expected:
        raise DraftError('remote_binding_review_changed')
    if events and events[-1]['operation'] == 'complete' and journal.value.get('approval_digest') == receipt['review_digest']:
        return
    journal.append('review', 'observed', snapshot=expected, mapping=mapping,
                   approval_digest=receipt['review_digest'])

    def fresh():
        current = observe()
        if snapshot(current, mapping) != journal.value['snapshot']:
            raise DraftError('remote_binding_review_changed')
        return current

    for track in ui.manifest['tracks']:
        if track['track_id'] in mapping:
            continue
        tracks = fresh()
        journal.append('upload', 'unknown', track_id=track['track_id'])
        if tracks:
            ui._append_batch([track], len(tracks), reorder=False)
        else:
            ui._audio_batch([track], reorder=False)
        after = observe()
        before_ids = {str(t['id']) for t in tracks}
        added = [t for t in after if str(t['id']) not in before_ids]
        retained = [t for t in after if str(t['id']) in before_ids]
        if len(added) != 1 or snapshot(retained, mapping) != journal.value['snapshot']:
            raise DraftError('recovery_upload_unknown_requires_review')
        mapping[track['track_id']] = str(added[0]['id'])
        current = snapshot(after, mapping)
        journal.append('upload', 'observed', snapshot=current, mapping=mapping, track_id=track['track_id'])

    tracks = fresh()
    by_id = {str(t['id']): t for t in tracks}
    ui.recovery_labels = {local: by_id[remote]['title'] for local, remote in mapping.items()}
    journal.append('metadata_save', 'unknown')
    ui.click(ui.page.get_by_role('button', name='Manage Tracks', exact=True))
    ui.sync_metadata_and_order()
    ui.update_title()
    ui.click(ui.page.get_by_role('button', name='Artwork', exact=True))
    if ui.page.locator('.artwork-selected').count() == 0:
        ui.artwork()
    # Metadata/reorder hanyalah state UI sampai Save. Tidak refresh receipt dari
    # tebakan judul: ID, audio URL, judul dan urutan harus cocok hasil operasi ini.
    fresh()
    ui.save()
    after = observe()
    actual = snapshot(after, mapping)
    old_audio = {t['id']: t['audio_url_sha256'] for t in journal.value['snapshot']}
    ordered = sorted(actual, key=lambda t: t['track_order'])
    wanted = ui.manifest['tracks']
    if (len(ordered) != len(wanted) or any(t['audio_url_sha256'] != old_audio.get(t['id']) for t in actual)
            or any(t['id'] != mapping[w['track_id']] or t['title'] != w['title'] for t, w in zip(ordered, wanted))):
        raise DraftError('recovery_saved_snapshot_mismatch')
    journal.append('metadata_save', 'observed', snapshot=actual, mapping=mapping)
    ui.read_only = True
    ui.readback()
    fresh()
    journal.append('complete', 'observed')


def recover(path, *, alias, expected_account, draft_id, endpoint, approve_draft,
            accept_ui_date, root=None, log=None, active_audio_timeout=False):
    from .live_journal import RecoveryJournal
    from .remote_binding import load_receipt, observe_release
    if approve_draft is not True or accept_ui_date is not True:
        raise DraftError('confirmation_required')
    if any(not isinstance(x, str) or not re.fullmatch(r'[1-9][0-9]*', x) for x in (expected_account, draft_id)):
        raise DraftError('recovery_identity_unverified')
    if not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{1,5}', endpoint) or not 1024 <= int(endpoint.rsplit(':', 1)[1]) <= 65535:
        raise DraftError('loopback_endpoint_required')
    manifest, base = preflight(path)
    if active_audio_timeout:
        return recover_active_editor(manifest, base, alias=alias, expected_account=expected_account,
                                     draft_id=draft_id, endpoint=endpoint, root=root, log=log)
    with profile(alias, root=root) as session:
        receipt = load_receipt(session, manifest, expected_account, draft_id)
        # Existing checkpoints are never replaced or removed by this command.
        try:
            checkpoint = session.read_checkpoint(manifest['release_id'])
        except StorageError as error:
            if str(error) != 'checkpoint_not_found':
                raise
        else:
            if checkpoint['state'] != 'validated':
                raise DraftError('resume_manifest_mismatch')
            # Receipt binds the reviewed replacement; legacy integrity stays bound
            # to its original checkpoint, never the new GUI asset snapshot.
            from .storage import _read
            try:
                old = _read(session.directory, manifest['release_id'] + '.live.json')
            except FileNotFoundError:
                old = None
            if old is not None:
                journal_old = LiveJournal(session, checkpoint, expected_account, endpoint, existing=True)
                if journal_old.value['remote_draft_id'] != draft_id:
                    raise DraftError('draft_target_changed')
        journal = RecoveryJournal(session, manifest, expected_account, draft_id, endpoint, receipt=receipt)
        from playwright.sync_api import sync_playwright
        from .browser import is_local_endpoint
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(endpoint, is_local=is_local_endpoint(endpoint))
            if len(browser.contexts) != 1:
                raise DraftError('recovery_context_not_unique')
            context = browser.contexts[0]
            tracks = observe_release(context, account=expected_account, draft=draft_id)
            page = context.new_page()
            ui = DraftUI(page, manifest, base, expected_account, lambda *a: None, log=log)
            ui.remote_id = draft_id
            try:
                ui.read_only = True
                page.goto('https://toolost.com/uploader/edit/' + draft_id, wait_until='domcontentloaded', timeout=30000)
                # Identity came from a same-context authenticated page load, not cookies.
                ui.identity_verified = True
                ui.guard_target()
                page.get_by_role('button', name='Save Changes', exact=True).wait_for(state='visible', timeout=30000)
                if page.locator('[role=dialog]:visible,[aria-modal=true]:visible').count():
                    raise DraftError('existing_dialog_requires_review')
                ui.read_only = False
                recovery_steps(ui, journal, receipt,
                               lambda: observe_release(context, account=expected_account, draft=draft_id))
            finally:
                ui.close()
                page.close()
        from .recovery_state import save_successor
        save_successor(session, manifest, expected_account, draft_id, endpoint, journal.read())
        return dict(status='draft_recovered_subset', draft_id=draft_id,
                    remote_audio_hashes_verified=False, warnings=['Binding ID disetujui pengguna, bukan kesamaan byte audio remote.',
                    'Tanggal UI diwarisi; rights/services belum diverifikasi; tidak Publish.'])


def active_editor_recovery_steps(ui, live, journal, observe_active, observe_saved):
    """Bounded continuation of audio only; metadata/Save intents cannot replay."""
    value = live.read()
    expected = [(name, outcome) for name in ('create', 'artwork') for outcome in ('unknown', 'observed')]
    expected.append(('audio', 'unknown'))
    if ([(e['operation'], e['outcome']) for e in value['events']] != expected
            or value['remote_draft_id'] != ui.remote_id or value.get('track_events')
            or value.get('sync_pending')):
        raise DraftError('active_recovery_stage_requires_review')
    journal.read()
    if any(e['operation'] in ('metadata_save', 'active_metadata_save', 'complete') for e in journal.value['events']):
        raise DraftError('active_recovery_stage_requires_review')
    recover_active_audio_timeout(ui, journal, observe_active)
    # Persist the no-replay barrier before reorder, metadata, or Save.
    journal.append('active_metadata_save', 'unknown')
    ui.click(ui.page.get_by_role('button', name='Manage Tracks', exact=True))
    ui.sync_metadata_and_order()
    ui.save()
    finalize_normal_upload(ui, journal, observe_saved)
    ui.read_only = True
    ui.readback()
    journal.append('complete', 'observed')


def recover_active_editor(manifest, base, *, alias, expected_account, draft_id, endpoint, root=None, log=None):
    from .live_journal import RecoveryJournal
    from .remote_binding import observe_active_editor, observe_release
    from .recovery_inspection import verify_open_draft_account
    from .storage import _read
    with profile(alias, root=root) as session:
        checkpoint = session.read_checkpoint(manifest['release_id'])
        live = LiveJournal(session, checkpoint, expected_account, endpoint, existing=True)
        if live.effective_manifest() != manifest or live.value['remote_draft_id'] != draft_id:
            raise DraftError('active_recovery_manifest_or_target_mismatch')
        # A recovery ledger from this upload is mandatory; never synthesize one
        # for an arbitrary dirty editor just because its titles happen to match.
        _read(session.directory, manifest['release_id'] + '.recovery.json')
        journal = RecoveryJournal(session, manifest, expected_account, draft_id, endpoint)
        from playwright.sync_api import sync_playwright
        from .browser import is_local_endpoint
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(endpoint, is_local=is_local_endpoint(endpoint))
            if len(browser.contexts) != 1:
                raise DraftError('recovery_context_not_unique')
            context = browser.contexts[0]
            pages = [p for p in context.pages if not p.is_closed() and p.url == 'https://toolost.com/uploader/edit/' + draft_id]
            if len(pages) != 1:
                raise DraftError('recovery_page_not_unique')
            page = pages[0]
            verify_open_draft_account(page, expected_account=expected_account, expected_draft=draft_id)
            if page.locator('.tl-upload-dialog:visible').count():
                raise DraftError('existing_dialog_requires_review')
            ui = DraftUI(page, manifest, base, expected_account, lambda *a: None, log=log)
            ui.remote_id, ui.identity_verified = draft_id, True
            def active():
                verify_open_draft_account(page, expected_account=expected_account, expected_draft=draft_id)
                ui.guard_target()
                return observe_active_editor(page, account=expected_account, draft=draft_id)
            try:
                active_editor_recovery_steps(ui, live, journal, active,
                    lambda: observe_release(context, account=expected_account, draft=draft_id))
            except Exception as error:
                error.remote_draft_id = draft_id
                raise
            finally:
                ui.close()
        from .recovery_state import save_successor
        save_successor(session, manifest, expected_account, draft_id, endpoint, journal.read())
        return dict(status='draft_recovered_subset', draft_id=draft_id, retry_safe=False,
                    remote_audio_hashes_verified=False, recovery_mode='active_audio_timeout')
