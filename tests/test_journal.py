import json
import os
from unittest.mock import patch
import unittest

import test_storage
from toolost_uploader import journal, storage


@unittest.skipUnless(os.name == 'posix', 'Storage POSIX saja.')
class JournalTests(unittest.TestCase):
    setUp = test_storage.StorageTests.setUp
    profile = test_storage.StorageTests.profile
    error = test_storage.StorageTests.error
    directory = test_storage.StorageTests.directory

    def setup_attempt(self, session, mode='success'):
        checkpoint = session.create_checkpoint(self.manifest, self.base)
        baseline = {'title': 'Before', 'track_ids': ['track-1']}
        self.desired = {'title': 'After', 'track_ids': ['track-1', 'track-2']}
        self.adapter = journal.FakeAdapter(baseline, mode=mode)
        self.run = checkpoint['run_id']
        attempt = journal.prepare(session, 'release-1', run_id=self.run, expected_revision=1,
                                  adapter=self.adapter, desired=self.desired)
        self.attempt = attempt['attempt_id']
        return attempt

    def execute(self, session):
        return journal.execute(session, 'release-1', run_id=self.run, attempt_id=self.attempt,
                               adapter=self.adapter, desired=self.desired)

    def reconcile(self, session):
        return journal.reconcile(session, 'release-1', run_id=self.run, attempt_id=self.attempt, adapter=self.adapter)

    def test_success_readback_not_save_ack(self):
        with self.profile() as session:
            self.setup_attempt(session)
            self.assertEqual(self.execute(session)['state'], 'applied')
            self.assertEqual(self.adapter.save_calls, 1)
            self.error('reconciliation_required', self.execute, session)
            self.assertEqual(session.read_checkpoint('release-1')['state'], 'validated')

    def test_lost_response_restart_reconciles_without_save(self):
        with self.profile() as session:
            self.setup_attempt(session, 'lost_response')
            self.assertEqual(self.execute(session)['state'], 'unknown')
        with self.profile() as session:
            self.error('reconciliation_required', self.execute, session)
            self.assertEqual(self.reconcile(session)['state'], 'applied')
            self.assertEqual(self.adapter.save_calls, 1)

    def test_before_send_not_applied_no_retry(self):
        with self.profile() as session:
            self.setup_attempt(session, 'before_send')
            self.assertEqual(self.execute(session)['state'], 'unknown')
            self.assertEqual(self.reconcile(session)['state'], 'not_applied')

    def test_intent_durability_unknown_never_calls_adapter(self):
        with self.profile() as session:
            self.setup_attempt(session)
            original = os.fsync
            calls = []

            def fsync(fd):
                calls.append(fd)
                if len(calls) == 2:
                    raise OSError('private error')
                original(fd)

            with patch('toolost_uploader.storage.os.fsync', side_effect=fsync):
                self.error('write_outcome_unknown', self.execute, session)
            self.assertEqual(self.adapter.save_calls, 0)
            self.error('reconciliation_required', self.execute, session)
            self.assertEqual(self.reconcile(session)['state'], 'not_applied')
            self.error('reconciliation_required', self.execute, session)
            self.assertEqual(self.adapter.save_calls, 0)

    def test_partial_ambiguous_and_read_timeout_remain_unknown(self):
        for mode in ('partial', 'ambiguous', 'lost_response'):
            with self.subTest(mode=mode), self.profile(mode) as session:
                self.setup_attempt(session, mode)
                if mode == 'lost_response':
                    self.adapter.read_error = True
                    # execute preflight must read before mutating.
                    self.error('fake_observation_unavailable', self.execute, session)
                    self.assertEqual(self.adapter.save_calls, 0)
                    self.adapter.read_error = False
                    self.execute(session)
                    self.adapter.read_error = True
                else:
                    self.assertEqual(self.execute(session)['state'], 'unknown')
                self.assertEqual(self.reconcile(session)['state'], 'unknown')
                self.assertEqual(self.adapter.save_calls, 1)

    def test_account_draft_and_changed_state_conflicts(self):
        with self.profile() as session:
            self.setup_attempt(session, 'lost_response')
            self.execute(session)
            self.adapter.draft = 'other'
            self.assertEqual(self.reconcile(session)['state'], 'conflict')
            self.assertEqual(self.adapter.save_calls, 1)
        with self.profile('other') as session:
            self.setup_attempt(session, 'before_send')
            self.execute(session)
            self.adapter.state['title'] = 'Human changed'
            self.assertEqual(self.reconcile(session)['state'], 'conflict')

    def test_preflight_mismatch_and_duplicate_intent(self):
        with self.profile() as session:
            self.setup_attempt(session)
            self.error('attempt_exists', journal.prepare, session, 'release-1', run_id=self.run,
                       expected_revision=1, adapter=self.adapter, desired=self.desired)
            self.desired['title'] = 'Changed desired'
            self.error('desired_mismatch', self.execute, session)
            self.desired['title'] = 'After'
            self.adapter.account = 'other'
            self.error('fake_identity_mismatch', self.execute, session)
            self.adapter.account = 'synthetic-account'
            self.adapter.state['title'] = 'Changed baseline'
            self.error('baseline_conflict', self.execute, session)
            self.assertEqual(self.adapter.save_calls, 0)

    def test_write_before_mutation_and_failure_after_save(self):
        with self.profile() as session:
            self.setup_attempt(session)
            original = journal._atomic_write
            with patch('toolost_uploader.journal._atomic_write', side_effect=storage.StorageError('write_failed')):
                self.error('write_failed', self.execute, session)
            self.assertEqual(self.adapter.save_calls, 0)
            calls = []

            def write(*args):
                calls.append(1)
                if len(calls) == 2:
                    raise storage.StorageError('write_failed')
                original(*args)

            with patch('toolost_uploader.journal._atomic_write', side_effect=write):
                self.error('write_failed', self.execute, session)
            self.assertEqual(self.adapter.save_calls, 1)
            self.assertEqual(journal.read_attempt(session, 'release-1', run_id=self.run)['state'], 'unknown')
            self.assertEqual(self.reconcile(session)['state'], 'applied')
            self.assertEqual(self.adapter.save_calls, 1)

    def test_crash_after_unknown_before_send(self):
        with self.profile() as session:
            self.setup_attempt(session)
            with patch.object(self.adapter, 'save', side_effect=SystemExit(17)):
                with self.assertRaises(SystemExit):
                    self.execute(session)
            self.assertEqual(journal.read_attempt(session, 'release-1', run_id=self.run)['state'], 'unknown')
        with self.profile() as session:
            self.error('reconciliation_required', self.execute, session)
            self.assertEqual(self.reconcile(session)['state'], 'not_applied')

    def test_corrupt_stale_and_wrong_adapter_fail_closed(self):
        with self.profile() as session:
            self.setup_attempt(session)
            self.error('fake_adapter_required', journal.execute, session, 'release-1', run_id=self.run,
                       attempt_id=self.attempt, adapter=object(), desired=self.desired)
            self.error('attempt_mismatch', journal.execute, session, 'release-1', run_id=self.run,
                       attempt_id='other', adapter=self.adapter, desired=self.desired)
            path = self.directory / 'checkpoints/release-1.attempt.json'
            record = json.loads(path.read_text())
            record['state'] = 'applied'
            path.write_text(json.dumps(record))
            self.error('journal_hash_mismatch', journal.read_attempt, session, 'release-1', run_id=self.run)
            path.write_text('{"secret":1,"secret":2}')
            self.error('corrupt_record', journal.read_attempt, session, 'release-1', run_id=self.run)

    def test_checkpoint_changes_and_cancel_block_journal(self):
        with self.profile() as session:
            self.setup_attempt(session)
            path = self.directory / 'checkpoints/release-1.json'
            record = json.loads(path.read_text())
            record['revision'] = 2
            record['record_sha256'] = storage._digest({k: v for k, v in record.items() if k != 'record_sha256'})
            path.write_text(json.dumps(record))
            self.error('journal_checkpoint_mismatch', self.execute, session)
            self.assertEqual(self.adapter.save_calls, 0)
            session.cancel_checkpoint('release-1', run_id=self.run, expected_revision=2)
            self.error('invalid_transition', journal.read_attempt, session, 'release-1', run_id=self.run)

    def test_prepare_noop_incomplete_and_stale_revision(self):
        with self.profile() as session:
            checkpoint = session.create_checkpoint(self.manifest, self.base)
            baseline = {'title': 'Same', 'track_ids': ['track-1']}
            adapter = journal.FakeAdapter(baseline)
            args = dict(run_id=checkpoint['run_id'], expected_revision=1, adapter=adapter, desired=baseline)
            self.error('no_change', journal.prepare, session, 'release-1', **args)
            args['expected_revision'] = True
            self.error('revision_conflict', journal.prepare, session, 'release-1', **args)
            args['expected_revision'] = 1
            adapter.complete = False
            self.error('reconciliation_required', journal.prepare, session, 'release-1', **args)
            self.assertEqual(adapter.save_calls, 0)
            self.assertFalse((self.directory / 'checkpoints/release-1.attempt.json').exists())
