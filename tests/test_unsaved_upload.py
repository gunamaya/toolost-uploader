import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

from toolost_uploader.live_draft import normal_upload_audio, finalize_normal_upload, recovery_steps, run_steps
from toolost_uploader.live_journal import DraftError, RecoveryJournal
from toolost_uploader.remote_binding import observe_active_editor, observe_release
from toolost_uploader.storage import profile


class UnsavedUploadTests(unittest.TestCase):
    def setup_run(self, session, serial=False):
        manifest = {'release_id': 'unsaved', 'title': 'Album', 'tracks': [
            {'track_id': str(i), 'title': 'Final ' + str(i),
             'audio': {'path': f'{i:02d} - Original.wav', 'sha256': 'a' * 64}}
            for i in range(12)]}
        ui = Mock(manifest=manifest, remote_id='2095311', serial_audio=serial)
        active = []
        def upload(selected, *args, **kwargs):
            for track in reversed(selected):
                active.append(dict(editor_key='client-' + track['track_id'], saved=False,
                                   title=Path(track['audio']['path']).stem,
                                   track_order=len(active), audio_present=True))
        ui._audio_batch.side_effect = upload
        ui._append_batch.side_effect = upload
        journal = RecoveryJournal(session, manifest, '431006', '2095311', 'http://127.0.0.1:9437')
        return ui, active, journal

    def test_empty_persisted_active_twelve_metadata_save_binds_numeric_ids(self):
        for serial in (False, True):
            with self.subTest(serial=serial), tempfile.TemporaryDirectory() as tmp, profile('test', root=Path(tmp).resolve() / 'private') as session:
                ui, active, journal = self.setup_run(session, serial)
                persisted = []
                def action(name, operation):
                    operation()
                ui.action.side_effect = action
                def audio():
                    normal_upload_audio(ui, journal, lambda: deepcopy(persisted),
                                        observe_active=lambda: deepcopy(active))
                def metadata():
                    self.assertEqual(len(journal.read()['snapshot']), 12)
                    self.assertEqual(journal.read()['mapping'], {})
                    self.assertEqual(persisted, [])
                    journal.append('metadata_save', 'unknown')
                ui.metadata.side_effect = metadata
                def save():
                    persisted.extend(dict(id=100 + i, title=t['title'], track_order=i,
                                          audio_url='https://test/private') for i, t in enumerate(ui.manifest['tracks']))
                ui.save.side_effect = save
                run_steps(ui, audio_operation=audio,
                          after_save=lambda: finalize_normal_upload(ui, journal, lambda: deepcopy(persisted)))
                self.assertEqual(len(journal.read()['mapping']), 12)
                self.assertTrue(all(key.isdigit() for key in journal.read()['mapping'].values()))
                self.assertNotIn('https://test/private', str(journal.read()))
                with self.assertRaisesRegex(DraftError, 'new_upload_unknown_requires_review'):
                    audio()
                self.assertEqual(ui._audio_batch.call_count, 1)
                ui.readback.assert_called_once()

    def test_deferred_journal_survives_restart_and_blocks_recovery(self):
        with tempfile.TemporaryDirectory() as tmp, profile('test', root=Path(tmp).resolve() / 'private') as session:
            ui, active, journal = self.setup_run(session)
            normal_upload_audio(ui, journal, lambda: [], observe_active=lambda: deepcopy(active))
            restored = RecoveryJournal(session, ui.manifest, '431006', '2095311', 'http://127.0.0.1:9437')
            observe = Mock(return_value=[])
            with self.assertRaisesRegex(DraftError, 'deferred_upload_binding_requires_review'):
                recovery_steps(ui, restored, {'mapping': {}, 'snapshot': [], 'review_digest': 'new'}, observe)
            observe.assert_not_called()
            self.assertEqual(ui._audio_batch.call_count, 1)
            ui.save.assert_not_called()

    def test_unknown_transfer_and_bad_saved_readback_keep_intent(self):
        with tempfile.TemporaryDirectory() as tmp, profile('test', root=Path(tmp).resolve() / 'private') as session:
            ui, active, journal = self.setup_run(session)
            ui._audio_batch.side_effect = RuntimeError('interrupted')
            with self.assertRaises(RuntimeError):
                normal_upload_audio(ui, journal, lambda: [], observe_active=lambda: [])
            self.assertEqual(journal.read()['events'][-1]['outcome'], 'unknown')
            with self.assertRaisesRegex(DraftError, 'saved_binding_requires_review'):
                finalize_normal_upload(ui, journal, lambda: [])
            self.assertEqual(journal.read()['events'][-1]['outcome'], 'unknown')

    def test_existing_active_rows_stop_before_transfer_even_if_persisted_empty(self):
        with tempfile.TemporaryDirectory() as tmp, profile('test', root=Path(tmp).resolve() / 'private') as session:
            ui, active, journal = self.setup_run(session)
            ui._audio_batch(ui.manifest['tracks'])
            ui._audio_batch.reset_mock()
            with self.assertRaisesRegex(DraftError, 'unexpected_existing_tracks'):
                normal_upload_audio(ui, journal, lambda: [], observe_active=lambda: deepcopy(active))
            ui._audio_batch.assert_not_called()

    def test_active_observation_blocks_disposable_persisted_read_without_navigation(self):
        page = Mock(url='https://toolost.com/uploader/edit/2095311')
        page.evaluate.return_value = dict(identity={'account': '431006', 'draft': '2095311'}, tracks=[
            dict(editor_key='nfppm', saved=False, title='04 - Original', track_order=0, audio_present=True)])
        context = Mock(pages=[page])
        result = observe_active_editor(page, account='431006', draft='2095311')
        self.assertEqual(result[0]['editor_key'], 'nfppm')
        with self.assertRaisesRegex(DraftError, 'active_unsaved_upload_requires_review'):
            observe_release(context, account='431006', draft='2095311')
        context.new_page.assert_not_called()
        page.goto.assert_not_called()
        page.reload.assert_not_called()
        page.evaluate.return_value['identity']['account'] = 'different'
        with self.assertRaisesRegex(DraftError, 'identity_unverified'):
            observe_active_editor(page, account='431006', draft='2095311')

    def test_absent_index_uses_array_position_not_remote_id(self):
        page = Mock(url='https://toolost.com/uploader/edit/2')
        page.evaluate.return_value = dict(identity={'account': '1', 'draft': '2'}, tracks=[
            dict(editor_key='client-a', saved=False, title='a', track_order=None, audio_present=True),
            dict(editor_key='client-b', saved=False, title='b', audio_present=True)])
        rows = observe_active_editor(page, account='1', draft='2')
        self.assertEqual([r['track_order'] for r in rows], [0, 1])
        self.assertNotIn('id', rows[0])
        for account, draft in [('9', '2'), ('1', '9')]:
            with self.assertRaises(DraftError):
                observe_active_editor(page, account=account, draft=draft)

    def test_duplicate_keys_and_missing_audio_fail_closed(self):
        page = Mock(url='https://toolost.com/uploader/edit/2')
        row = dict(editor_key='same', saved=False, title='a', track_order=None, audio_present=True)
        for rows in ([row, dict(row, title='b')], [dict(row, audio_present=False)], [dict(row, editor_key=True)]):
            page.evaluate.return_value = dict(identity={'account': '1', 'draft': '2'}, tracks=deepcopy(rows))
            with self.assertRaises(DraftError):
                observe_active_editor(page, account='1', draft='2')

    def setup_active_recovery(self, session):
        from toolost_uploader.live_draft import active_editor_recovery_steps
        ui, active, journal = self.setup_run(session)
        ui._audio_batch(ui.manifest['tracks'])
        ui._audio_batch.reset_mock()
        journal.append('new_upload_baseline', 'observed', snapshot=[], mapping={})
        journal.append('upload', 'unknown')
        live = Mock()
        live.read.return_value = dict(remote_draft_id=ui.remote_id, events=[
            dict(operation=op, outcome=outcome) for op, outcome in
            [('create', 'unknown'), ('create', 'observed'), ('artwork', 'unknown'), ('artwork', 'observed'), ('audio', 'unknown')]])
        persisted = [dict(id=i + 1, title=t['title'], track_order=i, audio_url='https://private/audio')
                     for i, t in enumerate(ui.manifest['tracks'])]
        call = lambda: active_editor_recovery_steps(ui, live, journal, lambda: deepcopy(active), lambda: deepcopy(persisted))
        return ui, active, journal, live, call

    def test_active_complete_continues_once_without_create_upload_or_extra_save(self):
        with tempfile.TemporaryDirectory() as tmp, profile('test', root=Path(tmp).resolve() / 'private') as session:
            ui, active, journal, live, call = self.setup_active_recovery(session)
            call()
            ui.create.assert_not_called()
            ui._audio_batch.assert_not_called()
            ui._append_batch.assert_not_called()
            ui.sync_metadata_and_order.assert_called_once()
            ui.save.assert_called_once()
            self.assertIs(ui.read_only, True)
            self.assertEqual(journal.read()['events'][-1]['operation'], 'complete')
            self.assertNotIn('https://private', str(journal.read()))
            with self.assertRaisesRegex(DraftError, 'stage_requires_review'):
                call()
            ui.save.assert_called_once()

    def test_interrupted_metadata_or_save_never_replayed(self):
        for operation in ('sync_metadata_and_order', 'save'):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as tmp, profile('test', root=Path(tmp).resolve() / 'private') as session:
                ui, active, journal, live, call = self.setup_active_recovery(session)
                getattr(ui, operation).side_effect = RuntimeError('private failure')
                with self.assertRaises(RuntimeError):
                    call()
                with self.assertRaisesRegex(DraftError, 'stage_requires_review'):
                    call()
                self.assertEqual(getattr(ui, operation).call_count, 1)
                ui.readback.assert_not_called()

    def test_active_partial_ambiguous_or_wrong_stage_no_metadata_save(self):
        for change in ('partial', 'duplicate-title', 'duplicate-key', 'metadata', 'draft'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp, profile('test', root=Path(tmp).resolve() / 'private') as session:
                ui, active, journal, live, call = self.setup_active_recovery(session)
                if change == 'partial': active.pop()
                if change == 'duplicate-title': active[1]['title'] = active[0]['title']
                if change == 'duplicate-key': active[1]['editor_key'] = active[0]['editor_key']
                if change == 'metadata': live.read.return_value['events'].append(dict(operation='metadata', outcome='unknown'))
                if change == 'draft': live.read.return_value['remote_draft_id'] = '8'
                with self.assertRaises(DraftError): call()
                ui.sync_metadata_and_order.assert_not_called()
                ui.save.assert_not_called()
