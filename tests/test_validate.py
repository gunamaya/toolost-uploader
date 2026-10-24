import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/validate.py'
spec = importlib.util.spec_from_file_location('manifest_validator', SCRIPT)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.manifest = json.loads((ROOT / 'docs/contract-manifest.example.json').read_text())
        for reference in (self.manifest['artwork'], self.manifest['tracks'][0]['audio']):
            path = self.base / reference['path']
            path.parent.mkdir(parents=True, exist_ok=True)
            content = b'SYNTHETIC TEST BYTES, NOT PRODUCTION MEDIA\n'
            path.write_bytes(content)
            reference['sha256'] = hashlib.sha256(content).hexdigest()
        self.path = self.base / 'manifest.json'

    def run_manifest(self, manifest=None):
        self.path.write_text(json.dumps(self.manifest if manifest is None else manifest), encoding='utf-8')
        return validator.validate(self.path)

    def assert_invalid(self, manifest, code):
        result = self.run_manifest(manifest)
        self.assertEqual(result['status'], 'invalid_input', result)
        self.assertEqual(result['error']['code'], code)
        self.assertNotIn(str(self.base), json.dumps(result))
        return result

    def test_valid_relative_paths_from_other_cwd(self):
        self.run_manifest()
        run = subprocess.run([sys.executable, str(SCRIPT), str(self.path), '--json'], cwd=ROOT,
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stderr, '')
        result = json.loads(run.stdout)
        self.assertEqual(result['status'], 'valid')
        self.assertFalse(result['remote_verified'])
        self.assertNotIn(str(self.base), run.stdout)

    def test_absolute_reference(self):
        self.manifest['artwork']['path'] = str(self.base / self.manifest['artwork']['path'])
        self.assertEqual(self.run_manifest()['status'], 'valid')

    def test_missing_and_null_ai(self):
        for value in (None, 0, 1, 'false'):
            with self.subTest(value=value):
                data = copy.deepcopy(self.manifest)
                data['tracks'][0]['ai_assisted'] = value
                self.assert_invalid(data, 'invalid_boolean')
        del self.manifest['tracks'][0]['ai_assisted']
        self.assert_invalid(self.manifest, 'missing_field')

    def test_unknown_keys_redacted_at_each_level(self):
        for target in ('release', 'track', 'file', 'copyright'):
            with self.subTest(target=target):
                data = copy.deepcopy(self.manifest)
                objects = {'release': data, 'track': data['tracks'][0], 'file': data['artwork']}
                data['copyright'] = {'c_year': 2027}
                objects['copyright'] = data['copyright']
                objects[target]['SECRET-KEY'] = 'secret-cookie-or-password'
                result = self.assert_invalid(data, 'unknown_field')
                self.assertNotIn('SECRET', json.dumps(result))
                self.assertNotIn('secret-cookie', json.dumps(result))

    def test_duplicate_keys_nested_and_root(self):
        for raw in ('{"schema_version":1,"schema_version":1}', '{"tracks":[{"title":"a","title":"b"}]}'):
            self.path.write_text(raw)
            self.assertEqual(validator.validate(self.path)['error']['code'], 'duplicate_key')

    def test_bad_json_and_nonfinite_redacted(self):
        for raw in ('not-json-private-value', '{"secret":NaN}', '{"secret":Infinity}', '\ufeff{}'):
            self.path.write_text(raw)
            result = validator.validate(self.path)
            self.assertEqual(result['status'], 'invalid_input')
            self.assertNotIn('private-value', json.dumps(result))

    def test_duplicate_track_ids(self):
        self.manifest['tracks'].append(copy.deepcopy(self.manifest['tracks'][0]))
        self.assert_invalid(self.manifest, 'duplicate_track_id')

    def test_hash_mismatch(self):
        self.manifest['artwork']['sha256'] = '0' * 64
        self.assert_invalid(self.manifest, 'hash_mismatch')

    def test_no_implicit_defaults_or_mutation(self):
        for key in ('instrumental', 'explicit', 'clean_version', 'language'):
            self.manifest['tracks'][0].pop(key, None)
        before = copy.deepcopy(self.manifest)
        validator.validate_manifest(self.manifest, self.base)
        self.assertEqual(self.manifest, before)

    def test_ai_conflict_is_warning_not_rewrite(self):
        self.manifest['tracks'][0]['ai_assisted'] = False
        result = self.run_manifest()
        self.assertEqual(result['status'], 'valid')
        self.assertTrue(any('Konflik' in item for item in result['warnings']))
        self.assertFalse(self.manifest['tracks'][0]['ai_assisted'])

    def test_dates_types_blank_and_unsupported(self):
        for key, value, code in (
            ('schema_version', True, 'unsupported_schema'),
            ('schema_version', 1.0, 'unsupported_schema'),
            ('schema_version', 2, 'unsupported_schema'),
            ('release_date', '2027-02-29', 'invalid_date'),
            ('release_date', '20270115', 'invalid_date'),
            ('title', '  ', 'invalid_text'),
            ('title', '\ud800', 'invalid_text'),
            ('release_id', '../account', 'invalid_id'),
            ('release_type', {}, 'invalid_release_type'),
            ('tracks', [], 'invalid_tracks'),
            ('tracks', [None], 'invalid_type'),
            ('artwork', None, 'invalid_type'),
            ('copyright', {}, 'invalid_copyright'),
            ('copyright', {'c_year': True}, 'invalid_year'),
        ):
            with self.subTest(key=key, value=repr(value)):
                data = copy.deepcopy(self.manifest)
                data[key] = value
                self.assert_invalid(data, code)

    def test_optional_null_or_clear_rejected(self):
        for value in (None, ''):
            data = copy.deepcopy(self.manifest)
            data['label'] = value
            self.assert_invalid(data, 'invalid_text')

    def test_missing_directory_empty_and_symlink(self):
        asset = self.base / self.manifest['artwork']['path']
        asset.unlink()
        self.assert_invalid(self.manifest, 'unreadable_input')
        asset.mkdir()
        self.assert_invalid(self.manifest, 'invalid_file')
        asset.rmdir()
        asset.write_bytes(b'')
        self.assert_invalid(self.manifest, 'empty_file')
        asset.unlink()
        asset.symlink_to(self.base / self.manifest['tracks'][0]['audio']['path'])
        self.assert_invalid(self.manifest, 'symlink_not_supported')

    def test_lyrics_hash_utf8_and_redaction(self):
        path = self.base / 'lyrics.txt'
        content = 'Lirik sintetis untuk tes.\n'.encode()
        path.write_bytes(content)
        reference = {'path': 'lyrics.txt', 'sha256': hashlib.sha256(content).hexdigest()}
        self.manifest['tracks'][0]['lyrics'] = reference
        result = self.run_manifest()
        self.assertEqual(result['status'], 'valid')
        self.assertNotIn('Lirik sintetis', json.dumps(result))
        path.write_bytes(b'\xff')
        reference['sha256'] = hashlib.sha256(b'\xff').hexdigest()
        self.assert_invalid(self.manifest, 'invalid_lyrics_encoding')

    def test_local_size_limits(self):
        self.path.write_bytes(b' ' * (validator.MAX_MANIFEST_BYTES + 1))
        self.assertEqual(validator.validate(self.path)['error']['code'], 'manifest_too_large')
        self.manifest['tracks'] *= 1001
        self.assert_invalid(self.manifest, 'invalid_tracks')

    def test_invalid_exit_and_usage(self):
        self.run_manifest({})
        run = subprocess.run([sys.executable, str(SCRIPT), str(self.path), '--json'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(json.loads(run.stdout)['status'], 'invalid_input')
        self.assertEqual(run.stderr, '')
        run = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(run.stdout, '')
        self.assertIn('Penggunaan', run.stderr)

    def test_result_envelope(self):
        for result in (self.run_manifest(), self.run_manifest({})):
            validator.validate_result(result)
            for field, value in (('remote_verified', True), ('command', 'upload'),
                                 ('profile', 'other'), ('schema_version', True),
                                 ('warnings', None), ('error', {})):
                with self.subTest(field=field, status=result['status']):
                    invalid = copy.deepcopy(result)
                    invalid[field] = value
                    with self.assertRaises(validator.InvalidInput):
                        validator.validate_result(invalid)

    def test_schema_files_and_documented_example(self):
        for name in ('manifest-v1', 'validate-result-v1'):
            schema = json.loads((ROOT / 'docs/schemas' / (name + '.schema.json')).read_text())
            self.assertEqual(schema['$schema'], 'https://json-schema.org/draft/2020-12/schema')
            self.assertFalse(schema['additionalProperties'])
        # jsonschema bukan dependency tes default; jika tersedia, cek independen.
        try:
            import jsonschema
        except ImportError:
            self.skipTest('Evaluator JSON Schema independen tidak terpasang; tes stdlib tetap berjalan.')
        for name in ('manifest-v1', 'validate-result-v1'):
            schema = json.loads((ROOT / 'docs/schemas' / (name + '.schema.json')).read_text())
            jsonschema.Draft202012Validator.check_schema(schema)
            evaluator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
            if name == 'manifest-v1':
                evaluator.validate(self.manifest)
                invalid = copy.deepcopy(self.manifest)
                invalid['tracks'][0]['ai_assisted'] = None
                self.assertFalse(evaluator.is_valid(invalid))
            else:
                evaluator.validate(self.run_manifest())
                evaluator.validate(self.run_manifest({}))


if __name__ == '__main__':
    unittest.main()
