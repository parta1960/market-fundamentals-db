"""Entrypoint shim (v0.2).

The Bootstrap workflow runs `PYTHONPATH=etl python etl/pilot_backfill.py`.
Since v0.2 this file delegates to full_backfill.py, which reads
etl/run_config.json to decide mode (full universe vs pilot), chunking,
and time budget. The v0.1 pilot logic lives on in git history (tag v0.1.0).
"""

import sys

import full_backfill

if __name__ == "__main__":
    sys.exit(full_backfill.main())
