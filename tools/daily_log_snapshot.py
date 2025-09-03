#!/usr/bin/env python3
# tools/daily_log_snapshot.py
# Read renewable_dashboard/logs/app_activity.log and produce a time-filtered snapshot.
# This script MUST NOT import streamlit or app.py.

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict
from pathlib import Path

# Project root assumed as parent of this file's folder
THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
LOG_DIR = ROOT_DIR / "logs"
LOG_PATH = LOG_DIR / "app_activity.log"
SNAP_DIR = LOG_DIR / "snapshots"

# Log format expected from app.py bootstrap:
#   "%(asctime)s [%(levelname)s] %(message)s"
# where %(message)s is a JSON payload we wrote via log_event(...).
#
# Example line:
# 2025-08-28 14:05:12,345 [INFO] {"ts":"2025-08-28T14:05:12.342918","visitor_id":"...","event":"click","widget":"button","label":"Home"}

def parse_line(line: str):
    """
    Returns (payload_dict, raw_json_str) or (None, None) if unparsable.
    """
    try:
        # Find the first JSON object start
        jpos = line.find("{")
        if jpos == -1:
            return None, None
        raw = line[jpos:].strip()
        payload = json.loads(raw)
        return payload, raw
    except Exception:
        return None, None

def to_dt(val):
    """Parse ISO time in payload['ts']; fallback to None."""
    if not val:
        return None
    try:
        # payload uses datetime.now().isoformat()
        # Some Python versions include microseconds, some not.
        return datetime.fromisoformat(val)
    except Exception:
        return None

def load_events(min_dt: datetime | None, min_level: str):
    """
    Load events from LOG_PATH, filter by timestamp >= min_dt (if given).
    min_level is one of INFO, WARNING, ERROR (used only if the JSON has "level", otherwise ignored).
    Returns list of payload dicts.
    """
    if not LOG_PATH.exists():
        raise FileNotFoundError(f"Log file not found: {LOG_PATH}")

    want_level = {"INFO": 1, "WARNING": 2, "ERROR": 3}.get(min_level.upper(), 1)
    events = []
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            payload, raw = parse_line(line)
            if not payload:
                continue
            ts = to_dt(payload.get("ts"))
            if min_dt and ts and ts < min_dt:
                continue

            # Optional level handling if your payload includes "level"
            # (our bootstrap doesn't add it inside JSON; it's in the prefix).
            plevel = payload.get("level", "INFO")
            plevel_rank = {"INFO": 1, "WARNING": 2, "ERROR": 3}.get(str(plevel).upper(), 1)
            if plevel_rank < want_level:
                continue

            events.append(payload)
    return events

def summarize(events):
    """
    Build summary strings and return (summary_text, csv_text).
    """
    total = len(events)
    by_event = Counter(e.get("event", "unknown") for e in events)
    by_visitor = Counter(e.get("visitor_id", "unknown") for e in events)

    # Widget details
    clicks = [e for e in events if e.get("event") == "click"]
    changes = [e for e in events if e.get("event") == "change"]
    downloads = [e for e in events if e.get("event") == "download"]

    by_widget_click = Counter((e.get("widget"), e.get("label")) for e in clicks)
    by_widget_change = Counter((e.get("widget"), e.get("label")) for e in changes)
    by_download_label = Counter(e.get("label") for e in downloads)

    lines = []
    lines.append("===== Under-Construction Dashboard — Log Snapshot =====")
    lines.append(f"Generated at: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"Log file:     {LOG_PATH}")
    lines.append("")
    lines.append(f"Total events: {total}")
    lines.append("Events by type:")
    for k, v in by_event.most_common():
        lines.append(f"  - {k}: {v}")
    lines.append("")
    lines.append(f"Unique visitors (session ids): {len(by_visitor)}")
    lines.append("Top visitors (by event count):")
    for vid, cnt in by_visitor.most_common(10):
        lines.append(f"  - {vid}: {cnt}")
    lines.append("")
    lines.append("Top button clicks:")
    for (widget, label), cnt in by_widget_click.most_common(10):
        lines.append(f"  - {label} [{widget}]: {cnt}")
    lines.append("")
    lines.append("Top input/filter changes:")
    for (widget, label), cnt in by_widget_change.most_common(10):
        lines.append(f"  - {label} [{widget}]: {cnt}")
    lines.append("")
    lines.append("Top downloads:")
    for label, cnt in by_download_label.most_common(10):
        lines.append(f"  - {label}: {cnt}")

    # Simple CSV export of raw events (flatten a few keys)
    csv_lines = ["ts,visitor_id,event,widget,label,file,projects,owners,states"]
    for e in events:
        row = [
            e.get("ts", ""),
            e.get("visitor_id", ""),
            e.get("event", ""),
            str(e.get("widget", "")),
            str(e.get("label", "")),
            str(e.get("file", "")),
            # Filters come as JSON strings in our bootstrap
            str(e.get("project_types", "")),
            str(e.get("owners", "")),
            str(e.get("states", "")),
        ]
        # Escape commas
        row = [str(x).replace(",", " ") for x in row]
        csv_lines.append(",".join(row))

    return "\n".join(lines), "\n".join(csv_lines)

def compute_cutoff(args):
    if args.hours is not None:
        return datetime.now() - timedelta(hours=args.hours)
    if args.since is not None:
        try:
            return datetime.fromisoformat(args.since)
        except Exception:
            raise SystemExit("--since must be ISO format, e.g. 2025-08-28T09:00:00")
    return None  # --all

def main():
    parser = argparse.ArgumentParser(description="Create a filtered snapshot from app_activity.log")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--hours", type=int, help="Include events from the last N hours")
    group.add_argument("--since", type=str, help="Include events since ISO time (e.g. 2025-08-28T09:00:00)")
    group.add_argument("--all", action="store_true", help="Include all events")
    parser.add_argument("--out", type=str, default="", help="Optional output folder for snapshot files (default logs/snapshots)")
    parser.add_argument("--min-level", type=str, default="INFO", choices=["INFO","WARNING","ERROR"], help="Minimum level to include (if present in JSON)")
    args = parser.parse_args()

    cutoff = compute_cutoff(args)
    out_dir = Path(args.out) if args.out else SNAP_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        events = load_events(cutoff, args.min_level)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return

    summary_text, csv_text = summarize(events)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    txt_path = out_dir / f"snapshot-{stamp}.txt"
    csv_path = out_dir / f"snapshot-{stamp}.csv"

    txt_path.write_text(summary_text, encoding="utf-8")
    csv_path.write_text(csv_text, encoding="utf-8")

    print(summary_text)
    print("")
    print(f"[OK] Wrote snapshot files:\n  - {txt_path}\n  - {csv_path}")

if __name__ == "__main__":
    main()
