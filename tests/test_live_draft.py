import copy
import json
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

import test_storage
from toolost_uploader.live_draft import DraftError, DraftUI, execute, preflight, run_steps
from toolost_uploader.validation import InvalidInput


class LiveDraftTests(unittest.TestCase):
    setUp = test_storage.StorageTests.setUp

    def manifest_file(self):
        path = self.base / 'manifest.json'
        path.write_text(json.dumps(self.manifest))
        return path

    def test_preflight_minimal_and_hash(self):
        path = self.manifest_file()
        manifest, base = preflight(path)
        self.assertEqual(manifest, self.manifest)
        self.assertEqual(base, self.base)
        self.asset.write_bytes(b'changed')
        with self.assertRaises(InvalidInput):
            preflight(path)

    def test_unsupported_scope_rejected(self):
        for mutate in ('ep', 'compilation', 'label', 'single_multi'):
            with self.subTest(mutate=mutate):
                data = copy.deepcopy(self.manifest)
                if mutate == 'ep':
                    data['release_type'] = 'ep'
                elif mutate == 'compilation':
                    data['release_type'] = 'compilation'
                elif mutate == 'label':
                    data['label'] = 'Synthetic label'
                elif mutate == 'single_multi':
                    data['release_type'] = 'single'
                    second = copy.deepcopy(data['tracks'][0])
                    second['track_id'] = 'second'
                    data['tracks'].append(second)
                path = self.base / 'other.json'
                path.write_text(json.dumps(data))
                with self.assertRaises(DraftError):
                    preflight(path)

    def test_lyrics_preflight_supported(self):
        lyrics_file = self.base / 'lyrics.txt'
        lyrics_file.write_text('Bait satu\nBait dua\n', encoding='utf-8')
        import hashlib
        data = copy.deepcopy(self.manifest)
        data['tracks'][0]['lyrics'] = {
            'path': 'lyrics.txt',
            'sha256': hashlib.sha256(lyrics_file.read_bytes()).hexdigest()
        }
        path = self.base / 'with_lyrics.json'
        path.write_text(json.dumps(data))
        manifest, base = preflight(path)
        self.assertIn('lyrics', manifest['tracks'][0])
        self.assertEqual(manifest['tracks'][0]['lyrics']['path'], 'lyrics.txt')

    def test_album_and_multi_track_preflight_supported(self):
        data = copy.deepcopy(self.manifest)
        data['release_type'] = 'album'
        second = copy.deepcopy(data['tracks'][0])
        second['track_id'] = 'track_2'
        second['title'] = 'Second Track'
        data['tracks'].append(second)
        path = self.base / 'album.json'
        path.write_text(json.dumps(data))
        manifest, base = preflight(path)
        self.assertEqual(manifest['release_type'], 'album')
        self.assertEqual(len(manifest['tracks']), 2)
        self.assertEqual(base, self.base)

    def test_album_create_and_audio_multi_files(self):
        album_manifest = copy.deepcopy(self.manifest)
        album_manifest['release_type'] = 'album'
        track2 = copy.deepcopy(album_manifest['tracks'][0])
        track2['track_id'] = 't2'
        track2['title'] = 'Track Two'
        album_manifest['tracks'].append(track2)

        page = Mock()
        page.url = 'https://toolost.com/uploader/edit/123'
        page.is_closed.return_value = False
        page.locator.return_value.count.return_value = 0
        record = Mock()
        ui = DraftUI(page, album_manifest, self.base, '123', record)
        ui.remote_id = '123'
        ui.identity_verified = True

        # Test create() memilih Album button
        page.locator.return_value.get_by_role.return_value = Mock()
        dialog = Mock()
        page.get_by_role.return_value.filter.return_value = dialog
        ui.create()
        album_button_calls = [call for call in dialog.get_by_role.call_args_list if call.kwargs.get('name')]
        self.assertTrue(any(hasattr(c.kwargs['name'], 'search') and c.kwargs['name'].search('Album / 6+ tracks') for c in album_button_calls))

        # Test audio() set_files list 2 asset dan klik 'Upload 2 files'
        track_items = Mock()
        track_items.count.side_effect = [0, 2] # 0 existing before upload, 2 visible after upload
        def locator_se(selector):
            if 'track-item' in selector:
                return track_items
            return Mock(count=Mock(return_value=0))
        page.locator.side_effect = locator_se
        from unittest.mock import MagicMock
        chooser_mock = Mock()
        cm = MagicMock()
        cm.__enter__.return_value = chooser_mock
        page.expect_file_chooser.return_value = cm
        ui.audio()
        chooser_mock.value.set_files.assert_called_once()
        files_arg = chooser_mock.value.set_files.call_args[0][0]
        self.assertEqual(len(files_arg), 2)

    def test_album_metadata_and_readback_multi_tracks(self):
        album_manifest = copy.deepcopy(self.manifest)
        album_manifest['release_type'] = 'album'
        track2 = copy.deepcopy(album_manifest['tracks'][0])
        track2['track_id'] = 't2'
        track2['title'] = 'Track Two'
        track2['ai_assisted'] = False
        album_manifest['tracks'].append(track2)

        page = Mock()
        page.url = 'https://toolost.com/uploader/edit/123'
        page.is_closed.return_value = False
        page.locator.side_effect = lambda selector: Mock(count=Mock(return_value=0 if 'password' in selector else 2))
        record = Mock()
        ui = DraftUI(page, album_manifest, self.base, '123', record)
        ui.remote_id = '123'
        ui.identity_verified = True

        # Test metadata() mengisi semua track
        with patch.object(ui, 'editor') as mock_editor, patch.object(ui, 'metadata_open') as mock_open:
            ui.metadata()
            self.assertEqual(mock_editor.call_count, 2)
            self.assertEqual(mock_open.call_count, 2)

        # Test readback() membaca Album name dan kedua track
        page.get_by_role.return_value.input_value.side_effect = [
            album_manifest['title'],
            album_manifest['tracks'][0]['title'],
            album_manifest['tracks'][1]['title']
        ]
        with patch.object(ui, 'editor'), patch.object(ui, 'ai_switch') as ai:
            ai.return_value.get_attribute.side_effect = ['true', 'false']
            ui.readback()

        # Pastikan label textbox yang dicari adalah 'Album name', bukan 'Single name'
        role_calls = [c.kwargs.get('name') for c in page.get_by_role.call_args_list if c.args and c.args[0] == 'textbox']
        self.assertIn('Album name', role_calls)
        self.assertNotIn('Single name', role_calls)

    def test_confirmation_and_endpoint_checked_before_disk_or_browser(self):
        kwargs = dict(alias='test', expected_account='123', endpoint='http://127.0.0.1:9437',
                      approve_draft=True, accept_ui_date=True)
        for key, value in (('approve_draft', False), ('accept_ui_date', False),
                           ('expected_account', 'cookie'), ('endpoint', 'http://example.test:9437'),
                           ('endpoint', 'http://127.0.0.1:65536')):
            with self.subTest(key=key, value=value):
                with self.assertRaises(DraftError):
                    execute('DO-NOT-READ', **dict(kwargs, **{key: value}))
        self.assertFalse(self.root.exists())

    def make_ui(self):
        page = Mock()
        page.url = 'https://toolost.com/uploader/edit/123'
        page.is_closed.return_value = False
        page.locator.return_value.count.return_value = 0
        record = Mock()
        ui = DraftUI(page, self.manifest, self.base, '123', record)
        ui.remote_id = '123'
        ui.identity_verified = True
        return ui, page, record

    def test_intent_before_action_and_failure_stays_unknown(self):
        ui, page, record = self.make_ui()
        events = []
        record.side_effect = lambda *args: events.append(args[:2])
        def action():
            self.assertEqual(events, [('audio', 'unknown')])
            raise TimeoutError('private path and request')
        with self.assertRaises(TimeoutError):
            ui.action('audio', action)
        self.assertEqual(events, [('audio', 'unknown')])

    def test_journal_failure_prevents_mutation(self):
        ui, page, record = self.make_ui()
        record.side_effect = OSError('storage failed')
        operation = Mock()
        with self.assertRaises(OSError):
            ui.action('create', operation)
        operation.assert_not_called()

    def test_login_origin_and_target_guards(self):
        for url in ('https://toolost.com/login', 'https://evil.test/uploader/edit/123',
                    'https://toolost.com/uploader/edit/999'):
            ui, page, record = self.make_ui()
            page.url = url
            operation = Mock()
            with self.assertRaises(DraftError):
                ui.action('save', operation)
            operation.assert_not_called()
            record.assert_not_called()

    def test_matching_locked_title_does_not_fill_or_toggle_blindly(self):
        ui, page, record = self.make_ui()
        title = page.get_by_role.return_value
        title.is_editable.return_value = False
        title.input_value.return_value = self.manifest['tracks'][0]['title']
        switch = Mock()
        switch.get_attribute.return_value = 'true'
        with patch.object(ui, 'ai_switch', return_value=switch):
            ui.metadata_open()
        title.fill.assert_not_called()
        switch.locator.assert_not_called()

    def test_upload_button_names_allow_observed_subtitles(self):
        ui, page, _ = self.make_ui()
        page.expect_file_chooser.side_effect = RuntimeError('stop before file selection')
        with self.assertRaises(RuntimeError):
            ui.artwork()
        patterns = [call.kwargs.get('name') for call in page.get_by_role.call_args_list]
        self.assertTrue(any(hasattr(pattern, 'search') and pattern.search('Upload Artwork\nJPG, PNG, or TIFF') for pattern in patterns))

    def test_readback_does_not_require_release_title_heading(self):
        ui, page, _ = self.make_ui()
        page.get_by_role.return_value.input_value.side_effect = [self.manifest['title'], self.manifest['tracks'][0]['title']]
        page.locator.side_effect = lambda selector: Mock(count=Mock(return_value=0 if 'password' in selector else 1))
        with patch.object(ui, 'editor'), patch.object(ui, 'ai_switch') as ai:
            ai.return_value.get_attribute.return_value = 'true'
            ui.readback()
        self.assertFalse(any(call.args and call.args[0] == 'heading' for call in page.get_by_role.call_args_list))

    def test_readback_clicks_done_saves_and_returns_to_portal(self):
        ui, page, _ = self.make_ui()
        page.locator.side_effect = lambda selector: Mock(count=Mock(return_value=0 if 'password' in selector else 1), first=Mock())

        done_button = Mock()
        done_button.count.return_value = 1

        save_button = Mock()
        save_button.is_visible.return_value = True
        save_button.is_enabled.return_value = True

        create_button = Mock()

        title_mock = Mock()
        title_mock.input_value.return_value = self.manifest['title']
        track_title_mock = Mock()
        track_title_mock.input_value.return_value = self.manifest['tracks'][0]['title']

        def get_role_mock(role, name=None, exact=None):
            if role == 'button' and name == 'Done':
                return done_button
            if role == 'button' and name == 'Save Changes':
                return save_button
            if role == 'button' and name == 'Create New Release':
                return create_button
            if role == 'textbox' and name == 'Single name':
                return title_mock
            if role == 'textbox' and name == 'Track name':
                return track_title_mock
            return Mock()

        page.get_by_role.side_effect = get_role_mock

        with patch.object(ui, 'editor'), patch.object(ui, 'ai_switch') as ai:
            ai.return_value.get_attribute.return_value = 'true'
            ui.readback()

        # 1. Pastikan Done diklik pada track terakhir
        done_button.click.assert_called_once()
        # 2. Pastikan Save Changes diklik
        save_button.click.assert_called_once()
        # 3. Pastikan kembali ke portal releases
        goto_urls = [call.args[0] for call in page.goto.call_args_list if call.args]
        self.assertIn('https://toolost.com/user-portal/releases/manage/1', goto_urls)
        create_button.wait_for.assert_called_once_with(state='visible', timeout=30000)

    def test_asset_rehashed_before_chooser(self):
        ui, _, _ = self.make_ui()
        self.assertEqual(ui.asset(self.manifest['artwork']), str(self.asset))
        self.asset.write_bytes(b'wrong')
        with self.assertRaises(InvalidInput):
            ui.asset(self.manifest['artwork'])

    def test_disabled_track_title_mismatch_stops_before_ai_or_save(self):
        ui, page, record = self.make_ui()
        title = page.get_by_role.return_value
        title.is_editable.return_value = False
        title.input_value.return_value = 'Different release title'
        with self.assertRaisesRegex(DraftError, 'track_title_locked_mismatch'):
            ui.metadata_open()
        title.fill.assert_not_called()
        record.assert_not_called()

    def test_existing_modal_never_navigated_away(self):
        ui, page, _ = self.make_ui()
        page.url = 'https://toolost.com/user-portal/releases/manage/1'
        page.locator.side_effect = [Mock(count=Mock(return_value=0)), Mock(count=Mock(return_value=1))]
        with self.assertRaises(DraftError):
            ui.verify_account()
        page.goto.assert_not_called()

    def test_existing_editor_never_abandoned(self):
        ui, page, _ = self.make_ui()
        with self.assertRaises(DraftError):
            ui.verify_account()
        page.goto.assert_not_called()

    def test_runner_order_and_stop_without_retries(self):
        class UI:
            remote_id = 'synthetic'
            def __init__(self, failure=None):
                self.events = []
                self.failure = failure
            def verify_account(self):
                self.events.append('verify')
            def action(self, name, operation):
                self.events.append(name)
                if name == self.failure:
                    raise TimeoutError('unknown outcome')
            def readback(self):
                self.events.append('reopen')
            def record(self, name, state, remote):
                self.events.append(name)
            create = artwork = audio = metadata = save = lambda self: None
        ui = UI()
        run_steps(ui)
        self.assertEqual(ui.events, ['verify', 'create', 'artwork', 'audio', 'metadata', 'save', 'reopen', 'readback'])
        for fail in ('create', 'audio', 'save'):
            ui = UI(fail)
            with self.assertRaises(TimeoutError):
                run_steps(ui)
            self.assertEqual(ui.events[-1], fail)
            self.assertEqual(ui.events.count(fail), 1)
            self.assertNotIn('reopen', ui.events)

    def test_lyrics_fill_and_readback(self):
        lyrics_file = self.base / 'test_lyrics.txt'
        expected_text = 'Lirik baris satu\nLirik baris dua\n'
        lyrics_file.write_text(expected_text, encoding='utf-8')
        import hashlib
        data = copy.deepcopy(self.manifest)
        data['tracks'][0]['lyrics'] = {
            'path': 'test_lyrics.txt',
            'sha256': hashlib.sha256(lyrics_file.read_bytes()).hexdigest()
        }

        ui, page, _ = self.make_ui()
        ui.manifest = data

        title = Mock(is_editable=Mock(return_value=True), input_value=Mock(return_value=data['tracks'][0]['title']))
        lyrics_box = Mock(input_value=Mock(return_value=expected_text))
        lyrics_button = Mock()
        done_button = Mock()

        def role_se(role, name=None, exact=False):
            if role == 'textbox' and name == 'Track name':
                return title
            if role == 'textbox' and name == 'Lyrics':
                return lyrics_box
            if role == 'button' and name == 'Lyrics':
                return lyrics_button
            if role == 'button' and name == 'Done':
                return done_button
            if role == 'textbox' and name in ('Single name', 'Album name'):
                return Mock(input_value=Mock(return_value=data['title']))
            return Mock()

        page.get_by_role.side_effect = role_se

        switch = Mock()
        switch.get_attribute.return_value = 'true'
        with patch.object(ui, 'ai_switch', return_value=switch):
            ui.metadata_open(data['tracks'][0])

        lyrics_box.fill.assert_called_once_with(expected_text)

        # Test readback mismatch raises lyrics_readback_mismatch
        lyrics_box.input_value.return_value = 'Different text'
        page.locator.side_effect = lambda selector: Mock(count=Mock(return_value=0 if 'password' in selector else 1), first=Mock())
        with patch.object(ui, 'editor'), patch.object(ui, 'ai_switch', return_value=switch):
            with self.assertRaisesRegex(DraftError, 'lyrics_readback_mismatch'):
                ui.readback()

    def test_append_tracks_and_metadata(self):
        album_manifest = copy.deepcopy(self.manifest)
        album_manifest['release_type'] = 'album'
        track2 = copy.deepcopy(album_manifest['tracks'][0])
        track2['track_id'] = 'track-2'
        track2['title'] = 'Second Susulan'
        album_manifest['tracks'].append(track2)

        page = Mock()
        page.url = 'https://toolost.com/uploader/edit/123'
        page.is_closed.return_value = False

        # Locator mock
        track_items = Mock()
        track_items.count.side_effect = [1, 2, 2, 2] # 1 lama -> 2 total
        track_items.first = Mock()

        def locator_se(selector):
            if selector == '.track-item:visible':
                return track_items
            if selector == '.tl-upload-dialog:visible':
                return Mock(count=Mock(return_value=0))
            if '[role=dialog]' in selector:
                dlg = Mock()
                dlg.wait_for = Mock()
                dlg.get_by_text.return_value = Mock()
                dlg.get_by_role.return_value = Mock()
                return dlg
            return Mock(count=Mock(return_value=0))

        page.locator.side_effect = locator_se
        from unittest.mock import MagicMock
        chooser_mock = Mock()
        cm = MagicMock()
        cm.__enter__.return_value = chooser_mock
        page.expect_file_chooser.return_value = cm

        record = Mock()
        ui = DraftUI(page, album_manifest, self.base, '123', record)
        ui.remote_id = '123'
        ui.identity_verified = True

        ui.append_tracks([track2], expected_old_count=1)
        chooser_mock.value.set_files.assert_called_once()

        # Metadata append
        with patch.object(ui, 'editor') as mock_editor, patch.object(ui, 'metadata_open') as mock_meta_open:
            ui.metadata_append([track2], start_index=1)
            mock_editor.assert_called_once_with(1)
            mock_meta_open.assert_called_once_with(track2)

    def test_append_guard_validations(self):
        path = self.manifest_file()
        kwargs = dict(alias='test', expected_account='123', endpoint='http://127.0.0.1:9437',
                      approve_draft=True, accept_ui_date=True, root=self.root, allow_append=True)
        # 1. Single manifest ditolak saat allow_append=True
        with self.assertRaisesRegex(DraftError, 'append_requires_album'):
            execute(path, **kwargs)

        # 2. Album manifest tanpa existing checkpoint ditolak
        album_path = self.base / 'album.json'
        album_data = copy.deepcopy(self.manifest)
        album_data['release_type'] = 'album'
        album_path.write_text(json.dumps(album_data))
        with self.assertRaisesRegex(DraftError, 'append_requires_existing_checkpoint'):
            execute(album_path, **kwargs)

    def test_execute_append_full_flow(self):
        import hashlib
        album1 = copy.deepcopy(self.manifest)
        album1['release_type'] = 'album'
        manifest1_path = self.base / 'album1.json'
        manifest1_path.write_text(json.dumps(album1))

        # Checkpoint dan journal awal
        with test_storage.storage.profile('test', root=self.root) as session:
            chk1 = session.create_checkpoint(album1, self.base)
            from toolost_uploader.live_journal import LiveJournal, STAGES
            j = LiveJournal(session, chk1, '123', 'http://127.0.0.1:9437')
            for stage in STAGES:
                j.record(stage, 'unknown', None if stage == 'create' else '2009483')
                j.record(stage, 'observed', '2009483')
            j.record('readback', 'verified_subset', '2009483')

        # Siapkan manifest album dengan track ke-2
        track2_asset = self.base / 'track2.bin'
        track2_asset.write_bytes(b'track 2 sound')
        album2 = copy.deepcopy(album1)
        album2['tracks'].append({
            'track_id': 'track-2',
            'title': 'Track Dua Susulan',
            'audio': {'path': track2_asset.name, 'sha256': hashlib.sha256(b'track 2 sound').hexdigest()},
            'ai_assisted': False
        })
        manifest2_path = self.base / 'album2.json'
        manifest2_path.write_text(json.dumps(album2))

        # Mock browser Playwright
        import sys
        import types
        from unittest.mock import MagicMock
        factory = MagicMock()
        p1 = Mock()
        p1.url = 'https://toolost.com/user-portal/releases/manage/1'
        p1.is_closed.return_value = False
        p1.locator.return_value.count.return_value = 0
        factory.return_value.__enter__.return_value.chromium.connect_over_cdp.return_value.contexts = [
            types.SimpleNamespace(pages=[p1])
        ]
        module = types.ModuleType('playwright.sync_api')
        module.sync_playwright = factory
        env = patch.dict(sys.modules, {'playwright': types.ModuleType('playwright'), 'playwright.sync_api': module})

        with env, patch('toolost_uploader.live_draft.update_run_steps') as mock_update_steps:
            res = execute(manifest2_path, alias='test', expected_account='123', endpoint='http://127.0.0.1:9437',
                          approve_draft=True, accept_ui_date=True, root=self.root, allow_append=True)
            self.assertEqual(res['status'], 'draft_appended_subset')
            self.assertEqual(res['draft_id'], '2009483')
            mock_update_steps.assert_called_once()
            args, kwargs = mock_update_steps.call_args
            # ui, title_changed, date_changed, artwork_changed, tracks_to_append, tracks_to_update, old_count
            self.assertFalse(args[1]) # title_changed
            self.assertFalse(args[2]) # date_changed
            self.assertFalse(args[3]) # artwork_changed
            self.assertEqual(len(args[4]), 1) # tracks_to_append
            self.assertEqual(args[4][0]['title'], 'Track Dua Susulan')
            self.assertEqual(len(args[5]), 0) # tracks_to_update
            self.assertEqual(args[6], 1) # old_count

        # Verifikasi checkpoint di disk sudah ter-update ke revisi 2
        with test_storage.storage.profile('test', root=self.root) as session:
            chk_after = session.read_checkpoint('release-1')
            self.assertEqual(chk_after['revision'], 2)
            self.assertEqual(len(chk_after['manifest']['tracks']), 2)

    def test_update_title_date_artwork_full_flow(self):
        import hashlib
        album1 = copy.deepcopy(self.manifest)
        album1['release_type'] = 'album'
        with test_storage.storage.profile('test', root=self.root) as session:
            chk1 = session.create_checkpoint(album1, self.base)
            from toolost_uploader.live_journal import LiveJournal, STAGES
            j = LiveJournal(session, chk1, '123', 'http://127.0.0.1:9437')
            for stage in STAGES:
                j.record(stage, 'unknown', None if stage == 'create' else '2009483')
                j.record(stage, 'observed', '2009483')
            j.record('readback', 'verified_subset', '2009483')

        # Siapkan artwork baru
        art2 = self.base / 'art2.bin'
        art2.write_bytes(b'new artwork bytes')
        album_updated = copy.deepcopy(album1)
        album_updated['title'] = 'Judul Album Baru Terupdate'
        album_updated['release_date'] = '2027-05-20'
        album_updated['artwork'] = {'path': art2.name, 'sha256': hashlib.sha256(b'new artwork bytes').hexdigest()}
        album_updated['tracks'][0]['title'] = 'Judul Lagu Satu Diperbaiki'
        album_updated_path = self.base / 'album_updated.json'
        album_updated_path.write_text(json.dumps(album_updated))

        import sys, types
        from unittest.mock import MagicMock
        factory = MagicMock()
        p1 = Mock()
        p1.url = 'https://toolost.com/user-portal/releases/manage/1'
        p1.is_closed.return_value = False
        p1.locator.return_value.count.return_value = 0
        factory.return_value.__enter__.return_value.chromium.connect_over_cdp.return_value.contexts = [
            types.SimpleNamespace(pages=[p1])
        ]
        module = types.ModuleType('playwright.sync_api')
        module.sync_playwright = factory
        env = patch.dict(sys.modules, {'playwright': types.ModuleType('playwright'), 'playwright.sync_api': module})

        with env, patch('toolost_uploader.live_draft.update_run_steps') as mock_update_steps:
            res = execute(album_updated_path, alias='test', expected_account='123', endpoint='http://127.0.0.1:9437',
                          approve_draft=True, accept_ui_date=True, root=self.root, allow_update=True)
            self.assertEqual(res['status'], 'draft_updated_subset')
            self.assertEqual(res['draft_id'], '2009483')
            mock_update_steps.assert_called_once()
            args, _ = mock_update_steps.call_args
            # ui, title_changed, date_changed, artwork_changed, tracks_to_append, tracks_to_update, old_count
            self.assertTrue(args[1]) # title_changed
            self.assertTrue(args[2]) # date_changed
            self.assertTrue(args[3]) # artwork_changed
            self.assertEqual(len(args[4]), 0) # tracks_to_append
            self.assertEqual(len(args[5]), 1) # tracks_to_update
            self.assertEqual(args[5][0][1]['title'], 'Judul Lagu Satu Diperbaiki')

    def test_update_draft_already_up_to_date(self):
        album1 = copy.deepcopy(self.manifest)
        album1['release_type'] = 'album'
        manifest_path = self.base / 'album_same.json'
        manifest_path.write_text(json.dumps(album1))

        with test_storage.storage.profile('test', root=self.root) as session:
            chk1 = session.create_checkpoint(album1, self.base)
            from toolost_uploader.live_journal import LiveJournal, STAGES
            j = LiveJournal(session, chk1, '123', 'http://127.0.0.1:9437')
            for stage in STAGES:
                j.record(stage, 'unknown', None if stage == 'create' else '2009483')
                j.record(stage, 'observed', '2009483')
            j.record('readback', 'verified_subset', '2009483')

        res = execute(manifest_path, alias='test', expected_account='123', endpoint='http://127.0.0.1:9437',
                      approve_draft=True, accept_ui_date=True, root=self.root, allow_update=True)
        self.assertEqual(res['status'], 'draft_up_to_date')
        self.assertEqual(res['draft_id'], '2009483')


if __name__ == '__main__':
    unittest.main()
