import json
import os
import unittest
from unittest.mock import patch

import test_storage
from toolost_uploader import approval, storage


@unittest.skipUnless(os.name == 'posix', 'Storage POSIX saja.')
class ApprovalTests(unittest.TestCase):
    setUp = test_storage.StorageTests.setUp
    profile = test_storage.StorageTests.profile
    error = test_storage.StorageTests.error
    directory = test_storage.StorageTests.directory

    def setup_gate(self, session):
        checkpoint = session.create_checkpoint(self.manifest, self.base)
        self.run = checkpoint['run_id']
        self.plan = {'operations': ['fake.upload', 'fake.edit', 'fake.save'], 'desired_sha256': 'a' * 64}
        self.target = dict(account='synthetic-account', draft='synthetic-draft')
        approval.bind(session, account=self.target['account'], reviewed=True)

    def approve(self, session):
        return approval.approve(session, 'release-1', run_id=self.run, expected_revision=1,
                                plan=self.plan, approved=True, **self.target)

    def test_consume_once_no_remote_claim(self):
        with self.profile() as session:
            self.setup_gate(session)
            record = self.approve(session)
            args = dict(run_id=self.run, approval_id=record['approval_id'], plan=self.plan, **self.target)
            self.assertEqual(approval.consume(session, 'release-1', **args)['state'], 'consumed')
            self.error('approval_consumed', approval.consume, session, 'release-1', **args)
            self.assertIsNone(session.read_checkpoint('release-1')['account_fingerprint'])
            self.error('approval_record_exists', self.approve, session)

    def test_binding_manual_and_immutable(self):
        with self.profile() as session:
            self.error('binding_review_required', approval.bind, session, account='synthetic-account', reviewed=False)
            self.error('identity_review_required', approval.bind, session, account='user@example.invalid', reviewed=True)
            approval.bind(session, account='synthetic-account', reviewed=True)
            self.error('approval_record_exists', approval.bind, session, account='synthetic-account', reviewed=True)
        self.error('profile_closed', approval.bind, session, account='synthetic-account', reviewed=True)

    def test_no_approval_or_no_binding_blocks(self):
        with self.profile() as session:
            record = session.create_checkpoint(self.manifest, self.base)
            kwargs = dict(run_id=record['run_id'], expected_revision=1, account='synthetic-account',
                          draft='synthetic-draft', plan={'operations': ['fake.save'], 'desired_sha256': 'a' * 64})
            self.error('binding_review_required', approval.approve, session, 'release-1', approved=True, **kwargs)
            approval.bind(session, account='synthetic-account', reviewed=True)
            self.error('confirmation_required', approval.approve, session, 'release-1', approved=False, **kwargs)

    def test_changed_target_plan_checkpoint(self):
        with self.profile() as session:
            self.setup_gate(session)
            record = self.approve(session)
            args = dict(run_id=self.run, approval_id=record['approval_id'], plan=self.plan, **self.target)
            for field, value, code in (('account', None, 'identity_review_required'),
                                      ('draft', 'other', 'identity_review_required'),
                                      ('approval_id', 'wrong', 'approval_mismatch'),
                                      ('plan', {'operations': ['fake.save'], 'desired_sha256': 'a' * 64}, 'approval_stale')):
                changed = dict(args)
                changed[field] = value
                self.error(code, approval.consume, session, 'release-1', **changed)
            path = self.directory / 'checkpoints/release-1.json'
            checkpoint = json.loads(path.read_text())
            checkpoint['revision'] = 2
            checkpoint['record_sha256'] = storage._digest({k: v for k, v in checkpoint.items() if k != 'record_sha256'})
            path.write_text(json.dumps(checkpoint))
            self.error('approval_stale', approval.consume, session, 'release-1', **args)

    def test_publish_delete_unknown_plan_rejected(self):
        with self.profile() as session:
            self.setup_gate(session)
            for operations in (['publish'], ['fake.delete'], [], ['fake.save', 'fake.save']):
                self.plan['operations'] = operations
                self.error('invalid_draft_plan', self.approve, session)
            self.plan['operations'] = ['fake.save']
            self.plan['cookie'] = 'secret'
            self.error('invalid_draft_plan', self.approve, session)

    def test_corrupt_record_no_consume(self):
        with self.profile() as session:
            self.setup_gate(session)
            record = self.approve(session)
            path = self.directory / 'checkpoints/release-1.approval.json'
            record['plan_sha256'] = '0' * 64
            path.write_text(json.dumps(record))
            self.error('approval_hash_mismatch', approval.consume, session, 'release-1', run_id=self.run,
                       approval_id=record['approval_id'], plan=self.plan, **self.target)

    def test_consume_write_outcome_unknown_stays_consumed(self):
        with self.profile() as session:
            self.setup_gate(session)
            record = self.approve(session)
            args = dict(run_id=self.run, approval_id=record['approval_id'], plan=self.plan, **self.target)
            original = os.fsync
            calls = []

            def fsync(fd):
                calls.append(fd)
                if len(calls) == 2:
                    raise OSError('private error')
                original(fd)

            with patch('toolost_uploader.storage.os.fsync', side_effect=fsync):
                self.error('write_outcome_unknown', approval.consume, session, 'release-1', **args)
            self.error('approval_consumed', approval.consume, session, 'release-1', **args)
