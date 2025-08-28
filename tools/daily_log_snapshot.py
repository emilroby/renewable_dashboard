# daily_log_snapshot.py
# -------------------------------------------------------------------
# Creates a timestamped copy of your Streamlit activity log so you can:
#  - run it manually any time (--now)
#  - schedule it daily at 10:00 via Windows Task Scheduler
#
# Assumes your main log file is written to:
#   C:\Users\rosei\PycharmProjects\renewable_dashboard\logs\app_activity.log
#
# Snapshots are saved under:
#   C:\Users\rosei\PycharmProjects\renewable_dashboard\logs\daily_logs\log_YYYY-MM-DD_HHMMSS.txt
# -------------------------------------------------------------------

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys

# Project paths (resolve from this file’s location)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = PROJECT_ROOT / "logs"
MAIN_LOG_FILE = LOGS_DIR / "app_activity.log"
SNAPSHOT_DIR = LOGS_DIR / "daily_logs"


def ensure_dirs() -> None:
    """Ensure the logs and snapshot directories exist."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def snapshot_log(run_dt: datetime | None = None) -> Path:
    """
    Copy the current main log to a timestamped text file and return its path.
    If the source log doesn't exist, create an empty snapshot with a note.
    """
    ensure_dirs()
    run_dt = run_dt or datetime.now()
    stamp = run_dt.strftime("%Y-%m-%d_%H%M%S")
    snapshot_path = SNAPSHOT_DIR / f"log_{stamp}.txt"

    if MAIN_LOG_FILE.exists():
        # Copy as text file (preserve content only)
        # Using shutil.copyfile ensures correct handling across platforms.
        shutil.copyfile(MAIN_LOG_FILE, snapshot_path)
    else:
        # Create an empty snapshot with a note so your automation still has a file
        with snapshot_path.open("w", encoding="utf-8") as f:
            f.write(
                "No log found to snapshot.\n"
                f"Expected at: {MAIN_LOG_FILE}\n"
                f"Created at: {run_dt.isoformat(timespec='seconds')}\n"
            )

    return snapshot_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create a timestamped snapshot of the app activity log."
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="Create a snapshot immediately (use for manual runs).",
    )
    args = parser.parse_args(argv)

    if not args.now:
        print(
            "Nothing to do. Use '--now' to create a snapshot immediately.\n\n"
            "Examples:\n"
            "  python tools\\daily_log_snapshot.py --now\n\n"
            "Schedule this command daily at 10:00 with Windows Task Scheduler."
        )
        return 0

    try:
        snap = snapshot_log()
        print(f"[OK] Log snapshot written to: {snap}")
        return 0
    except Exception as e:
        print(f"[ERROR] Failed to create snapshot: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
