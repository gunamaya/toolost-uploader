import os
import unittest
from unittest.mock import patch

import test_fake_ui
import test_storage
from toolost_uploader import approval, fake_flow, journal, storage
from toolost_uploader.fake_ui import FakeUI


@unittest.skipUnless(os.name == 'posix', 'Storage POSIX saja.')
class FakeFlowTests(unittest.TestCase):
    setUp = test_storage.StorageTests.setUp
    profile = test_storage.StorageTests.profile
    error = test_storage.StorageTests.error
    stage = test_fake_ui.FakeUITests.stage
    upload = test_fake_ui.FakeUITests.upload

    def setup_flow(self, session, route='dialog'):
        self.ui = FakeUI(save_route=route)
        self.stage(self.ui)
        checkpoint = session.create_checkpoint(self.manifest, self.base)
        self.run = checkpoint['run_id']
        approval.bind(session, account=self.ui.account, reviewed=True)
        record = approval.approve(session, 'release-1', run_id=self.run, expected_revision=1,
                                  account=self.ui.account, draft=self.ui.draft,
                                  plan=fake_flow.plan(self.ui), approved=True)
        self.args = dict(run_id=self.run, expected_revision=1, approval_id=record['approval_id'], ui=self.ui)

    def test_approved_save_once(self):
        with self.profile() as session:
            self.setup_flow(session)
            self.assertEqual(fake_flow.execute(session, 'release-1', **self.args)['state'], 'applied')
            self.assertEqual(self.ui.save_calls, 1)
            self.ui.reopen()
            self.ui.tick()
            self.error('approval_consumed', fake_flow.execute, session, 'release-1', **self.args)
            self.assertEqual(self.ui.save_calls, 1)

    def test_missing_wrong_or_stale_approval_no_save(self):
        with self.profile() as session:
            self.setup_flow(session)
            wrong = dict(self.args, approval_id='wrong')
            self.error('approval_mismatch', fake_flow.execute, session, 'release-1', **wrong)
            self.ui.set_title('Changed after approval')
            self.error('approval_stale', fake_flow.execute, session, 'release-1', **self.args)
            self.error('attempt_not_found', journal.read_attempt, session, 'release-1', run_id=self.run)
            self.assertEqual(self.ui.save_calls, 0)

    def test_identity_change_and_revision_no_save(self):
        with self.profile() as session:
            self.setup_flow(session)
            self.ui.account = 'other'
            self.error('identity_review_required', fake_flow.execute, session, 'release-1', **self.args)
            self.ui.account = 'synthetic-account'
            self.error('revision_conflict', fake_flow.execute, session, 'release-1', **dict(self.args, expected_revision=2))
            self.assertEqual(self.ui.save_calls, 0)

    def test_consume_failure_leaves_prepared_no_save(self):
        with self.profile() as session:
            self.setup_flow(session)
            with patch('toolost_uploader.approval.consume', side_effect=storage.StorageError('write_failed')):
                self.error('write_failed', fake_flow.execute, session, 'release-1', **self.args)
            attempt = journal.read_attempt(session, 'release-1', run_id=self.run)
            self.assertEqual(attempt['state'], 'prepared')
            self.assertEqual(self.ui.save_calls, 0)
            self.error('attempt_exists', fake_flow.execute, session, 'release-1', **self.args)

    def test_unknown_after_save_restart_read_only(self):
        with self.profile() as session:
            self.setup_flow(session, 'lost_response')
            result = fake_flow.execute(session, 'release-1', **self.args)
            self.assertEqual(result['state'], 'unknown')
            self.attempt = result['attempt_id']
        self.ui.reopen()
        self.ui.tick()
        with self.profile() as session:
            result = fake_flow.reconcile(session, 'release-1', run_id=self.run,
                                         approval_id=self.args['approval_id'], attempt_id=self.attempt, ui=self.ui)
            self.assertEqual(result['state'], 'applied')
            self.assertEqual(self.ui.save_calls, 1)

    def test_consumed_before_journal_execute_crash_no_retry(self):
        with self.profile() as session:
            self.setup_flow(session)
            with patch('toolost_uploader.fake_flow.journal.execute', side_effect=SystemExit(17)):
                with self.assertRaises(SystemExit):
                    fake_flow.execute(session, 'release-1', **self.args)
            self.error('approval_consumed', fake_flow.execute, session, 'release-1', **self.args)
            attempt = journal.read_attempt(session, 'release-1', run_id=self.run)
            self.error('invalid_attempt_transition', fake_flow.reconcile, session, 'release-1',
                       run_id=self.run, approval_id=self.args['approval_id'], attempt_id=attempt['attempt_id'], ui=self.ui)
            self.assertEqual(self.ui.save_calls, 0)

    def test_error_outcome_and_changed_identity_reconcile(self):
        for route, expected in (('error', 'not_applied'), ('lost_response', 'conflict')):
            with self.profile(route) as session:
                self.setup_flow(session, route)
                attempt = fake_flow.execute(session, 'release-1', **self.args)
                if route == 'lost_response':
                    self.ui.draft = 'other'
                result = fake_flow.reconcile(session, 'release-1', run_id=self.run,
                                             approval_id=self.args['approval_id'], attempt_id=attempt['attempt_id'], ui=self.ui)
                self.assertEqual(result['state'], expected)
                self.assertEqual(self.ui.save_calls, 1)
