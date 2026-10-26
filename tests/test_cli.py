import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from toolost_uploader import __version__
from toolost_uploader.cli import main
from toolost_uploader.validation import validate


class CLITests(unittest.TestCase):
    def invoke(self, args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = main(args)
            except SystemExit as error:
                code = error.code
        return code, out.getvalue(), err.getvalue()

    def test_help_version(self):
        for args in (['--help'], ['validate', '--help'], ['--version']):
            code, out, err = self.invoke(args)
            self.assertEqual(code, 0)
            self.assertTrue(out)
            self.assertEqual(err, '')
        self.assertIn(__version__, self.invoke(['--version'])[1])

    def test_bad_args_do_not_echo_sensitive_values(self):
        secret = 'PRIVATE-SECRET-PATH'
        for args in ([], [secret], ['publish', secret], ['validate'],
                     ['validate', secret, '--cookie', secret], ['validate', secret, '--js']):
            with self.subTest(args=args):
                code, out, err = self.invoke(args)
                self.assertEqual(code, 2)
                self.assertEqual(out, '')
                self.assertNotIn(secret, err)
                self.assertNotIn('Traceback', err)

    def test_invalid_input_json(self):
        code, out, err = self.invoke(['validate', 'MISSING-PRIVATE-PATH', '--json'])
        self.assertEqual(code, 2)
        self.assertEqual(err, '')
        self.assertEqual(json.loads(out)['status'], 'invalid_input')
        self.assertNotIn('MISSING-PRIVATE-PATH', out)

    def test_human_output_and_warning_separation(self):
        result = validate('MISSING-PRIVATE-PATH')
        result.update(status='valid', release_id='synthetic', issues=[], error=None,
                      warnings=['Validasi offline saja.'])
        with patch('toolost_uploader.cli.validate', return_value=result):
            code, out, err = self.invoke(['validate', 'unused'])
        self.assertEqual(code, 0)
        self.assertEqual(out, 'Manifest valid (offline).\n')
        self.assertEqual(err, 'Validasi offline saja.\n')

    def test_stdout_failure_nonzero(self):
        with patch('toolost_uploader.cli.sys.stdout') as output:
            output.write.side_effect = OSError('closed output')
            self.assertEqual(main(['validate', 'missing', '--json']), 5)

    def test_upload_help(self):
        code, out, err = self.invoke(['upload', '--help'])
        self.assertEqual(code, 0)
        self.assertIn('--draft-only', out)
        self.assertIn('--profile', out)
        self.assertIn('--expected-account', out)
        self.assertEqual(err, '')

    def test_upload_without_draft_only_rejected(self):
        # Human output
        code, out, err = self.invoke(['upload', 'manifest.json', '--profile', 'test', '--expected-account', '123'])
        self.assertEqual(code, 2)
        self.assertIn('--draft-only', err)

        # JSON output
        code, out, err = self.invoke(['upload', 'manifest.json', '--profile', 'test', '--expected-account', '123', '--json'])
        self.assertEqual(code, 2)
        payload = json.loads(out)
        self.assertEqual(payload['status'], 'invalid_input')
        self.assertEqual(payload['error']['code'], 'draft_only_required')

    def test_upload_success_json_and_human(self):
        mock_result = {
            'status': 'draft_saved_subset',
            'run_id': 'run123',
            'draft_id': 'draft456',
            'warnings': ['Peringatan offline']
        }
        with patch('toolost_uploader.live_draft.execute', return_value=mock_result):
            # JSON
            code, out, err = self.invoke(['upload', 'manifest.json', '--draft-only', '--profile', 'test',
                                          '--expected-account', '123', '--json'])
            self.assertEqual(code, 0)
            payload = json.loads(out)
            self.assertEqual(payload['status'], 'draft_saved_subset')
            self.assertEqual(payload['draft_id'], 'draft456')

            # Human
            code, out, err = self.invoke(['upload', 'manifest.json', '--draft-only', '--profile', 'test',
                                          '--expected-account', '123'])
            self.assertEqual(code, 0)
            self.assertIn('draft_id=draft456', out)
            self.assertIn('Peringatan offline', err)

    def test_upload_invalid_input_and_draft_error(self):
        from toolost_uploader.validation import InvalidInput
        from toolost_uploader.live_draft import DraftError

        with patch('toolost_uploader.live_draft.execute', side_effect=InvalidInput('bad_code', 'detail')):
            code, out, err = self.invoke(['upload', 'manifest.json', '--draft-only', '--profile', 'test',
                                          '--expected-account', '123', '--json'])
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(out)['status'], 'invalid_input')

        with patch('toolost_uploader.live_draft.execute', side_effect=DraftError('account_mismatch')):
            code, out, err = self.invoke(['upload', 'manifest.json', '--draft-only', '--profile', 'test',
                                          '--expected-account', '123', '--json'])
            self.assertEqual(code, 4)
            payload = json.loads(out)
            self.assertEqual(payload['status'], 'reconciliation_required')
            self.assertEqual(payload['code'], 'account_mismatch')

    def test_upload_verbose_flag(self):
        code, out, err = self.invoke(['upload', '--help'])
        self.assertIn('--verbose', out)
        self.assertIn('-v', out)

        def fake_execute(*args, **kwargs):
            log = kwargs.get('log')
            if log:
                log('Langkah 1 dimulai')
                log('Langkah 2 selesai')
            return {'status': 'draft_saved_subset', 'draft_id': 'd123'}

        with patch('toolost_uploader.live_draft.execute', side_effect=fake_execute):
            code, out, err = self.invoke(['upload', 'manifest.json', '--draft-only', '--profile', 'test',
                                          '--expected-account', '123', '--verbose', '--json'])
            self.assertEqual(code, 0)
            self.assertIn('[toolost] Langkah 1 dimulai', err)
            self.assertIn('[toolost] Langkah 2 selesai', err)
            # Pastikan stdout tetap valid JSON murni
            payload = json.loads(out)
            self.assertEqual(payload['status'], 'draft_saved_subset')



if __name__ == '__main__':
    unittest.main()
