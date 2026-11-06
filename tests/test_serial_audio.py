import copy
import hashlib
import json
import unittest
from unittest.mock import Mock

import test_storage
from toolost_uploader.live_draft import DraftUI, DraftError, execute
from toolost_uploader.live_journal import LiveJournal, STAGES
from toolost_uploader.storage import profile
from toolost_uploader.validation import verified_bytes, InvalidInput


class SerialAudioTests(unittest.TestCase):
    setUp = test_storage.StorageTests.setUp

    def test_bound_bytes_survive_source_change(self):
        ref = self.manifest['tracks'][0]['audio']
        before = verified_bytes(ref, self.base)
        self.asset.write_bytes(b'changed')
        self.assertEqual(hashlib.sha256(before).hexdigest(), ref['sha256'])
        with self.assertRaises(InvalidInput):
            verified_bytes(ref, self.base)

    def test_loader_size_limit(self):
        with self.assertRaises(InvalidInput):
            verified_bytes(self.manifest['tracks'][0]['audio'], self.base, limit=1)

    def test_bound_buffer_requires_serial_before_disk(self):
        with self.assertRaisesRegex(DraftError, 'bound_buffer_requires_serial'):
            execute('DO-NOT-READ', alias='test', expected_account='123', endpoint='http://127.0.0.1:9437',
                    approve_draft=True, accept_ui_date=True, bound_buffer=True)

    def test_serial_calls_one_track_and_stops_after_failure(self):
        tracks = [dict(track_id=str(i), audio=dict(sha256=str(i))) for i in range(3)]
        ui = object.__new__(DraftUI)
        ui.manifest = dict(tracks=tracks)
        ui.record_track = Mock()
        ui._audio_batch = Mock()
        ui._append_batch = Mock(side_effect=TimeoutError('unknown'))
        ui.reorder_tracks = Mock()
        with self.assertRaises(TimeoutError):
            ui._serial_tracks(tracks, 0)
        self.assertEqual(ui._audio_batch.call_count, 1)
        self.assertEqual(ui._append_batch.call_count, 1)
        self.assertEqual([c.args[-1] for c in ui.record_track.call_args_list], ['unknown', 'observed', 'unknown'])
        ui.reorder_tracks.assert_not_called()

    def test_track_journal_persists_unknown_and_blocks_later_stage(self):
        with profile('test', root=self.root) as session:
            checkpoint = session.create_checkpoint(self.manifest, self.base)
            journal = LiveJournal(session, checkpoint, '123', 'http://127.0.0.1:9437')
            for stage in ('create', 'artwork'):
                journal.record(stage, 'unknown', None if stage == 'create' else '456')
                journal.record(stage, 'observed', '456')
            journal.record('audio', 'unknown', '456')
            track = self.manifest['tracks'][0]
            journal.record_track(track['track_id'], track['audio']['sha256'], 0, 'unknown')
            reopened = LiveJournal(session, checkpoint, '123', 'http://127.0.0.1:9437', existing=True)
            with self.assertRaises(DraftError):
                reopened.record('audio', 'observed', '456')
            with self.assertRaises(DraftError):
                reopened.require_reconciliation()
            with self.assertRaises(DraftError):
                reopened.record_track('wrong', track['audio']['sha256'], 0, 'observed')
            reopened.record_track(track['track_id'], track['audio']['sha256'], 0, 'observed')
            reopened.record('audio', 'observed', '456')

    def test_buffer_payload_has_no_path_and_lyrics_hash_checked(self):
        ui = object.__new__(DraftUI)
        ui.base = self.base; ui.bound_buffer = True
        reference = copy.deepcopy(self.manifest['tracks'][0]['audio'])
        mp3 = self.base / 'audio.mp3'; mp3.write_bytes(self.asset.read_bytes())
        reference['path'] = str(mp3)
        payload = ui.asset(reference)
        self.assertEqual(set(payload), {'name', 'mimeType', 'buffer'})
        lyric = self.base / 'lyrics.txt'; lyric.write_text('hello', encoding='utf8')
        track = dict(lyrics=dict(path=str(lyric), sha256=hashlib.sha256(b'hello').hexdigest()))
        self.assertEqual(ui.lyrics_text(track), 'hello')
        lyric.write_text('changed')
        with self.assertRaises(InvalidInput):
            ui.lyrics_text(track)

    def test_dialog_timeout_does_not_report_observed(self):
        from unittest.mock import MagicMock
        from test_live_draft import LiveDraftTests
        ui, page, record = LiveDraftTests.make_ui(self)
        items = Mock(); items.count.side_effect = [0] + [1] * 1000
        page.locator.side_effect = lambda selector: items if 'track-item' in selector else Mock(count=Mock(return_value=1 if 'upload-dialog' in selector else 0))
        page.expect_file_chooser.return_value = MagicMock()
        with self.assertRaisesRegex(DraftError, 'audio_upload_timeout'):
            ui._audio_batch(self.manifest['tracks'])

    def test_batch_and_append_pass_size_timeout_and_do_not_retry(self):
        from unittest.mock import MagicMock, patch
        from test_live_draft import LiveDraftTests
        for append in (False, True):
            with self.subTest(append=append):
                ui, page, _ = LiveDraftTests.make_ui(self)
                ui.guard_target = Mock()
                ui.click = Mock()
                items = Mock(count=Mock(return_value=1 if append else 0))
                page.locator.side_effect = lambda selector: items if 'track-item' in selector else Mock()
                chooser = MagicMock()
                page.expect_file_chooser.return_value = chooser
                with patch('toolost_uploader.live_draft.wait_for_audio', side_effect=DraftError('audio_upload_timeout')) as wait:
                    with self.assertRaisesRegex(DraftError, 'audio_upload_timeout'):
                        if append:
                            ui._append_batch(self.manifest['tracks'], 1)
                        else:
                            ui._audio_batch(self.manifest['tracks'])
                chooser.__enter__.return_value.value.set_files.assert_called_once()
                self.assertEqual(chooser.__enter__.return_value.value.set_files.call_args.kwargs['timeout'], 240000)
                self.assertEqual(wait.call_args.args[1:], (2 if append else 1, 240000))

    def test_cli_rejects_buffer_without_serial_before_browser(self):
        from toolost_uploader.cli import main
        from unittest.mock import patch
        with patch('toolost_uploader.browser.ensure_cdp_ready') as boot:
            code = main(['upload', 'DO-NOT-READ', '--draft-only', '--profile', 'test',
                         '--expected-account', '123', '--bound-buffer', '--json'])
        self.assertNotEqual(code, 0)
        boot.assert_not_called()

    def test_metadata_only_update_preserves_serial_journal(self):
        self.manifest['release_type'] = 'album'
        with profile('test', root=self.root) as session:
            checkpoint = session.create_checkpoint(self.manifest, self.base)
            journal = LiveJournal(session, checkpoint, '123', 'http://127.0.0.1:9437')
            track = self.manifest['tracks'][0]
            for stage in STAGES:
                journal.record(stage, 'unknown', None if stage == 'create' else '456')
                if stage == 'audio':
                    journal.record_track(track['track_id'], track['audio']['sha256'], 0, 'unknown')
                    journal.record_track(track['track_id'], track['audio']['sha256'], 0, 'observed')
                journal.record(stage, 'observed', '456')
            journal.record('readback', 'verified_subset', '456')
            revised = copy.deepcopy(self.manifest)
            revised['tracks'][0]['title'] = 'Changed metadata only'
            new_checkpoint = session.update_checkpoint(revised, self.base, expected_revision=1)
            journal.update_for_append(new_checkpoint)
            self.assertEqual(journal.read()['track_events'], journal.value['track_events'])

    def test_large_bound_asset_rejected_before_checkpoint_or_browser(self):
        from toolost_uploader.live_draft import check_buffer_mode
        from unittest.mock import patch
        large = self.base / 'large.mp3'
        with large.open('wb') as stream:
            stream.truncate(50 * 1024 * 1024 + 1)
        manifest = copy.deepcopy(self.manifest)
        manifest['tracks'][0]['audio']['path'] = str(large)
        path = self.base / 'manifest.json'; path.write_text(json.dumps(manifest))
        with patch('toolost_uploader.live_draft.preflight', return_value=(manifest, self.base)):
            with self.assertRaises(InvalidInput) as result:
                check_buffer_mode(path, serial_audio=True, bound_buffer=True)
        self.assertEqual(result.exception.code, 'buffer_limit_exceeded')
        self.assertFalse(self.root.exists())


    def test_invalid_asset_after_intent_requires_reconciliation(self):
        ui = object.__new__(DraftUI)
        ui.guard_identity = Mock(); ui.guard_target = Mock()
        ui.page = Mock(url='https://toolost.com/uploader/edit/456')
        ui.remote_id = '456'; ui.attempted = set(); ui.record = Mock()
        def invalid():
            raise InvalidInput('hash_mismatch', 'fixture')
        with self.assertRaisesRegex(DraftError, 'asset_invalid_after_intent'):
            ui.action('audio', invalid)
        self.assertEqual(ui.record.call_count, 1)
        self.assertEqual(ui.record.call_args.args[1], 'unknown')

    def test_sync_pending_persists_and_blocks_false_up_to_date(self):
        with profile('test', root=self.root) as session:
            checkpoint = session.create_checkpoint(self.manifest, self.base)
            journal = LiveJournal(session, checkpoint, '123', 'http://127.0.0.1:9437')
            for stage in STAGES:
                journal.record(stage, 'unknown', None if stage == 'create' else '456')
                journal.record(stage, 'observed', '456')
            journal.record('readback', 'verified_subset', '456')
            journal.begin_sync()
            reopened = LiveJournal(session, checkpoint, '123', 'http://127.0.0.1:9437', existing=True)
            with self.assertRaisesRegex(DraftError, 'sync_outcome_unknown'):
                reopened.require_reconciliation()
            reopened.record('update_title', 'unknown', '456')
            reopened.record('update_title', 'observed', '456')
            reopened.record('save', 'unknown', '456')
            reopened.record('save', 'observed', '456')
            reopened.record('readback', 'verified_subset', '456')
            self.assertEqual(reopened.require_reconciliation(), '456')
            self.assertFalse(reopened.read()['sync_pending'])

    def test_reorder_rejects_ambiguous_basename_before_metadata(self):
        ui = object.__new__(DraftUI)
        ui.manifest = {'tracks': [{'audio': {'path': 'song.mp3'}}, {'audio': {'path': 'song2.mp3'}}]}
        page = Mock(); items = Mock(); items.count.return_value = 2
        items.nth.return_value.text_content.return_value = 'song2'
        page.locator.return_value = items; ui.page = page
        with self.assertRaisesRegex(DraftError, 'track_identity_ambiguous'):
            ui.reorder_tracks()
        page.mouse.down.assert_not_called()


    def test_reorder_accepts_concatenated_portal_ordinal_and_edit(self):
        ui = object.__new__(DraftUI)
        ui.manifest = {'tracks': [{'audio': {'path': 'testtrack001_abc.mp3'}}, {'audio': {'path': 'testtrack002_def.mp3'}}]}
        items = Mock(); items.count.return_value = 2
        labels = ['1testtrack001_abcEdit', '2testtrack002_defEdit']
        items.nth.side_effect = lambda index: Mock(text_content=Mock(return_value=labels[index]))
        ui.page = Mock(); ui.page.locator.return_value = items
        ui.reorder_tracks()
        ui.page.mouse.down.assert_not_called()
