"""Executor smoke nyata draft-only. Login manual; tidak menyediakan Publish."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from toolost_uploader.live_draft import execute


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest')
    parser.add_argument('--profile', required=True)
    parser.add_argument('--expected-account', required=True, help='ID akun yang direview, bukan cookie/token.')
    parser.add_argument('--cdp', default='http://127.0.0.1:9437')
    parser.add_argument('--approve-draft', action='store_true')
    parser.add_argument('--accept-ui-date-for-smoke', action='store_true')
    args = parser.parse_args()
    try:
        result = execute(args.manifest, alias=args.profile, expected_account=args.expected_account,
                         endpoint=args.cdp, approve_draft=args.approve_draft,
                         accept_ui_date=args.accept_ui_date_for_smoke)
        code = 0
    except Exception:
        result = {'status': 'reconciliation_required', 'error': 'Operasi dihentikan; periksa checkpoint privat sebelum tindakan berikutnya. Jangan retry create/upload/Save.'}
        code = 4
    print(json.dumps(result))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
