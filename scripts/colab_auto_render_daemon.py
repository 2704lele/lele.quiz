#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Colab Auto-Render Daemon for LeLe Chinese Automation.
Periodically scans Google Sheets tabs (pinyin, vocabCN, vocabVN, multilevels)
for rows with Status == "Pending", and dispatches them to Google Colab Cloud VMs
using continuous batch generation on a single mounted session.
"""

import os
import sys
import time
import argparse
import logging
from pathlib import Path

QUIZ_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(QUIZ_ROOT))

from colab.colab_orchestrator import ColabQuizOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [AutoRenderDaemon] %(message)s"
)
logger = logging.getLogger("AutoRenderDaemon")


def main():
    parser = argparse.ArgumentParser(description="Colab Auto-Render Daemon for Quiz System")
    parser.add_argument("--once", action="store_true", help="Run a single scan cycle and exit")
    parser.add_argument("--interval", type=int, default=300, help="Polling interval in seconds (default: 300)")
    parser.add_argument("--quality", default="qh", choices=["ql", "qm", "qh", "qk"], help="Render quality (default: qh)")
    parser.add_argument("--cpu", action="store_true", help="Force High-Speed CPU VM instead of GPU T4")
    args = parser.parse_args()

    orch = ColabQuizOrchestrator()
    logger.info("=== LeLe Quiz Colab Auto-Render Daemon Initialized ===")
    logger.info(f"Mode: {'Forced CPU' if args.cpu else 'GPU T4 (Automatic CPU Fallback)'} | Quality: {args.quality}")

    if args.once:
        logger.info("Running single scan cycle...")
        success = orch.run_all_pending(quality=args.quality, force_gpu=not args.cpu)
        logger.info(f"Single scan finished. Status: {'SUCCESS' if success else 'IDLE / PARTIAL'}")
        return

    logger.info(f"Running continuously in daemon mode. Polling interval: {args.interval}s...")
    while True:
        try:
            pending_map = orch.find_pending_rows_across_tabs()
            total_pending = sum(len(v) for v in pending_map.values())
            if total_pending > 0:
                logger.info(f"👉 Found {total_pending} pending batch(es): {pending_map}. Triggering Colab Continuous Runner...")
                orch.run_all_pending(quality=args.quality, force_gpu=not args.cpu)
            else:
                logger.info("✓ 0 pending rows found across all tabs. System is clean.")
        except KeyboardInterrupt:
            logger.info("Daemon interrupted by user. Stopping...")
            break
        except Exception as e:
            logger.error(f"Unexpected error in daemon cycle: {e}")

        logger.info(f"Sleeping for {args.interval}s until next scan cycle...")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
