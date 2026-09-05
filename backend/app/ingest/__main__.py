"""Run ``python -m app.ingest``."""

from __future__ import annotations

import sys

from . import main

raise SystemExit(main(sys.argv[1:]))
