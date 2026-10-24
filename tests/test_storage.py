import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from toolost_uploader import storage


@unittest.skipUnless(os.name == 'posix', 'Storage privat POSIX saja.')
class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'state'
        self.asset = self.base / 'synthetic.bin'
        content = b'Synthetic bytes only, not real media.\n'
        self.asset.write_bytes(content)
        reference = {'path': self.asset.name, 'sha256': hashlib.sha256(content).hexdigest()}
        self.manifest = {'schema_version': 1, 'release_id': 'release-1', 'release_type': 'single',
                         'title': 'Synthetic release', 'release_date': '2027-01-15', 'artwork': reference,
                         'tracks': [{'track_id': 'track-1', 'title': 'Synthetic track',
                                     'audio': copy.deepcopy(reference), 'ai_assisted': True}]}

    def profile(self, alias='test'):
        return storage.profile(alias, root=self.root)

    @property
    def directory(self):
        return self.root / 'profiles/test'

    @property
    def checkpoint(self):
        return self.directory / 'checkpoints/release-1.json'

    def error(self, code, function, *args, **kwargs):
        with self.assertRaises(storage.StorageError) as raised:
            function(*args, **kwargs)
        self.assertEqual(raised.exception.code, code)
        self.assertNotIn(str(self.base), str(raised.exception))

    def test_profile_permissions_and_no_browser(self):
        with self.profile() as session:
            config = json.loads((self.directory / 'profile.json').read_text())
            self.assertEqual(config, {'storage_version': 1, 'profile': 'test', 'account_fingerprint': None})
            for path in (self.root, self.root / 'profiles', self.directory, self.directory / 'checkpoints'):
                self.assertEqual(path.stat().st_mode & 0o777, 0o700)
            for path in (self.directory / 'profile.json', self.directory / 'writer.lock'):
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(set(p.name for p in self.directory.iterdir()),
                             {'profile.json', 'writer.lock', 'checkpoints'})
        self.error('profile_closed', session.read_checkpoint, 'release-1')

    def test_invalid_alias_before_disk_access(self):
        for alias in ('', '../escape', '..', '.', '/absolute', 'a/b', 'é', 'a' * 65, 1):
            with self.subTest(alias=alias):
                with self.assertRaises(storage.StorageError):
                    with self.profile(alias):
                        self.fail('invalid alias accepted')
        self.assertFalse(self.root.exists())

    def test_alias_config_mismatch(self):
        with self.profile():
            pass
        config_path = self.directory / 'profile.json'
        config = json.loads(config_path.read_text())
        config['profile'] = 'other'
        config_path.write_text(json.dumps(config))
        with self.assertRaises(storage.StorageError):
            with self.profile():
                self.fail('mismatched alias accepted')

    def test_corrupt_config_not_recreated_and_caller_error_preserved(self):
        with self.assertRaisesRegex(OSError, 'caller failure'):
            with self.profile():
                raise OSError('caller failure')
        config = self.directory / 'profile.json'
        for raw in ('[]', 'null', '{"profile":"a","profile":"b"}', 'broken'):
            config.write_text(raw)
            with self.assertRaises(storage.StorageError):
                with self.profile():
                    self.fail('corrupt config accepted')
            self.assertEqual(config.read_text(), raw)

    def test_fail_closed_permissions_and_links(self):
        with self.profile():
            pass
        targets = (self.root, self.directory, self.directory / 'profile.json', self.directory / 'writer.lock')
        for target in targets:
            mode = target.stat().st_mode & 0o777
            target.chmod(0o755 if target.is_dir() else 0o644)
            try:
                with self.assertRaises(storage.StorageError):
                    with self.profile():
                        self.fail('unsafe mode accepted')
                self.assertEqual(target.stat().st_mode & 0o777, 0o755 if target.is_dir() else 0o644)
            finally:
                target.chmod(mode)
        os.link(self.directory / 'profile.json', self.base / 'hardlink')
        with self.assertRaises(storage.StorageError):
            with self.profile():
                self.fail('hardlink accepted')

    def test_owner_mismatch(self):
        info = self.base.stat()
        with patch('toolost_uploader.storage.os.geteuid', return_value=info.st_uid + 1):
            self.error('unsafe_permissions', storage._private, info, directory=True)

    def test_symlink_root_parent_and_profile_file(self):
        real = self.base / 'real'
        real.mkdir(mode=0o700)
        link = self.base / 'link'
        link.symlink_to(real, target_is_directory=True)
        for root in (link, link / 'child', Path('relative'), self.base / '..' / 'state'):
            with self.assertRaises(storage.StorageError):
                with storage.profile('test', root=root):
                    self.fail('unsafe root accepted')
        with self.profile():
            pass
        path = self.directory / 'profile.json'
        path.unlink()
        path.symlink_to(self.asset)
        with self.assertRaises(storage.StorageError):
            with self.profile():
                self.fail('symlink accepted')
        self.assertTrue(self.asset.read_bytes().startswith(b'Synthetic'))

    def test_checkpoint_snapshot_hash_identity_no_reupload(self):
        with self.profile() as session:
            record = session.create_checkpoint(self.manifest, self.base)
            self.assertEqual(record['state'], 'validated')
            self.assertIsNone(record['account_fingerprint'])
            self.assertIsNone(record['remote_draft_id'])
            self.assertEqual(self.checkpoint.stat().st_mode & 0o777, 0o600)
            self.manifest['title'] = 'Changed outside snapshot'
            record['manifest']['title'] = 'Changed return value'
            self.asset.unlink()
            reread = session.read_checkpoint('release-1')
            self.assertEqual(reread['manifest']['title'], 'Synthetic release')
            self.assertNotIn('Changed', self.checkpoint.read_text())
            self.error('invalid_identifier', session.read_checkpoint, '../escape')

    def test_existing_checkpoint_never_overwritten(self):
        with self.profile() as session:
            first = session.create_checkpoint(self.manifest, self.base)
            self.error('checkpoint_exists', session.create_checkpoint, self.manifest, self.base)
            self.assertEqual(session.read_checkpoint('release-1'), first)
            self.checkpoint.write_text('corrupt')
            self.error('corrupt_record', session.create_checkpoint, self.manifest, self.base)
            self.assertEqual(self.checkpoint.read_text(), 'corrupt')

    def test_manifest_validation_and_no_credentials(self):
        for mutate in ('unknown', 'hash', 'ai'):
            data = copy.deepcopy(self.manifest)
            if mutate == 'unknown':
                data['cookie'] = 'PRIVATE-SECRET'
            elif mutate == 'hash':
                data['artwork']['sha256'] = '0' * 64
            else:
                data['tracks'][0]['ai_assisted'] = None
            with self.profile() as session:
                self.error('invalid_manifest', session.create_checkpoint, data, self.base)
            self.assertFalse(self.checkpoint.exists())

    def test_cancel_revision_and_closed_handle(self):
        with self.profile() as session:
            record = session.create_checkpoint(self.manifest, self.base)
            self.error('run_mismatch', session.cancel_checkpoint, 'release-1', run_id='other', expected_revision=1)
            self.error('revision_conflict', session.cancel_checkpoint, 'release-1', run_id=record['run_id'], expected_revision=True)
            cancelled = session.cancel_checkpoint('release-1', run_id=record['run_id'], expected_revision=1)
            self.assertEqual(cancelled['revision'], 2)
            self.assertEqual(cancelled['state'], 'cancelled')
            self.error('revision_conflict', session.cancel_checkpoint, 'release-1', run_id=record['run_id'], expected_revision=1)
            self.error('invalid_transition', session.cancel_checkpoint, 'release-1', run_id=record['run_id'], expected_revision=2)
        self.error('profile_closed', session.cancel_checkpoint, 'release-1', run_id=record['run_id'], expected_revision=2)

    def test_corruption_duplicate_unknown_and_hash(self):
        with self.profile() as session:
            record = session.create_checkpoint(self.manifest, self.base)
            for field, value, code in (
                ('profile', 'other', 'checkpoint_mismatch'),
                ('manifest_sha256', '0' * 64, 'manifest_hash_mismatch'),
                ('record_sha256', '0' * 64, 'record_hash_mismatch'),
                ('remote_draft_id', 'made-up', 'invalid_record'),
                ('state', 'draft_saved', 'invalid_record'),
                ('password', 'SECRET', 'invalid_record'),
                ('revision', True, 'invalid_record'),
            ):
                data = copy.deepcopy(record)
                data[field] = value
                self.checkpoint.write_text(json.dumps(data))
                self.error(code, session.read_checkpoint, 'release-1')
            for raw in ('{"a":1,"a":2}', '{"a":NaN}', '[1]', 'not json'):
                self.checkpoint.write_text(raw)
                with self.assertRaises(storage.StorageError):
                    session.read_checkpoint('release-1')

    def test_failure_before_rename_preserves_old_and_cleans_temp(self):
        with self.profile() as session:
            record = session.create_checkpoint(self.manifest, self.base)
            before = self.checkpoint.read_bytes()
            for operation in ('os.replace', 'os.fsync'):
                with patch('toolost_uploader.storage.' + operation, side_effect=OSError('PRIVATE-PATH')):
                    self.error('write_failed', session.cancel_checkpoint, 'release-1',
                               run_id=record['run_id'], expected_revision=1)
                self.assertEqual(self.checkpoint.read_bytes(), before)
                self.assertEqual(list(self.checkpoint.parent.glob('.pending-*')), [])

    def test_failure_after_rename_reports_unknown_not_rollback(self):
        with self.profile() as session:
            record = session.create_checkpoint(self.manifest, self.base)
            original = os.fsync
            calls = []

            def fsync(fd):
                calls.append(fd)
                if len(calls) == 2:
                    raise OSError('directory sync failed')
                return original(fd)

            with patch('toolost_uploader.storage.os.fsync', side_effect=fsync):
                self.error('write_outcome_unknown', session.cancel_checkpoint, 'release-1',
                           run_id=record['run_id'], expected_revision=1)
            self.assertEqual(session.read_checkpoint('release-1')['state'], 'cancelled')
            self.error('revision_conflict', session.cancel_checkpoint, 'release-1',
                       run_id=record['run_id'], expected_revision=1)

    def test_lock_same_process_and_other_alias(self):
        with self.profile():
            with self.assertRaises(storage.StorageError) as raised:
                with self.profile():
                    self.fail('concurrent writer accepted')
            self.assertEqual(raised.exception.code, 'profile_locked')
            with self.profile('other'):
                pass
        with self.profile():
            pass

    def test_lock_process_death_releases_without_unlink(self):
        program = '''import sys
from toolost_uploader.storage import profile
with profile('test', root=sys.argv[1]):
    print('locked', flush=True)
    sys.stdin.read()
'''
        env = dict(os.environ, PYTHONPATH=str(ROOT))
        child = subprocess.Popen([sys.executable, '-c', program, str(self.root)], env=env,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'locked')
            inode = (self.directory / 'writer.lock').stat().st_ino
            with self.assertRaises(storage.StorageError):
                with self.profile():
                    self.fail('second process acquired lock')
            child.kill()
            child.communicate(timeout=10)
            with self.profile():
                self.assertEqual((self.directory / 'writer.lock').stat().st_ino, inode)
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=10)

    def test_checkpoint_symlink_and_size_limit(self):
        with self.profile() as session:
            session.create_checkpoint(self.manifest, self.base)
            self.checkpoint.unlink()
            self.checkpoint.symlink_to(self.asset)
            with self.assertRaises(storage.StorageError):
                session.read_checkpoint('release-1')
            self.checkpoint.unlink()
            self.checkpoint.write_bytes(b'x' * (storage.MAX_RECORD_BYTES + 1))
            self.checkpoint.chmod(0o600)
            self.error('record_too_large', session.read_checkpoint, 'release-1')

    def test_process_crash_at_replace_boundary(self):
        program = '''import os, sys
from toolost_uploader import storage
with storage.profile('test', root=sys.argv[1]) as session:
    record = session.read_checkpoint('release-1')
    original = storage.os.replace
    def crash(*args, **kwargs):
        if sys.argv[2] == 'after':
            original(*args, **kwargs)
        os._exit(17)
    storage.os.replace = crash
    session.cancel_checkpoint('release-1', run_id=record['run_id'], expected_revision=1)
'''
        with self.profile() as session:
            session.create_checkpoint(self.manifest, self.base)
        for stage, state in (('before', 'validated'), ('after', 'cancelled')):
            result = subprocess.run([sys.executable, '-c', program, str(self.root), stage],
                                    env=dict(os.environ, PYTHONPATH=str(ROOT)), capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 17, result.stderr)
            with self.profile() as session:
                record = session.read_checkpoint('release-1')
                self.assertEqual(record['state'], state)
        # Orphan temp dari crash sebelum rename tidak dipakai sebagai checkpoint.
        self.assertEqual(len(list(self.checkpoint.parent.glob('.pending-*'))), 1)

    def test_default_paths_and_unsupported(self):
        with patch('toolost_uploader.storage.sys.platform', 'darwin'), patch('pathlib.Path.home', return_value=self.base):
            self.assertEqual(storage.default_root(), self.base / 'Library/Application Support/toolost-uploader')
        with patch('toolost_uploader.storage.sys.platform', 'linux'), patch.dict(os.environ, {'XDG_STATE_HOME': str(self.base)}):
            self.assertEqual(storage.default_root(), self.base / 'toolost-uploader')
        with patch('toolost_uploader.storage.sys.platform', 'linux'), patch.dict(os.environ, {'XDG_STATE_HOME': 'relative'}):
            self.error('unsafe_storage_path', storage.default_root)
        with patch('toolost_uploader.storage.sys.platform', 'win32'):
            self.error('unsupported_platform', storage.default_root)


if __name__ == '__main__':
    unittest.main()
