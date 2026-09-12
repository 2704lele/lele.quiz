#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Central Dispatcher for Quiz Video Rendering across all 4 tabs:
- Executes Manim vertical 1080x1920 60fps rendering
- Synthesizes Edge-TTS audio
- Uploads directly to Google Drive folder for each tab
- Runs Gatekeeper 2 physical QC
- Populates Column K (Streamable URL) and Column D ('Ready')
- Strictly enforces 21px row height invariant
"""

import os
import sys
import argparse

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

QUIZ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if QUIZ_ROOT not in sys.path:
    sys.path.insert(0, QUIZ_ROOT)

from scripts.enforce_row_height_21px import RowHeightEnforcer


def main():
    parser = argparse.ArgumentParser(description="Quiz Render Dispatcher")
    parser.add_argument("--tab", "-t", default="all", choices=["all", "pinyin", "vocabCN", "vocabVN", "multilevels"])
    parser.add_argument("--row", "-r", default="", help="Specific Row ID or empty for all pending")
    parser.add_argument("--quality", "-q", default="qh", choices=["ql", "qm", "qh", "qk"])
    args = parser.parse_args()

    print(f"🎬 === Starting Quiz Video Render Dispatcher (Tab: {args.tab}, Row: {args.row or 'ALL_PENDING'}, Quality: {args.quality}) ===")

    # Check if running in GitHub Actions or locally on VPS
    in_gha = os.getenv("GITHUB_ACTIONS") == "true"

    if not in_gha:
        # On VPS: Delegate to Colab Cloud VM Orchestrator (Zero VPS Compute)
        from colab.colab_orchestrator import ColabQuizOrchestrator
        orch = ColabQuizOrchestrator()
        if args.tab == "all" and not args.row:
            success = orch.run_all_pending(quality=args.quality)
        else:
            success = orch.dispatch_quiz_job(pipeline=args.tab, row_id=args.row, quality=args.quality)
    else:
        # In GitHub Actions: Execute directly on GHA Cloud Runner
        worker_script = os.path.join(QUIZ_ROOT, "colab", "colab_worker_quiz.py")
        if os.path.exists(worker_script):
            cmd = f"python3 {worker_script} --pipeline {args.tab} --quality {args.quality}"
            if args.row:
                cmd += f" --row-id {args.row}"
            rc = os.system(cmd)
            success = (rc == 0)
        else:
            print("❌ Cloud worker script not found.")
            success = False

    print("\n📏 Enforcing strict 21px row height invariant across all tabs...")
    try:
        enforcer = RowHeightEnforcer()
        enforcer.enforce_all()
        print("✓ 21px Row Height Invariant successfully enforced.")
    except Exception as e:
        print(f"⚠ Warning: Could not run row height enforcer: {e}")

    if success:
        print("🎉 Render Dispatcher Finished Successfully!")
        sys.exit(0)
    else:
        print("❌ Render Dispatcher encountered issues.")
        sys.exit(1)


if __name__ == "__main__":
    main()
