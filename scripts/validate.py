"""Wrapper source-checkout untuk command validate yang sama dengan package."""

from pathlib import Path
import sys

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from toolost_uploader.cli import main

    raise SystemExit(main(["validate", *sys.argv[1:]]))
