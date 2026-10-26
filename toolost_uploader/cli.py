"""Antarmuka CLI untuk integrasi subprocess."""

import argparse
from datetime import datetime
import json
import sys

from . import __version__
from .validation import validate, validate_result


class Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse biasanya mengulang nilai argumen; jangan bocorkan path/secret input.
        self.print_usage(sys.stderr)
        self.exit(2, "Argumen tidak valid; lihat toolost --help.\n")


def main(argv=None):
    parser = Parser(prog="toolost", allow_abbrev=False,
                    description="CLI Toolost Uploader untuk validasi manifest dan penyimpanan draft release.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    validate_cmd = commands.add_parser("validate", allow_abbrev=False, help="Periksa manifest dan hash file lokal.")
    validate_cmd.add_argument("manifest", help="Path manifest JSON UTF-8.")
    validate_cmd.add_argument("--json", action="store_true", help="Tulis satu objek JSON hasil ke stdout.")

    upload_cmd = commands.add_parser("upload", allow_abbrev=False,
                                     help="Unggah draft release ke Too Lost (draft-only).")
    upload_cmd.add_argument("manifest", help="Path manifest JSON UTF-8.")
    upload_cmd.add_argument("--draft-only", action="store_true",
                            help="Wajib: batasi operasi hanya simpan draft; tidak memicu publish.")
    upload_cmd.add_argument("--profile", required=True, help="Alias profil penyimpanan lokal.")
    upload_cmd.add_argument("--expected-account", required=True, help="ID akun numerik yang direview.")
    upload_cmd.add_argument("--cdp", default="http://127.0.0.1:9437", help="Endpoint CDP browser loopback.")
    upload_cmd.add_argument("--approve-draft", action="store_true", help="Persetujuan pembuatan draft baru.")
    upload_cmd.add_argument("--accept-ui-date", "--accept-ui-date-for-smoke", dest="accept_ui_date",
                            action="store_true", help="Persetujuan mewarisi tanggal UI default.")
    upload_cmd.add_argument("--approve-release-title-equals-track", action="store_true",
                            help="Persetujuan amendment judul rilis jika terkunci di UI.")
    upload_cmd.add_argument("--reconcile-readback-only", action="store_true",
                            help="Reopen dan readback draft yang sudah attempt Save.")
    upload_cmd.add_argument("-v", "--verbose", action="store_true",
                            help="Tampilkan progres verbose secara real-time ke stderr.")
    upload_cmd.add_argument("--json", action="store_true", help="Tulis satu objek JSON hasil ke stdout.")

    args = parser.parse_args(argv)

    if args.command == "validate":
        result = validate(args.manifest)
        validate_result(result)
        try:
            if args.json:
                print(json.dumps(result, ensure_ascii=True, allow_nan=False))
            else:
                print("Manifest valid (offline)." if result["status"] == "valid" else "Manifest tidak valid.")
                for warning in result["warnings"]:
                    print(warning, file=sys.stderr)
                if result["error"]:
                    print(result["error"]["message"], file=sys.stderr)
            sys.stdout.flush()
        except OSError:
            return 5
        return 0 if result["status"] == "valid" else 2

    if args.command == "upload":
        if not args.draft_only:
            err_msg = "Operasi upload tanpa --draft-only tidak didukung; publish/distribusi dilarang keras."
            try:
                if args.json:
                    res = {"status": "invalid_input",
                           "error": {"code": "draft_only_required", "message": err_msg}}
                    print(json.dumps(res, ensure_ascii=True, allow_nan=False))
                else:
                    print(err_msg, file=sys.stderr)
                sys.stdout.flush()
            except OSError:
                return 5
            return 2

        from .live_draft import execute, DraftError
        from .validation import InvalidInput

        def log_verbose(msg):
            now = datetime.now().strftime("%H:%M:%S")
            sys.stderr.write(f"[{now}] [toolost] {msg}\n")
            sys.stderr.flush()

        progress_log = log_verbose if args.verbose else None

        try:
            result = execute(
                args.manifest,
                alias=args.profile,
                expected_account=args.expected_account,
                endpoint=args.cdp,
                approve_draft=args.approve_draft,
                accept_ui_date=args.accept_ui_date,
                approve_release_title_amendment=args.approve_release_title_equals_track,
                reconcile_only=args.reconcile_readback_only,
                log=progress_log,
            )
            code = 0
        except InvalidInput as error:
            if progress_log:
                progress_log(f"Input tidak valid: {type(error).__name__} ({error})")
            result = {
                "status": "invalid_input",
                "error": {"code": type(error).__name__, "message": str(error)}
            }
            code = 2
        except Exception as error:
            if progress_log:
                progress_log(f"Operasi dihentikan: {type(error).__name__} ({error})")
            result = {
                "status": "reconciliation_required",
                "code": str(error) if isinstance(error, DraftError) else type(error).__name__,
                "error": "Operasi dihentikan; periksa checkpoint privat sebelum tindakan berikutnya. Jangan retry create/upload/Save."
            }
            code = 4

        try:
            if args.json:
                print(json.dumps(result, ensure_ascii=True, allow_nan=False))
            else:
                if code == 0:
                    print(f"Draft berhasil disimpan: draft_id={result.get('draft_id')}")
                    for warning in result.get("warnings", []):
                        print(warning, file=sys.stderr)
                elif code == 2:
                    print("Input manifest atau argumen tidak valid.", file=sys.stderr)
                    if "error" in result and "message" in result["error"]:
                        print(result["error"]["message"], file=sys.stderr)
                else:
                    print(result.get("error", "Terjadi kesalahan operasi draft."), file=sys.stderr)
            sys.stdout.flush()
        except OSError:
            return 5
        return code
