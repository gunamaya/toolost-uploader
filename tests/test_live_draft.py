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


if __name__ == '__main__':
    unittest.main()
