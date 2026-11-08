import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

from toolost_uploader.live_draft import normal_upload_audio, run_steps
from toolost_uploader.live_journal import DraftError, RecoveryJournal
from toolost_uploader.remote_binding import observed_upload_mapping
from toolost_uploader.storage import profile


class NormalUploadBindingTests(unittest.TestCase):
    def setup_run(self, session, serial=False):
        manifest = {'release_id': 'new', 'title': 'Album', 'tracks': [
            {'track_id': 'a', 'title': 'One', 'audio': {'path': 'snapshot/01-One.wav', 'sha256': 'a' * 64}},
            {'track_id': 'b', 'title': 'Two', 'audio': {'path': 'snapshot/02-Two.wav', 'sha256': 'b' * 64}}]}
        ui = Mock(manifest=manifest, serial_audio=serial, remote_id='2')
        tracks = []
        def upload(selected, *args, **kwargs):
            for track in reversed(selected):
                tracks.append({'id': len(tracks) + 10, 'title': Path(track['audio']['path']).stem,
                               'track_order': len(tracks) + 1, 'audio_url': 'https://test/' + track['track_id']})
        ui._audio_batch.side_effect = upload
        ui._append_batch.side_effect = upload
        journal = RecoveryJournal(session, manifest, '1', '2', 'http://127.0.0.1:9437')
        return ui, tracks, journal

    def test_normal_metadata_interrupt_keeps_ids_before_metadata_batch_and_serial(self):
        for serial in (False, True):
            with self.subTest(serial=serial), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve() / 'private'
                with profile('test', root=root) as session:
                    ui, tracks, journal = self.setup_run(session, serial)
                    def action(name, operation):
                        if name == 'audio':
                            operation()
                        if name == 'metadata':
                            self.assertEqual(set(journal.read()['mapping']), {'a', 'b'})
                            raise RuntimeError('metadata interrupted')
                    ui.action.side_effect = action
                    with self.assertRaisesRegex(RuntimeError, 'metadata interrupted'):
                        run_steps(ui, audio_operation=lambda: normal_upload_audio(ui, journal, lambda: deepcopy(tracks)))
                    expected = journal.read()['mapping']
                    self.assertEqual(len(set(expected.values())), 2)
                with profile('test', root=root) as session:
                    restored = RecoveryJournal(session, ui.manifest, '1', '2', 'http://127.0.0.1:9437')
                    self.assertEqual(restored.read()['mapping'], expected)
                    with self.assertRaisesRegex(DraftError, 'unknown_requires_review'):
                        normal_upload_audio(ui, restored, lambda: deepcopy(tracks))
                    self.assertEqual(len(tracks), 2)

    def test_unknown_audio_never_replays_even_when_remote_empty(self):
        with tempfile.TemporaryDirectory() as tmp, profile('test', root=Path(tmp).resolve() / 'private') as session:
            ui, tracks, journal = self.setup_run(session)
            ui._audio_batch.side_effect = RuntimeError('interrupted')
            with self.assertRaises(RuntimeError):
                normal_upload_audio(ui, journal, lambda: deepcopy(tracks))
            restored = RecoveryJournal(session, ui.manifest, '1', '2', 'http://127.0.0.1:9437')
            with self.assertRaisesRegex(DraftError, 'unknown_requires_review'):
                normal_upload_audio(ui, restored, lambda: deepcopy(tracks))
            self.assertEqual(ui._audio_batch.call_count, 1)
            ui.reorder_tracks.assert_not_called()

    def test_missing_ambiguous_or_existing_remote_stops_before_metadata(self):
        for mode in ('unknown_title', 'collision', 'existing'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                with profile('test', root=Path(tmp).resolve() / 'private') as session:
                    ui, tracks, journal = self.setup_run(session)
                    if mode == 'collision':
                        ui.manifest['tracks'][1]['title'] = '01-One'
                    if mode == 'existing':
                        tracks.append({'id': 99})
                    def observe():
                        result = deepcopy(tracks)
                        if mode == 'unknown_title' and result:
                            result[0]['title'] = 'unrecognized'
                        return result
                    with self.assertRaises(DraftError):
                        normal_upload_audio(ui, journal, observe)
                    ui.reorder_tracks.assert_not_called()
                    if mode == 'existing':
                        ui._audio_batch.assert_not_called()

    def test_title_fallback_and_filename_stem_both_unique(self):
        manifest = {'tracks': [{'track_id': 'a', 'title': 'Final', 'audio': {'path': '01-Initial.wav'}}]}
        for title in ('01-Initial', '01-Initial.wav', 'Final'):
            self.assertEqual(observed_upload_mapping(manifest, [], [{'id': 9, 'title': title}], manifest['tracks']), {'a': '9'})

    def test_review_proposes_durable_ids_after_metadata_title_change(self):
        import sys
        import types
        from unittest.mock import MagicMock
        from toolost_uploader.remote_binding import review_live
        with tempfile.TemporaryDirectory() as tmp, profile('test', root=Path(tmp).resolve() / 'private') as session:
            ui, tracks, journal = self.setup_run(session)
            normal_upload_audio(ui, journal, lambda: deepcopy(tracks))
            for track in tracks:
                track['title'] = 'Partially edited title'
            factory = MagicMock()
            factory.return_value.__enter__.return_value.chromium.connect_over_cdp.return_value.contexts = [Mock()]
            module = types.ModuleType('playwright.sync_api')
            module.sync_playwright = factory
            with patch.dict(sys.modules, {'playwright': types.ModuleType('playwright'), 'playwright.sync_api': module}), \
                    patch('toolost_uploader.validation.load_manifest', return_value=ui.manifest), \
                    patch('toolost_uploader.validation.validate_manifest'), \
                    patch('toolost_uploader.remote_binding.observe_release', return_value=tracks):
                review = review_live('manifest.json', account='1', draft='2', endpoint='http://127.0.0.1:9437',
                                     alias='test', observed_binding=journal.read())
                self.assertEqual(review['mapping'], journal.read()['mapping'])
                self.assertFalse(review['retry_safe'])
                self.assertFalse(review['execution_available'])
                self.assertFalse(review['remote_audio_hashes_verified'])
                tracks[0]['audio_url'] += '/changed'
                with self.assertRaisesRegex(DraftError, 'review_changed'):
                    review_live('manifest.json', account='1', draft='2', endpoint='http://127.0.0.1:9437',
                                alias='test', observed_binding=journal.read())
