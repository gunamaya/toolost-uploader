"""Antarmuka CLI offline untuk integrasi subprocess."""

import argparse
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
                    description="Validasi manifest offline; tidak membuka browser atau menjalankan upload/publish.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("validate", allow_abbrev=False, help="Periksa manifest dan hash file lokal.")
    command.add_argument("manifest", help="Path manifest JSON UTF-8.")
    command.add_argument("--json", action="store_true", help="Tulis satu objek JSON hasil ke stdout.")
    args = parser.parse_args(argv)
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
