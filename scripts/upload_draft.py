"""Executor smoke nyata draft-only. Login manual; tidak menyediakan Publish."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from toolost_uploader.live_draft import execute
from toolost_uploader.live_draft import DraftError
from toolost_uploader.cli import Parser


def main():
    parser = Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument('manifest')
    parser.add_argument('--profile', required=True)
    parser.add_argument('--expected-account', required=True, help='ID akun yang direview, bukan cookie/token.')
    parser.add_argument('--cdp', default='http://127.0.0.1:9437')
    parser.add_argument('--approve-draft', action='store_true')
    parser.add_argument('--accept-ui-date-for-smoke', action='store_true')
    parser.add_argument('--resume-stopped-before-artwork', action='store_true',
                        help='Dinonaktifkan: recovery debugging lama, bukan resume produksi.')
    parser.add_argument('--resume-stopped-before-audio', action='store_true',
                        help='Dinonaktifkan: tidak boleh mengulang upload.')
    parser.add_argument('--resume-selected-audio', action='store_true',
                        help='Dinonaktifkan: tidak boleh mengirim file yang sudah dipilih.')
    parser.add_argument('--resume-open-metadata', action='store_true',
                        help='Dinonaktifkan: tidak boleh mengulang metadata/Save.')
    parser.add_argument('--approve-release-title-equals-track', action='store_true',
                        help='Persetujuan amendment immutable sebelum create, bukan edit draft existing.')
    parser.add_argument('--reconcile-readback-only', action='store_true',
                        help='Reopen/readback setelah attempt Save; wajib mulai portal, tanpa create/upload/Save.')
    args = parser.parse_args()
    try:
        result = execute(args.manifest, alias=args.profile, expected_account=args.expected_account,
                         endpoint=args.cdp, approve_draft=args.approve_draft,
                         accept_ui_date=args.accept_ui_date_for_smoke,
                         resume_before_artwork=args.resume_stopped_before_artwork,
                         resume_before_audio=args.resume_stopped_before_audio,
                         resume_selected_audio=args.resume_selected_audio,
                         resume_open_metadata=args.resume_open_metadata,
                         approve_release_title_amendment=args.approve_release_title_equals_track,
                         reconcile_only=args.reconcile_readback_only)
        code = 0
    except Exception as error:
        result = {'status': 'reconciliation_required', 'code': str(error) if isinstance(error, DraftError) else type(error).__name__, 'error': 'Operasi dihentikan; periksa checkpoint privat sebelum tindakan berikutnya. Jangan retry create/upload/Save.'}
        code = 4
    print(json.dumps(result))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
