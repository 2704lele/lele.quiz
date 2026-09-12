#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI tool on VPS to dispatch quiz Manim rendering and Auto-QC to Google Colab CLI.
Replaces legacy GitHub Actions triggers with 100% cloud Colab execution.
Supports batch continuity across all tabs, automatic CPU fallback, and 30-min cooldown.
"""

import os
import sys
import argparse
from pathlib import Path

QUIZ_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(QUIZ_ROOT))

from colab.colab_orchestrator import ColabQuizOrchestrator


def main():
    parser = argparse.ArgumentParser(description="LeLe Quiz Colab CLI Dispatcher")
    parser.add_argument(
        "--pipeline", "-p",
        default="all",
        choices=["all", "pinyin", "vocabcn", "vocabvn", "multilevels", "ml"],
        help="Target pipeline (default: 'all' to process all pending rows across all 4 tabs)"
    )
    parser.add_argument("--row", "-r", default="", help="Specific Row ID to render (leave blank for all pending)")
    parser.add_argument("--quality", "-q", default="qh", choices=["ql", "qm", "qh", "qk"], help="Render quality (default: qh for 1080x1920 60fps)")
    parser.add_argument("--action", "-a", default="all", choices=["render", "qc", "all"], help="Execution action")
    parser.add_argument("--cpu", action="store_true", help="Force High-Speed CPU VM instead of GPU T4")
    parser.add_argument("--status", action="store_true", help="Display Colab Account Pool status")
    parser.add_argument("--pending", action="store_true", help="Scan and list pending rows across all tabs")
    parser.add_argument("--stop", action="store_true", help="Stop currently active Colab session")

    args = parser.parse_args()
    orch = ColabQuizOrchestrator()

    if args.status:
        print("\n=======================================================")
        print("  GOOGLE COLAB QUIZ RUNNER — POOL STATUS (30M COOLDOWN)")
        print("=======================================================")
        for a in orch.get_pool_status():
            rem = a.get("cooldown_remaining_sec", 0)
            if rem > 0:
                mins = rem // 60
                secs = rem % 60
                cd_str = f" | Cooldown: {mins}m {secs}s remaining"
            else:
                cd_str = " | Cooldown: READY"
            print(f"  * [{a['status']:<12}] Alias: {a['alias']:<10} Email: {a['email']:<26} Success: {a['success_count']:<3}{cd_str}")
        print("=======================================================\n")
        return

    if args.pending:
        pending = orch.find_pending_rows_across_tabs()
        total = sum(len(v) for v in pending.values())
        print("\n=======================================================")
        print(f"  PENDING ROWS REPORT (Total: {total})")
        print("=======================================================")
        for tab, rows in pending.items():
            print(f"  • Tab '{tab:<12}': {len(rows)} pending -> {rows}")
        print("=======================================================\n")
        return

    if args.stop:
        orch.stop_session()
        print("✓ Stopped Colab session.")
        return

    # Batch Continuity Mode: If pipeline == "all" and no specific row
    if args.pipeline.lower() == "all" and not args.row:
        print(f"\n🚀 [Colab Continuous Dispatch] Processing ALL pending rows across 4 tabs...")
        print(f"   Quality: {args.quality} | Mode: {'CPU (Forced)' if args.cpu else 'GPU T4 (Auto CPU Fallback)'}")
        success = orch.run_all_pending(quality=args.quality, force_gpu=not args.cpu)
        if success:
            print("\n🎉 [Colab Continuous Dispatch] SUCCESS! All pending rows across all tabs completed.")
            sys.exit(0)
        else:
            print("\n❌ [Colab Continuous Dispatch] Finished with errors or remaining rows.")
            sys.exit(1)

    target_pl = "multilevelsquiz" if args.pipeline in ["multilevels", "ml"] else args.pipeline
    row_label = f"Row #{args.row}" if args.row else "ALL PENDING"

    print(f"\n🚀 [Colab Dispatch] Pipeline: {target_pl.upper()} | {row_label} | Quality: {args.quality} | Mode: {'CPU (Forced)' if args.cpu else 'GPU T4 (Auto CPU Fallback)'}...")
    success = orch.dispatch_quiz_job(
        pipeline=target_pl,
        row_id=args.row,
        quality=args.quality,
        action=args.action,
        force_gpu=not args.cpu
    )

    if success:
        print(f"\n🎉 [Colab Dispatch] SUCCESS! {target_pl.upper()} {row_label} completed successfully.")
        sys.exit(0)
    else:
        print(f"\n❌ [Colab Dispatch] FAILED for {target_pl.upper()} {row_label}.")
        sys.exit(1)


if __name__ == "__main__":
    main()
