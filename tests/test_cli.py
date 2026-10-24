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


if __name__ == '__main__':
    unittest.main()
