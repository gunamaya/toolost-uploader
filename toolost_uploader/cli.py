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
    root_epilog = """Alur Kerja Utama:
  1. Validasi manifest rilis:
     toolost validate manifest.json --json
  2. Setup sesi browser login manual:
     toolost setup --profile <alias>
  3. Diagnosa kesiapan lingkungan (Chrome, port CDP, akun login):
     toolost check --profile <alias> --expected-account <id> --auto-bootup --json
  4. Unggah dan simpan draft rilis (draft-only):
     toolost upload manifest.json --draft-only --profile <alias> --expected-account <id> \\
       --approve-draft --accept-ui-date --verbose --json
"""
    parser = Parser(prog="toolost", allow_abbrev=False,
                    formatter_class=argparse.RawDescriptionHelpFormatter,
                    description="CLI Toolost Uploader untuk validasi manifest dan penyimpanan draft release.",
                    epilog=root_epilog)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    validate_epilog = """Contoh:
  toolost validate manifest.json
  toolost validate manifest.json --json
"""
    validate_cmd = commands.add_parser("validate", allow_abbrev=False,
                                       formatter_class=argparse.RawDescriptionHelpFormatter,
                                       help="Periksa manifest dan hash file lokal.",
                                       epilog=validate_epilog)
    validate_cmd.add_argument("manifest", help="Path manifest JSON UTF-8.")
    validate_cmd.add_argument("--json", action="store_true", help="Tulis satu objek JSON hasil ke stdout.")

    upload_epilog = """Contoh:
  toolost upload album.json --draft-only --profile my-profile --expected-account 422512 \\
    --approve-draft --accept-ui-date --verbose --json

Catatan Keamanan:
  Operasi upload DIBATASI HANYA sampai tahap penyimpanan draft (Save Changes).
  Perintah ini TIDAK PERNAH menekan tombol Publish atau memicu distribusi rilis.
"""
    upload_cmd = commands.add_parser("upload", allow_abbrev=False,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     help="Unggah draft release ke Too Lost (draft-only).",
                                     epilog=upload_epilog)
    upload_cmd.add_argument("manifest", help="Path manifest JSON UTF-8.")
    upload_cmd.add_argument("--draft-only", action="store_true",
                            help="Wajib: batasi operasi hanya simpan draft; tidak memicu publish.")
    upload_cmd.add_argument("--profile", required=True, help="Alias profil penyimpanan lokal.")
    upload_cmd.add_argument("--expected-account", required=True, help="ID akun numerik yang direview.")
    upload_cmd.add_argument("--cdp", default="http://127.0.0.1:9437", help="Endpoint CDP browser loopback.")
    upload_cmd.add_argument("--auto-bootup", action=argparse.BooleanOptionalAction, default=True,
                            help="Otomatis jalankan Chrome CDP bila belum aktif (default: True).")
    upload_cmd.add_argument("--chrome", help="Path khusus ke Google Chrome executable.")
    upload_cmd.add_argument("--approve-draft", action="store_true", help="Persetujuan pembuatan draft baru.")
    upload_cmd.add_argument("--accept-ui-date", "--accept-ui-date-for-smoke", dest="accept_ui_date",
                            action="store_true", help="Persetujuan mewarisi tanggal UI default.")
    upload_cmd.add_argument("--approve-release-title-equals-track", action="store_true",
                            help="Persetujuan amendment judul rilis jika terkunci di UI.")
    upload_cmd.add_argument("--reconcile-readback-only", action="store_true",
                            help="Reopen dan readback draft yang sudah attempt Save.")
    upload_cmd.add_argument("--append", action="store_true",
                            help="Unggah lagu susulan ke draft release album yang sudah ada di Too Lost.")
    upload_cmd.add_argument("--update", action="store_true",
                            help="Sinkronkan pembaruan judul, tanggal, artwork, metadata track, atau lagu susulan ke draft existing.")
    upload_cmd.add_argument("-v", "--verbose", action="store_true",
                            help="Tampilkan progres verbose secara real-time ke stderr.")
    upload_cmd.add_argument("--json", action="store_true", help="Tulis satu objek JSON hasil ke stdout.")

    setup_epilog = """Contoh:
  toolost setup --profile my-profile
  toolost setup --profile my-profile --url https://toolost.com/login
"""
    setup_cmd = commands.add_parser("setup", allow_abbrev=False,
                                    formatter_class=argparse.RawDescriptionHelpFormatter,
                                    help="Buka browser Chrome lokal untuk login manual Too Lost.",
                                    epilog=setup_epilog)
    setup_cmd.add_argument("--profile", default="default", help="Alias profil browser lokal (default: 'default').")
    setup_cmd.add_argument("--chrome", help="Path khusus ke Google Chrome executable.")
    setup_cmd.add_argument("--url", help="URL target pembuka (default: https://toolost.com/login).")
    setup_cmd.add_argument("-v", "--verbose", action="store_true", help="Tampilkan progres verbose ke stderr.")

    check_epilog = """Contoh:
  toolost check --profile my-profile --expected-account 422512
  toolost check --profile my-profile --expected-account 422512 --auto-bootup --json
"""
    check_cmd = commands.add_parser("check", allow_abbrev=False,
                                    formatter_class=argparse.RawDescriptionHelpFormatter,
                                    help="Periksa kesiapan lingkungan (Chrome, profil, CDP, dan akun login).",
                                    epilog=check_epilog)
    check_cmd.add_argument("--profile", default="default", help="Alias profil browser lokal (default: 'default').")
    check_cmd.add_argument("--expected-account", help="ID akun numerik yang diharapkan.")
    check_cmd.add_argument("--cdp", default="http://127.0.0.1:9437", help="Endpoint CDP browser loopback.")
    check_cmd.add_argument("--auto-bootup", action="store_true", help="Nyalakan Chrome CDP otomatis bila port belum aktif.")
    check_cmd.add_argument("--chrome", help="Path khusus ke Google Chrome executable.")
    check_cmd.add_argument("-v", "--verbose", action="store_true", help="Tampilkan progres verbose ke stderr.")
    check_cmd.add_argument("--json", action="store_true", help="Tulis satu objek JSON hasil ke stdout.")

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
        from .browser import is_cdp_available, ensure_cdp_ready, resolve_profile_dir

        def log_verbose(msg):
            now = datetime.now().strftime("%H:%M:%S")
            sys.stderr.write(f"[{now}] [toolost] {msg}\n")
            sys.stderr.flush()

        progress_log = log_verbose if args.verbose else None

        if getattr(args, "auto_bootup", True) and not is_cdp_available(args.cdp):
            pdir = resolve_profile_dir(args.profile)
            if progress_log:
                progress_log(f"CDP loopback {args.cdp} belum aktif; melakukan auto-bootup Chrome...")
            ready = ensure_cdp_ready(args.cdp, profile_dir=pdir, log=progress_log, chrome_path=args.chrome)
            if not ready and progress_log:
                progress_log(f"Peringatan: auto-bootup Chrome pada {args.cdp} belum merespons tepat waktu.")

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
                allow_append=args.append,
                allow_update=getattr(args, "update", False),
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
                    status = result.get("status")
                    if status == "draft_up_to_date":
                        print(f"Draft sudah up-to-date (tidak ada perubahan): draft_id={result.get('draft_id')}")
                    elif status == "draft_appended_subset":
                        print(f"Draft berhasil diperbarui (append): draft_id={result.get('draft_id')}")
                    elif status == "draft_updated_subset":
                        print(f"Draft berhasil diperbarui: draft_id={result.get('draft_id')}")
                    else:
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

    if args.command == "setup":
        from .browser import find_chrome_binary, resolve_profile_dir, launch_chrome
        chrome_bin = find_chrome_binary(args.chrome)
        if not chrome_bin:
            sys.stderr.write("Error: Google Chrome executable tidak ditemukan di sistem.\n")
            return 2
        pdir = resolve_profile_dir(args.profile)
        msg = (
            f"Membuka Google Chrome untuk login manual Too Lost pada profil '{pdir.name}'...\n"
            "Silakan selesaikan proses login (dan 2FA bila ada). Setelah masuk ke portal, TUTUP jendela browser ini.\n"
        )
        sys.stderr.write(msg)
        sys.stderr.flush()
        try:
            proc = launch_chrome(pdir, mode="setup", chrome_path=chrome_bin, url=args.url)
            proc.wait()
            sys.stderr.write("Browser ditutup. Profil lokal siap digunakan.\n")
            sys.stderr.flush()
            return 0
        except Exception as e:
            sys.stderr.write(f"Gagal menjalankan browser: {e}\n")
            return 5

    if args.command == "check":
        from .browser import (
            find_chrome_binary, resolve_profile_dir, check_and_clean_stale_lock,
            is_cdp_available, ensure_cdp_ready, check_auth_identity
        )

        def log_verbose(msg):
            now = datetime.now().strftime("%H:%M:%S")
            sys.stderr.write(f"[{now}] [toolost] {msg}\n")
            sys.stderr.flush()

        progress_log = log_verbose if args.verbose else None

        if progress_log:
            progress_log("Memeriksa kesiapan lingkungan uploader...")

        chrome_bin = find_chrome_binary(args.chrome)
        pdir = resolve_profile_dir(args.profile)
        is_locked, lock_msg = check_and_clean_stale_lock(pdir)

        cdp_active = is_cdp_available(args.cdp)
        if not cdp_active and args.auto_bootup:
            if progress_log:
                progress_log(f"CDP loopback {args.cdp} belum aktif; mencoba auto-bootup Chrome...")
            cdp_active = ensure_cdp_ready(args.cdp, profile_dir=pdir, log=progress_log, chrome_path=chrome_bin)

        auth_info = None
        if cdp_active:
            if progress_log:
                progress_log(f"CDP aktif; memeriksa status autentikasi di {args.cdp}...")
            auth_info = check_auth_identity(args.cdp)

        checks = {
            "chrome": {
                "status": "ok" if chrome_bin else "missing",
                "path": str(chrome_bin) if chrome_bin else None
            },
            "profile": {
                "status": "ok" if (not is_locked or cdp_active) else "locked",
                "path": str(pdir),
                "message": "Profil aktif digunakan oleh browser CDP." if cdp_active else lock_msg
            },
            "cdp": {
                "status": "ok" if cdp_active else "offline",
                "endpoint": args.cdp
            },
            "auth": auth_info or {"status": "skipped", "message": "CDP offline"}
        }

        if not chrome_bin:
            overall_status = "chrome_missing"
            overall_error = "Google Chrome executable tidak ditemukan di sistem."
            code = 2
        elif is_locked and not cdp_active:
            overall_status = "profile_locked"
            overall_error = f"Profil browser sedang terkunci: {lock_msg}"
            code = 2
        elif not cdp_active:
            overall_status = "cdp_offline"
            overall_error = f"Browser CDP di {args.cdp} tidak aktif. Gunakan --auto-bootup atau jalankan browser terlebih dahulu."
            code = 2
        elif auth_info and auth_info.get("status") == "unauthorized":
            overall_status = "login_required"
            overall_error = "Sesi autentikasi Too Lost kedaluwarsa atau belum login. Jalankan 'toolost setup' untuk login."
            code = 2
        elif auth_info and auth_info.get("status") != "authenticated":
            overall_status = "auth_error"
            overall_error = f"Gagal membaca status autentikasi: {auth_info.get('message', auth_info.get('status'))}"
            code = 2
        elif args.expected_account and auth_info and auth_info.get("account_id") != args.expected_account:
            overall_status = "account_mismatch"
            overall_error = f"Akun aktif ({auth_info.get('account_id')}) tidak cocok dengan expected account ({args.expected_account})."
            code = 2
        else:
            overall_status = "ready"
            overall_error = None
            code = 0

        res = {
            "status": overall_status,
            "account_id": auth_info.get("account_id") if auth_info and auth_info.get("status") == "authenticated" else None,
            "cdp_endpoint": args.cdp if cdp_active else None,
            "error": overall_error,
            "checks": checks
        }

        try:
            if args.json:
                print(json.dumps(res, ensure_ascii=True, allow_nan=False))
            else:
                if code == 0:
                    print(f"Lingkungan SIAP: Akun #{res['account_id']} terverifikasi pada {args.cdp}.")
                else:
                    print(f"Lingkungan BELUM SIAP: [{overall_status.upper()}] {overall_error}", file=sys.stderr)
            sys.stdout.flush()
        except OSError:
            return 5
        return code


if __name__ == "__main__":
    sys.exit(main())
