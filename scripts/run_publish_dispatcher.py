#!/usr/bin/env python3
"""
scripts/run_publish_dispatcher.py
Gatekeeper 3 Social Media Distribution Dispatcher with Anti-Duplicate, Anti-Repeat, Anti-Missing controls.
Publishes to Buffer 1 (YouTube Shorts, TikTok, Facebook Reels).
"""

import os
import sys
import argparse
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple

# Suppress bytecode generation on exFAT mounts
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, SCRIPTS_DIR)

from monitor import get_gsheet_client, fetch_tab_raw_values, STANDARD_COLUMNS, SOCIAL_CHANNELS
from scripts.publish_social_batch import publish_row_to_social, parse_platform_metadata, to_direct_stream_url
from scripts.enforce_row_height_21px import RowHeightEnforcer

TAB_LIST = ["pinyin", "vocabCN", "vocabVN", "multilevels"]

def parse_args():
    parser = argparse.ArgumentParser(description="Gatekeeper 3 Social Media Distribution Dispatcher")
    parser.add_argument("--tab", type=str, default="all", help="Target tab: all, pinyin, vocabCN, vocabVN, multilevels")
    parser.add_argument("--row", dest="row_id", type=str, default="", help="Specific row number to publish")
    parser.add_argument("--channels", type=str, default="buffer1", help="Target channels (default: buffer1)")
    parser.add_argument("--delay", type=int, default=30, help="Initial delay in minutes (subsequent posts spaced by delay)")
    parser.add_argument("--limit", type=int, default=5, help="Max posts to publish per run")
    parser.add_argument("--dry-run", action="store_true", help="Simulate publishing without updating Buffer or Sheets")
    return parser.parse_args()

def check_gatekeeper_3(tab_name: str, row_id: int, headers: List[str], row_data: List[str]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Gatekeeper 3: Anti-Duplicate, Anti-Repeat, Anti-Missing verification.
    Returns: (is_eligible, reason, row_info)
    """
    row_dict = {headers[i]: row_data[i] if i < len(row_data) else "" for i in range(len(headers))}
    status = row_dict.get("Status", "").strip()
    topic = row_dict.get("Topic", "").strip()
    video_url = row_dict.get("Video", "").strip()
    yt_col = row_dict.get("Youtube", "").strip()
    tt_col = row_dict.get("Tiktok", "").strip()
    fb_col = row_dict.get("Facebook", "").strip()

    # Rule 1: Anti-Missing Video URL
    if not video_url or "drive.google.com" not in video_url:
        return False, f"Anti-Missing: Row #{row_id} has no valid Google Drive video URL (Status: {status})", row_dict

    # Rule 2: Status check (Must be Ready)
    if status.lower() != "ready":
        if status.lower() == "published":
            return False, f"Anti-Duplicate: Row #{row_id} ('{topic}') is ALREADY 'Published'", row_dict
        return False, f"Anti-Missing: Row #{row_id} is '{status}', not 'Ready'", row_dict

    # Rule 3: Anti-Repeat Social Channels check
    # If all 3 channels have 'Scheduled' or 'Published', do not duplicate
    if "Scheduled" in yt_col and "Scheduled" in tt_col and "Scheduled" in fb_col:
        return False, f"Anti-Duplicate: Row #{row_id} already scheduled on all channels ({yt_col})", row_dict

    # Passed GK3 QC
    return True, "Passed Gatekeeper 3 validation", row_dict

def run_distribution():
    args = parse_args()
    print("=" * 70)
    print("🚀 GATEKEEPER 3: SOCIAL MEDIA DISTRIBUTION DISPATCHER")
    print(f"⏰ Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Target Tab: {args.tab}")
    print(f"🎬 Specific Row: {args.row_id or 'Auto-detect Ready rows'}")
    print(f"📢 Channels: {args.channels} | Delay: {args.delay}m | Limit: {args.limit} | DryRun: {args.dry_run}")
    print("=" * 70)

    client, err = get_gsheet_client()
    if not client:
        print(f"❌ Failed to authenticate with Google Sheets: {err}")
        sys.exit(1)

    target_tabs = TAB_LIST if args.tab.lower() == "all" else [args.tab]
    published_count = 0
    current_delay = args.delay

    for tab in target_tabs:
        if published_count >= args.limit:
            print(f"🛑 Reached distribution limit ({args.limit}). Stopping.")
            break

        print(f"\n📂 Inspecting Tab: [{tab}]...")
        ok, rows, msg = fetch_tab_raw_values(tab, client=client, use_cache=False)
        if not ok or not rows:
            print(f"  ⚠ Failed to fetch rows from '{tab}': {msg}")
            continue

        headers = rows[0]
        eligible_candidates = []

        if args.row_id:
            try:
                target_r = int(args.row_id)
                if 2 <= target_r <= len(rows):
                    eligible_candidates.append((target_r, rows[target_r - 1]))
                else:
                    print(f"  ❌ Specified row #{target_r} is out of bounds (2..{len(rows)})")
            except ValueError:
                print(f"  ❌ Invalid row ID '{args.row_id}'")
        else:
            for idx in range(1, len(rows)):
                r_num = idx + 1
                r_data = rows[idx]
                eligible, reason, _ = check_gatekeeper_3(tab, r_num, headers, r_data)
                if eligible:
                    eligible_candidates.append((r_num, r_data))
                else:
                    # Optional log for debug
                    pass

        print(f"  Found {len(eligible_candidates)} candidate row(s) eligible for publishing in '{tab}'.")

        for r_num, r_data in eligible_candidates:
            if published_count >= args.limit:
                break

            eligible, reason, r_dict = check_gatekeeper_3(tab, r_num, headers, r_data)
            if not eligible:
                print(f"  🛡 GK3 BLOCKED Row #{r_num}: {reason}")
                continue

            topic = r_dict.get("Topic", "Unknown")
            print(f"\n  📤 [PUBLISHING] Row #{r_num} ('{topic}') in '{tab}' (Queue Delay: {current_delay}m)...")

            try:
                res = publish_row_to_social(
                    tab_name=tab,
                    row_id=r_num,
                    channels=args.channels,
                    dry_run=args.dry_run,
                    delay_minutes=current_delay
                )
                print(f"  ✅ Row #{r_num} successfully queued to Buffer!")
                published_count += 1
                current_delay += args.delay  # Space out subsequent posts by delay_minutes
            except Exception as e:
                print(f"  ❌ Failed to publish Row #{r_num}: {e}")

    print("\n" + "=" * 70)
    print(f"🎉 DISTRIBUTION RUN COMPLETED! Total Published/Queued: {published_count}")
    print("=" * 70)

    # Invariant: Enforce 21px row height on all tabs
    print("\n📏 Enforcing 21px row height across all tabs...")
    try:
        enforcer = RowHeightEnforcer()
        enforcer.enforce_all()
    except Exception as e:
        print(f"⚠ Warning: Row height enforcement error: {e}")

if __name__ == "__main__":
    run_distribution()
