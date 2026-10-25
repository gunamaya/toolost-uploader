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
        for mutate in ('album', 'multi', 'lyrics', 'label'):
            with self.subTest(mutate=mutate):
                data = copy.deepcopy(self.manifest)
                if mutate == 'album':
                    data['release_type'] = 'album'
                elif mutate == 'multi':
                    second = copy.deepcopy(data['tracks'][0])
                    second['track_id'] = 'second'
                    data['tracks'].append(second)
                elif mutate == 'lyrics':
                    data['tracks'][0]['lyrics'] = copy.deepcopy(data['tracks'][0]['audio'])
                else:
                    data['label'] = 'Synthetic label'
                path = self.base / 'other.json'
                path.write_text(json.dumps(data))
                with self.assertRaises(DraftError):
                    preflight(path)

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
        page.locator.return_value.count.return_value = 0
        record = Mock()
        ui = DraftUI(page, self.manifest, self.base, '123', record)
        ui.remote_id = '123'
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


if __name__ == '__main__':
    unittest.main()
