"""Jalankan dengan TOOLOST_TEST_DIST_DIR menunjuk hasil python -m build."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
import venv
import zipfile


@unittest.skipUnless(os.environ.get('TOOLOST_TEST_DIST_DIR'), 'Uji instalasi opt-in: set TOOLOST_TEST_DIST_DIR.')
class PackagingTests(unittest.TestCase):
    def test_artifacts_and_clean_wheel_install(self):
        dist = Path(os.environ['TOOLOST_TEST_DIST_DIR']).resolve()
        wheels = list(dist.glob('*.whl'))
        sdists = list(dist.glob('*.tar.gz'))
        self.assertEqual(len(wheels), 1)
        self.assertEqual(len(sdists), 1)
        with zipfile.ZipFile(wheels[0]) as archive:
            wheel_names = archive.namelist()
            self.assertIn('toolost_uploader/validation.py', wheel_names)
            metadata_name = next(name for name in wheel_names if name.endswith('.dist-info/METADATA'))
            metadata = archive.read(metadata_name).decode()
            self.assertIn('Private :: Do Not Upload', metadata)
            self.assertIn('Requires-Python: >=3.10', metadata)
            self.assertTrue(all('extra ==' in line for line in metadata.splitlines() if line.startswith('Requires-Dist:')))
            self.assertFalse(any(name.startswith(('tests/', 'scripts/', 'docs/')) for name in wheel_names))
        with tarfile.open(sdists[0]) as archive:
            sdist_names = archive.getnames()
        for name in wheel_names + sdist_names:
            self.assertFalse(set(Path(name).parts) & {'.local', '.venv', '.git', '__pycache__'})
            self.assertFalse(name.endswith(('.mp3', '.wav', '.pyc', '.env')))
        self.assertTrue(any(name.endswith('/docs/schemas/manifest-v1.schema.json') for name in sdist_names))
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            env = dict(os.environ)
            env.pop('PYTHONPATH', None)
            env.pop('PYTHONHOME', None)
            venv.EnvBuilder(with_pip=True).create(base / 'venv')
            binary = base / 'venv' / ('Scripts' if os.name == 'nt' else 'bin')
            python = binary / ('python.exe' if os.name == 'nt' else 'python')
            toolost = binary / ('toolost.exe' if os.name == 'nt' else 'toolost')

            def run(args):
                return subprocess.run(args, cwd=base, env=env, capture_output=True, text=True, timeout=90)

            installed = run([str(python), '-m', 'pip', 'install', '--no-index', '--no-deps', str(wheels[0])])
            self.assertEqual(installed.returncode, 0, installed.stderr)
            for args in ([str(toolost), '--help'], [str(toolost), '--version'],
                         [str(python), '-I', '-m', 'toolost_uploader', '--help']):
                result = run(args)
                self.assertEqual(result.returncode, 0, result.stderr)
            media = base / 'synthetic.bin'
            media.write_bytes(b'Synthetic test bytes only\n')
            reference = {'path': media.name, 'sha256': hashlib.sha256(media.read_bytes()).hexdigest()}
            manifest = {'schema_version': 1, 'release_id': 'test-release', 'release_type': 'single',
                        'title': 'Synthetic release', 'release_date': '2027-01-15', 'artwork': reference,
                        'tracks': [{'track_id': 'test-track', 'title': 'Synthetic track',
                                    'audio': reference, 'ai_assisted': True}]}
            path = base / 'manifest.json'
            path.write_text(json.dumps(manifest))
            for prefix in ([str(toolost)], [str(python), '-I', '-m', 'toolost_uploader']):
                valid = run([*prefix, 'validate', str(path), '--json'])
                self.assertEqual(valid.returncode, 0, valid.stderr)
                self.assertEqual(valid.stderr, '')
                self.assertEqual(json.loads(valid.stdout)['status'], 'valid')
                invalid = run([*prefix, 'validate', str(base / 'missing'), '--json'])
                self.assertEqual(invalid.returncode, 2)
                self.assertEqual(json.loads(invalid.stdout)['status'], 'invalid_input')
                unsupported = run([*prefix, 'upload', 'SECRET-ARGUMENT'])
                self.assertEqual(unsupported.returncode, 2)
                self.assertNotIn('SECRET-ARGUMENT', unsupported.stdout + unsupported.stderr)


if __name__ == '__main__':
    unittest.main()
