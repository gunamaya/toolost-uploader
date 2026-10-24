import copy
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_storage
from toolost_uploader import fake_upload as upload, storage


@unittest.skipUnless(os.name == 'posix', 'Storage POSIX saja.')
class FakeUploadTests(unittest.TestCase):
    setUp = test_storage.StorageTests.setUp
    profile = test_storage.StorageTests.profile
    error = test_storage.StorageTests.error
    directory = test_storage.StorageTests.directory

    def setup_upload(self, session, duplicate=False):
        second = copy.deepcopy(self.manifest['tracks'][0])
        second['track_id'] = 'track-2'
        if not duplicate:
            second['audio']['path'] = 'second.bin'
            (self.base / 'second.bin').write_bytes(self.asset.read_bytes())
        self.manifest['tracks'].append(second)
        checkpoint = session.create_checkpoint(self.manifest, self.base)
        self.run = checkpoint['run_id']
        upload.initialize(session, 'release-1', run_id=self.run)
        record = upload.prepare(session, 'release-1', run_id=self.run, expected_revision=1)
        self.args = dict(run_id=self.run, attempt_id=record['attempt_id'])
        return record

    def test_restart_in_other_process_no_reupload(self):
        with self.profile() as session:
            self.setup_upload(session)
            self.assertEqual(upload.execute(session, 'release-1', mode='lost_response', **self.args)['state'], 'unknown')
        program = '''import sys
from toolost_uploader import storage, fake_upload as u
with storage.profile('test', root=sys.argv[1]) as s:
    args=dict(run_id=sys.argv[2], attempt_id=sys.argv[3])
    assert u.reconcile(s, 'release-1', **args)['state']=='unknown'
    u.settle(s, 'release-1', run_id=args['run_id'])
    assert u.reconcile(s, 'release-1', **args)['state']=='applied'
    assert u.observe(s, 'release-1', run_id=args['run_id'])['upload_calls']==1
'''
        result = subprocess.run([sys.executable, '-c', program, str(self.root), self.run, self.args['attempt_id']],
                                env=dict(os.environ, PYTHONPATH=str(test_storage.ROOT)), capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        with self.profile() as session:
            server = upload.observe(session, 'release-1', run_id=self.run)
            self.assertEqual([t['track_id'] for t in server['tracks']], ['track-2', 'track-1'])
            self.error('reconciliation_required', upload.execute, session, 'release-1', **self.args)
            self.assertEqual(server['upload_calls'], 1)

    def test_partial_failed_encoding_and_duplicate_names_unknown(self):
        for mode, duplicate, failed in (('partial', False, False), ('pending', False, True), ('pending', True, False)):
            with self.subTest(mode=mode, duplicate=duplicate), self.profile(mode + str(duplicate) + str(failed)) as session:
                # setUp manifest is copied so each scenario has exactly two tracks.
                self.manifest['tracks'] = self.manifest['tracks'][:1]
                self.setup_upload(session, duplicate=duplicate)
                upload.execute(session, 'release-1', mode=mode, **self.args)
                upload.settle(session, 'release-1', run_id=self.run, failed=failed)
                self.assertEqual(upload.reconcile(session, 'release-1', **self.args)['state'], 'unknown')
                self.error('reconciliation_required', upload.execute, session, 'release-1', **self.args)
                self.assertEqual(upload.observe(session, 'release-1', run_id=self.run)['upload_calls'], 1)

    def test_intent_fsync_unknown_stops_before_upload(self):
        with self.profile() as session:
            self.setup_upload(session)
            original = os.fsync
            calls = []

            def fsync(fd):
                calls.append(fd)
                if len(calls) == 2:
                    raise OSError('private path')
                original(fd)

            with patch('toolost_uploader.storage.os.fsync', side_effect=fsync):
                self.error('write_outcome_unknown', upload.execute, session, 'release-1', **self.args)
            self.assertEqual(upload.observe(session, 'release-1', run_id=self.run)['upload_calls'], 0)
            self.error('reconciliation_required', upload.execute, session, 'release-1', **self.args)
            self.assertEqual(upload.reconcile(session, 'release-1', **self.args)['state'], 'not_applied')

    def test_wrong_run_attempt_version_and_unknown_keys(self):
        with self.profile() as session:
            self.setup_upload(session)
            self.error('run_mismatch', upload.observe, session, 'release-1', run_id='other')
            self.error('attempt_mismatch', upload.execute, session, 'release-1', run_id=self.run, attempt_id='other')
            self.error('invalid_fake_mode', upload.execute, session, 'release-1', mode='retry', **self.args)
            path = self.directory / 'checkpoints/release-1.upload-attempt.json'
            original = upload.read_attempt(session, 'release-1', run_id=self.run)
            for key, value, code in (('version', True, 'invalid_fixture'),
                                     ('password', 'SECRET', 'invalid_fixture'),
                                     ('batch_sha256', '0' * 64, 'batch_mismatch')):
                record = dict(original)
                record[key] = value
                upload._save(session, path.name, record)
                self.error(code, upload.read_attempt, session, 'release-1', run_id=self.run)

    def test_failed_encoding_not_promoted_by_settle(self):
        with self.profile() as session:
            self.setup_upload(session)
            upload.execute(session, 'release-1', **self.args)
            upload.settle(session, 'release-1', run_id=self.run, failed=True)
            upload.settle(session, 'release-1', run_id=self.run)
            self.assertTrue(all(t['encoding'] == 'failed' for t in upload.observe(session, 'release-1', run_id=self.run)['tracks']))
            self.assertEqual(upload.reconcile(session, 'release-1', **self.args)['state'], 'unknown')

    def test_before_send_no_retry_even_not_applied(self):
        with self.profile() as session:
            self.setup_upload(session)
            upload.execute(session, 'release-1', mode='before_send', **self.args)
            self.assertEqual(upload.reconcile(session, 'release-1', **self.args)['state'], 'not_applied')
            self.error('reconciliation_required', upload.execute, session, 'release-1', **self.args)
            self.error('fixture_exists', upload.prepare, session, 'release-1', run_id=self.run, expected_revision=1)

    def test_fault_before_intent_and_after_ingest(self):
        with self.profile() as session:
            self.setup_upload(session)
            with patch('toolost_uploader.fake_upload._save', side_effect=storage.StorageError('write_failed')):
                self.error('write_failed', upload.execute, session, 'release-1', **self.args)
            self.assertEqual(upload.observe(session, 'release-1', run_id=self.run)['upload_calls'], 0)
            original = upload._save
            calls = []

            def die_after_server(*args):
                result = original(*args)
                calls.append(1)
                if len(calls) == 2:
                    raise SystemExit(17)
                return result

            with patch('toolost_uploader.fake_upload._save', side_effect=die_after_server):
                with self.assertRaises(SystemExit):
                    upload.execute(session, 'release-1', **self.args)
        with self.profile() as session:
            self.error('reconciliation_required', upload.execute, session, 'release-1', **self.args)
            upload.settle(session, 'release-1', run_id=self.run)
            self.assertEqual(upload.reconcile(session, 'release-1', **self.args)['state'], 'applied')
            self.assertEqual(upload.observe(session, 'release-1', run_id=self.run)['upload_calls'], 1)

    def test_identity_and_corruption_fail_closed(self):
        with self.profile() as session:
            self.setup_upload(session)
            path = self.directory / 'checkpoints/release-1.fake-server.json'
            server = json.loads(path.read_text())
            server['account'] = 'other'
            upload._save(session, path.name, server)
            self.error('fake_identity_mismatch', upload.execute, session, 'release-1', **self.args)
            server['account'] = 'synthetic-account'
            upload._save(session, path.name, server)
            upload.execute(session, 'release-1', **self.args)
            server = upload.observe(session, 'release-1', run_id=self.run)
            server['draft'] = 'other'
            upload._save(session, path.name, server)
            self.assertEqual(upload.reconcile(session, 'release-1', **self.args)['state'], 'conflict')
            server['draft'] = 'tampered-without-hash'
            path.write_text(json.dumps(server))
            self.error('fixture_hash_mismatch', upload.observe, session, 'release-1', run_id=self.run)

    def test_reconcile_read_only_pending_server(self):
        with self.profile() as session:
            self.setup_upload(session)
            upload.execute(session, 'release-1', **self.args)
            path = self.directory / 'checkpoints/release-1.fake-server.json'
            before = path.read_bytes()
            for _ in range(3):
                self.assertEqual(upload.reconcile(session, 'release-1', **self.args)['state'], 'unknown')
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(upload.observe(session, 'release-1', run_id=self.run)['upload_calls'], 1)
