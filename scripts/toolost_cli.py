"""Standalone CLI entry point for frozen toolost executable."""
from __future__ import annotations

from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from toolost_uploader.cli import main

if __name__ == "__main__":
    sys.exit(main())
