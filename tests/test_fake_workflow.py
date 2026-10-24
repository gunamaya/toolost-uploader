import os
import unittest
from unittest.mock import patch

import test_storage
from toolost_uploader import approval, fake_upload, fake_workflow as flow, storage
from toolost_uploader.fake_ui import FakeUI


@unittest.skipUnless(os.name == 'posix', 'Storage POSIX saja.')
class WorkflowTests(unittest.TestCase):
    setUp = test_storage.StorageTests.setUp
    profile = test_storage.StorageTests.profile
    error = test_storage.StorageTests.error

    def setup_flow(self, session, route='dialog'):
        checkpoint = session.create_checkpoint(self.manifest, self.base)
        self.run = checkpoint['run_id']
        self.ui = FakeUI(save_route=route)
        fake_upload.initialize(session, 'release-1', run_id=self.run)
        approval.bind(session, account='synthetic-account', reviewed=True)
        receipt = approval.approve(session, 'release-1', run_id=self.run, expected_revision=1,
                                   account='synthetic-account', draft='synthetic-draft',
                                   plan=flow.plan(session, 'release-1', run_id=self.run), approved=True)
        self.token = receipt['approval_id']
        return flow.start(session, 'release-1', run_id=self.run, expected_revision=1, approval_id=self.token)

    def advance(self, session):
        return flow.advance(session, 'release-1', run_id=self.run, ui=self.ui)

    def reconcile(self, session):
        return flow.reconcile(session, 'release-1', run_id=self.run, ui=self.ui)

    def ready(self, session):
        self.advance(session)
        fake_upload.settle(session, 'release-1', run_id=self.run)
        self.assertEqual(self.reconcile(session)['steps'], ['applied', 'pending', 'pending'])

    def test_full_workflow_one_token_three_receipts(self):
        with self.profile() as session:
            self.setup_flow(session)
            self.ready(session)
            self.assertEqual(self.advance(session)['steps'], ['applied', 'applied', 'pending'])
            result = self.advance(session)
            self.assertEqual(result['steps'], ['applied'] * 3)
            self.assertEqual(self.ui.save_calls, 1)
            self.assertEqual(fake_upload.observe(session, 'release-1', run_id=self.run)['upload_calls'], 1)
            self.ui.reopen()
            self.ui.tick()
            self.assertTrue(self.ui.rows()[0]['ai_assisted'])
            self.error('workflow_complete', self.advance, session)

    def test_unknown_upload_blocks_edit_until_explicit_reconcile(self):
        with self.profile() as session:
            self.setup_flow(session)
            self.assertEqual(self.advance(session)['steps'][0], 'unknown')
            self.error('reconciliation_required', self.advance, session)
            self.assertEqual(self.reconcile(session)['steps'][0], 'unknown')
            self.assertEqual(self.ui.staged['tracks'], [])
            fake_upload.settle(session, 'release-1', run_id=self.run)
        with self.profile() as session:
            self.assertEqual(self.reconcile(session)['steps'][0], 'applied')
            self.advance(session)
            self.assertEqual(self.ui.save_calls, 0)

    def test_staging_lost_after_reopen_blocks_save(self):
        with self.profile() as session:
            self.setup_flow(session)
            self.ready(session)
            self.advance(session)
            self.ui.reopen()
            self.ui.tick()
            self.error('staging_lost_or_changed', self.advance, session)
            self.assertEqual(self.ui.save_calls, 0)

    def test_save_lost_response_read_only_recovery(self):
        with self.profile() as session:
            self.setup_flow(session, route='lost_response')
            self.ready(session)
            self.advance(session)
            self.assertEqual(self.advance(session)['steps'][2], 'unknown')
        self.ui.reopen()
        self.ui.tick()
        with self.profile() as session:
            self.assertEqual(self.reconcile(session)['steps'], ['applied'] * 3)
            self.assertEqual(self.ui.save_calls, 1)

    def test_intent_failure_no_upload_and_consumed_approval(self):
        with self.profile() as session:
            self.setup_flow(session)
            with patch('toolost_uploader.fake_workflow._write', side_effect=storage.StorageError('write_failed')):
                self.error('write_failed', self.advance, session)
            self.assertEqual(fake_upload.observe(session, 'release-1', run_id=self.run)['upload_calls'], 0)

    def test_receipt_saved_ledger_failure_recovers_without_save_again(self):
        with self.profile() as session:
            self.setup_flow(session)
            self.ready(session)
            self.advance(session)
            original = flow._write
            calls = []

            def write(*args):
                calls.append(1)
                if len(calls) == 2:
                    raise storage.StorageError('write_failed')
                return original(*args)

            with patch('toolost_uploader.fake_workflow._write', side_effect=write):
                self.error('write_failed', self.advance, session)
            self.assertEqual(self.ui.save_calls, 1)
            self.assertEqual(self.reconcile(session)['steps'], ['applied'] * 3)
            self.assertEqual(self.ui.save_calls, 1)

    def test_edit_receipt_failure_stays_unknown_not_replayed(self):
        with self.profile() as session:
            self.setup_flow(session)
            self.ready(session)
            original = flow._write
            calls = []

            def write(*args):
                calls.append(1)
                if len(calls) == 2:
                    raise storage.StorageError('write_failed')
                return original(*args)

            with patch('toolost_uploader.fake_workflow._write', side_effect=write):
                self.error('write_failed', self.advance, session)
            self.assertEqual(self.reconcile(session)['steps'][1], 'unknown')
            self.error('reconciliation_required', self.advance, session)
            self.assertEqual(self.ui.save_calls, 0)

    def test_unmapped_optional_metadata_rejected(self):
        self.manifest['tracks'][0]['lyrics'] = dict(self.manifest['tracks'][0]['audio'])
        with self.profile() as session:
            checkpoint = session.create_checkpoint(self.manifest, self.base)
            self.error('unsupported_workflow_fields', flow.plan, session, 'release-1', run_id=checkpoint['run_id'])

    def test_before_send_no_automatic_retry(self):
        with self.profile() as session:
            self.setup_flow(session)
            flow.advance(session, 'release-1', run_id=self.run, ui=self.ui, upload_mode='before_send')
            self.assertEqual(self.reconcile(session)['steps'][0], 'not_applied')
            self.error('reconciliation_required', self.advance, session)
            self.assertEqual(self.ui.save_calls, 0)

    def test_wrong_approval_plan_and_identity(self):
        with self.profile() as session:
            self.setup_flow(session)
            self.error('approval_consumed', flow.start, session, 'release-1', run_id=self.run,
                       expected_revision=1, approval_id=self.token)
            self.ui.account = 'other'
            self.error('fake_identity_mismatch', self.advance, session)
            self.assertEqual(fake_upload.observe(session, 'release-1', run_id=self.run)['upload_calls'], 0)
