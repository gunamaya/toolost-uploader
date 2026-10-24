import os
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_storage
from toolost_uploader import approval, fake_flow, fake_upload, storage


@unittest.skipUnless(os.name == 'posix', 'Storage POSIX saja.')
class GatedUploadTests(unittest.TestCase):
    setUp = test_storage.StorageTests.setUp
    profile = test_storage.StorageTests.profile
    error = test_storage.StorageTests.error

    def setup_gate(self, session, save_plan=False):
        checkpoint = session.create_checkpoint(self.manifest, self.base)
        self.run = checkpoint['run_id']
        fake_upload.initialize(session, 'release-1', run_id=self.run)
        approval.bind(session, account='synthetic-account', reviewed=True)
        plan = fake_flow.upload_plan(session, 'release-1', run_id=self.run)
        if save_plan:
            plan['operations'] = ['fake.save']
        record = approval.approve(session, 'release-1', run_id=self.run, expected_revision=1,
                                  account='synthetic-account', draft='synthetic-draft', plan=plan, approved=True)
        self.args = dict(run_id=self.run, approval_id=record['approval_id'], expected_revision=1)

    def calls(self, session):
        return fake_upload.observe(session, 'release-1', run_id=self.run)['upload_calls']

    def test_consumed_gate_before_upload_and_read_only_restart(self):
        with self.profile() as session:
            self.setup_gate(session)
            attempt = fake_flow.execute_upload(session, 'release-1', mode='lost_response', **self.args)
            self.assertEqual(attempt['state'], 'unknown')
            self.error('approval_consumed', fake_flow.execute_upload, session, 'release-1', **self.args)
            self.assertEqual(self.calls(session), 1)
        program = '''import sys
from toolost_uploader import storage, fake_flow as f, fake_upload as u
with storage.profile('test', root=sys.argv[1]) as s:
    args=dict(run_id=sys.argv[2], approval_id=sys.argv[3], attempt_id=sys.argv[4])
    assert f.reconcile_upload(s, 'release-1', **args)['state']=='unknown'
    u.settle(s, 'release-1', run_id=args['run_id'])
    assert f.reconcile_upload(s, 'release-1', **args)['state']=='applied'
    assert u.observe(s, 'release-1', run_id=args['run_id'])['upload_calls']==1
'''
        result = subprocess.run([sys.executable, '-c', program, str(self.root), self.run,
                                 self.args['approval_id'], attempt['attempt_id']],
                                env=dict(os.environ, PYTHONPATH=str(test_storage.ROOT)), capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_save_approval_and_wrong_token_block_upload(self):
        with self.profile() as session:
            self.setup_gate(session, save_plan=True)
            self.error('approval_stale', fake_flow.execute_upload, session, 'release-1', **self.args)
            self.error('approval_mismatch', fake_flow.execute_upload, session, 'release-1',
                       **dict(self.args, approval_id='wrong'))
            self.assertEqual(self.calls(session), 0)
            self.error('fixture_not_found', fake_upload.read_attempt, session, 'release-1', run_id=self.run)

    def test_identity_changed_after_upload_conflicts_without_retry(self):
        with self.profile() as session:
            self.setup_gate(session)
            attempt = fake_flow.execute_upload(session, 'release-1', **self.args)
            server = fake_upload.observe(session, 'release-1', run_id=self.run)
            server['account'] = 'other'
            fake_upload._save(session, 'release-1.fake-server.json', server)
            result = fake_flow.reconcile_upload(session, 'release-1', run_id=self.run,
                                               approval_id=self.args['approval_id'], attempt_id=attempt['attempt_id'])
            self.assertEqual(result['state'], 'conflict')
            self.assertEqual(self.calls(session), 1)

    def test_consume_failure_no_upload_and_no_retry(self):
        with self.profile() as session:
            self.setup_gate(session)
            with patch('toolost_uploader.approval.consume', side_effect=storage.StorageError('write_failed')):
                self.error('write_failed', fake_flow.execute_upload, session, 'release-1', **self.args)
            attempt = fake_upload.read_attempt(session, 'release-1', run_id=self.run)
            self.assertEqual(attempt['state'], 'prepared')
            self.assertEqual(self.calls(session), 0)
            self.error('fixture_exists', fake_flow.execute_upload, session, 'release-1', **self.args)
            self.error('approval_not_consumed', fake_flow.reconcile_upload, session, 'release-1',
                       run_id=self.run, approval_id=self.args['approval_id'], attempt_id=attempt['attempt_id'])

    def test_crash_after_consume_does_not_replay_upload(self):
        with self.profile() as session:
            self.setup_gate(session)
            with patch('toolost_uploader.fake_flow.fake_upload.execute', side_effect=SystemExit(17)):
                with self.assertRaises(SystemExit):
                    fake_flow.execute_upload(session, 'release-1', **self.args)
            self.error('approval_consumed', fake_flow.execute_upload, session, 'release-1', **self.args)
            attempt = fake_upload.read_attempt(session, 'release-1', run_id=self.run)
            self.error('invalid_attempt_transition', fake_flow.reconcile_upload, session, 'release-1',
                       run_id=self.run, approval_id=self.args['approval_id'], attempt_id=attempt['attempt_id'])
            self.assertEqual(self.calls(session), 0)

    def test_before_send_terminal_not_applied_no_replay(self):
        with self.profile() as session:
            self.setup_gate(session)
            attempt = fake_flow.execute_upload(session, 'release-1', mode='before_send', **self.args)
            args = dict(run_id=self.run, approval_id=self.args['approval_id'], attempt_id=attempt['attempt_id'])
            self.assertEqual(fake_flow.reconcile_upload(session, 'release-1', **args)['state'], 'not_applied')
            self.error('approval_consumed', fake_flow.execute_upload, session, 'release-1', **self.args)
            self.assertEqual(self.calls(session), 0)

    def test_invalid_mode_and_revision_leave_approval_unconsumed(self):
        with self.profile() as session:
            self.setup_gate(session)
            self.error('invalid_fake_mode', fake_flow.execute_upload, session, 'release-1', mode='publish', **self.args)
            self.error('revision_conflict', fake_flow.execute_upload, session, 'release-1',
                       **dict(self.args, expected_revision=2))
            approval.verify(session, 'release-1', run_id=self.run, approval_id=self.args['approval_id'],
                            account='synthetic-account', draft='synthetic-draft',
                            plan=fake_flow.upload_plan(session, 'release-1', run_id=self.run))
            self.assertEqual(self.calls(session), 0)
