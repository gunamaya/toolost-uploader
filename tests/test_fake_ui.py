import os
import unittest
from unittest.mock import patch

import test_storage
from toolost_uploader import journal
from toolost_uploader.fake_ui import FakeUI
from toolost_uploader.storage import StorageError


@unittest.skipUnless(os.name == 'posix', 'Journal storage POSIX saja.')
class FakeUITests(unittest.TestCase):
    setUp = test_storage.StorageTests.setUp
    profile = test_storage.StorageTests.profile
    error = test_storage.StorageTests.error

    def upload(self, ui, duplicate=False):
        ui.open_upload()
        ui.browse()
        ui.select([{'track_id': 'track-1', 'basename': 'one.mp3'},
                   {'track_id': 'track-2', 'basename': 'one.mp3' if duplicate else 'two.mp3'}])
        ui.upload()

    def stage(self, ui):
        self.upload(ui)
        for _ in range(ui.encoding_ticks):
            ui.tick()
        ui.reorder(['track-1', 'track-2'])
        ui.edit_track('track-1')
        for _ in range(ui.field_ticks):
            ui.tick()
        ui.set_ai(True)
        ui.done()
        for _ in range(ui.field_ticks):
            ui.tick()
        ui.set_title('Synthetic desired')

    def attempt(self, session, ui):
        checkpoint = session.create_checkpoint(self.manifest, self.base)
        desired = ui.desired()
        record = journal.prepare(session, 'release-1', run_id=checkpoint['run_id'],
                                 expected_revision=1, adapter=ui, desired=desired)
        return dict(run_id=checkpoint['run_id'], attempt_id=record['attempt_id'], adapter=ui), desired

    def test_upload_modal_progress_encoding_reverse_ingest(self):
        ui = FakeUI()
        self.error('fake_wrong_scope', ui.browse)
        self.upload(ui)
        self.assertEqual(ui.progress, 100)
        self.assertIsNotNone(ui.encoding)
        self.error('fake_panel_not_ready', ui.rows)
        ui.tick()
        self.error('fake_panel_not_ready', ui.rows)
        ui.tick()
        self.assertEqual([t['track_id'] for t in ui.rows()], ['track-2', 'track-1'])
        ui.reorder(['track-1', 'track-2'])
        self.assertEqual([t['track_id'] for t in ui.rows()], ['track-1', 'track-2'])
        self.error('reconciliation_required', ui.open_upload)
        self.assertEqual(ui.upload_calls, 1)
        self.assertEqual(ui.observe()['state']['track_ids'], [])

    def test_field_visibility_aria_and_done_are_staged_only(self):
        ui = FakeUI()
        self.upload(ui)
        ui.tick()
        ui.tick()
        ui.edit_track('track-1')
        self.error('fake_panel_not_ready', ui.set_ai, True)
        ui.tick()
        ui.set_ai(True)
        self.assertEqual(ui.ai_readback(), {'native_checked': False, 'aria_checked': True})
        ui.done()
        self.error('fake_panel_not_ready', ui.set_title, 'Not ready')
        ui.tick()
        ui.set_title('Unsaved')
        ui.reopen()
        ui.tick()
        self.assertEqual(ui.desired()['title'], 'Synthetic baseline')
        self.assertEqual(ui.desired()['track_ids'], [])
        self.assertEqual(ui.save_calls, 0)

    def test_save_dialog_and_navigation_persist_verified_order_metadata(self):
        for route in ('dialog', 'navigation'):
            with self.subTest(route=route), self.profile(route) as session:
                ui = FakeUI(save_route=route)
                self.stage(ui)
                args, desired = self.attempt(session, ui)
                result = journal.execute(session, 'release-1', desired=desired, **args)
                self.assertEqual(result['state'], 'applied')
                ui.reopen()
                ui.tick()
                self.assertEqual(ui.desired(), desired)
                self.assertEqual(ui.rows()[0]['ai_assisted'], True)
                self.assertEqual(ui.save_dialogs, 1 if route == 'dialog' else 0)
                self.assertEqual((ui.upload_calls, ui.save_calls), (1, 1))
                self.error('reconciliation_required', journal.execute, session, 'release-1', desired=desired, **args)

    def test_save_error_and_lost_response_no_retry_no_reupload(self):
        for route, expected in (('error', 'not_applied'), ('lost_response', 'applied')):
            with self.subTest(route=route), self.profile(route) as session:
                ui = FakeUI(save_route=route)
                self.stage(ui)
                args, desired = self.attempt(session, ui)
                self.assertEqual(journal.execute(session, 'release-1', desired=desired, **args)['state'], 'unknown')
                self.error('reconciliation_required', journal.execute, session, 'release-1', desired=desired, **args)
                self.assertEqual(journal.reconcile(session, 'release-1', **args)['state'], expected)
                ui.reopen()
                self.assertEqual((ui.upload_calls, ui.save_calls), (1, 1))

    def test_metadata_not_persisted_is_conflict_not_applied(self):
        with self.profile() as session:
            ui = FakeUI(save_route='metadata_loss')
            self.stage(ui)
            args, desired = self.attempt(session, ui)
            result = journal.execute(session, 'release-1', desired=desired, **args)
            self.assertEqual(ui.observe()['state']['track_ids'], desired['track_ids'])
            self.assertNotEqual(ui.observe()['state']['metadata_sha256'], desired['metadata_sha256'])
            self.assertEqual(result['state'], 'conflict')

    def test_duplicate_basename_blocks_mapping_and_save(self):
        ui = FakeUI()
        self.upload(ui, duplicate=True)
        ui.tick()
        ui.tick()
        self.error('reconciliation_required', ui.rows)
        self.error('reconciliation_required', ui.reorder, ['track-1', 'track-2'])
        self.error('reconciliation_required', ui.desired)
        self.assertEqual((ui.upload_calls, ui.save_calls), (1, 0))

    def test_incomplete_or_ambiguous_readback_remains_unknown(self):
        for flag in ('complete', 'identity_verified'):
            with self.subTest(flag=flag), self.profile(flag) as session:
                ui = FakeUI(save_route='lost_response')
                self.stage(ui)
                args, desired = self.attempt(session, ui)
                journal.execute(session, 'release-1', desired=desired, **args)
                setattr(ui, flag, False)
                self.assertEqual(journal.reconcile(session, 'release-1', **args)['state'], 'unknown')
                setattr(ui, flag, True)
                self.assertEqual(journal.reconcile(session, 'release-1', **args)['state'], 'applied')
                self.assertEqual((ui.upload_calls, ui.save_calls), (1, 1))

    def test_adapter_save_not_called_if_journal_write_fails(self):
        with self.profile() as session:
            ui = FakeUI()
            self.stage(ui)
            args, desired = self.attempt(session, ui)
            with patch('toolost_uploader.journal._atomic_write', side_effect=StorageError('write_failed')):
                self.error('write_failed', journal.execute, session, 'release-1', desired=desired, **args)
            self.assertEqual(ui.save_calls, 0)

    def test_bad_inputs_and_wrong_scopes(self):
        for kwargs in ({'field_ticks': -1}, {'encoding_ticks': 0}, {'save_route': 'publish'}):
            with self.assertRaises(StorageError):
                FakeUI(**kwargs)
        ui = FakeUI()
        self.error('fake_wrong_scope', ui.select, [])
        self.error('fake_wrong_scope', ui.upload)
        self.error('fake_wrong_scope', ui.done)
        ui.open_upload()
        ui.browse()
        self.error('invalid_fake_tracks', ui.select, [{'track_id': 'x', 'basename': 'a', 'password': 'SECRET'}])
        self.error('invalid_fake_tracks', ui.select, [{'track_id': 'x', 'basename': 'a'}, {'track_id': 'x', 'basename': 'b'}])

    def test_track_id_does_not_control_panel_scope(self):
        ui = FakeUI(field_ticks=0, encoding_ticks=1)
        ui.open_upload()
        ui.browse()
        ui.select([{'track_id': 'main', 'basename': 'one.mp3'}])
        ui.upload()
        ui.tick()
        ui.edit_track('main')
        ui.set_ai(True)
        self.assertTrue(ui.ai_readback()['aria_checked'])
        self.error('fake_panel_not_ready', ui.set_title, 'Wrong scope')
        ui.done()
        self.assertTrue(ui.rows()[0]['ai_assisted'])

    def test_identity_change_before_save_blocks_mutation(self):
        with self.profile() as session:
            ui = FakeUI()
            self.stage(ui)
            args, desired = self.attempt(session, ui)
            ui.account = 'other'
            self.error('fake_identity_mismatch', journal.execute, session, 'release-1', desired=desired, **args)
            self.assertEqual(ui.save_calls, 0)
