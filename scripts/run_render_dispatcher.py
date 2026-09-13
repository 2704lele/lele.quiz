#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Central Dispatcher for Quiz Video Rendering across all 4 tabs:
- In GitHub Actions: Executes Manim 1080x1920 60fps rendering, Edge-TTS, GDrive upload, and QC
- On VPS: Dispatches GitHub Actions workflow ('02_quiz_video_rendering_and_qc.yml')
- Populates Column K (Streamable URL) and Column D ('Ready')
- Strictly enforces 21px row height invariant
"""

import os
import sys
import subprocess
import argparse

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

QUIZ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if QUIZ_ROOT not in sys.path:
    sys.path.insert(0, QUIZ_ROOT)

from scripts.enforce_row_height_21px import RowHeightEnforcer

PIPELINE_MAP = {
    "pinyin": "pinyinquiz",
    "pinyinquiz": "pinyinquiz",
    "vocabcn": "vocabCNquiz",
    "vocabCN": "vocabCNquiz",
    "vocabcnquiz": "vocabCNquiz",
    "vocabCNquiz": "vocabCNquiz",
    "vocabvn": "vocabVNquiz",
    "vocabVN": "vocabVNquiz",
    "vocabvnquiz": "vocabVNquiz",
    "vocabVNquiz": "vocabVNquiz",
    "multilevels": "multilevelsquiz",
    "multilevelsquiz": "multilevelsquiz",
    "all": "all",
}


def dispatch_via_gha(tab: str, row: str, quality: str) -> bool:
    """Dispatches rendering job to GitHub Actions workflow."""
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        try:
            res = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=QUIZ_ROOT, capture_output=True, text=True, check=True
            )
            url = res.stdout.strip()
            if "://" in url and "@" in url:
                token = url.split("://")[1].split("@")[0].split(":")[-1]
        except Exception:
            pass

    env = os.environ.copy()
    if token:
        env["GH_TOKEN"] = token

    cmd = ["gh", "workflow", "run", "02_quiz_video_rendering_and_qc.yml"]
    if tab != "all":
        cmd.extend(["-f", f"tab={tab}"])
    else:
        cmd.extend(["-f", "tab=all"])

    if row:
        cmd.extend(["-f", "mode=specific_row", "-f", f"row_id={row}"])
    else:
        cmd.extend(["-f", "mode=all_pending"])

    cmd.extend(["-f", f"quality={quality}"])

    print(f"🚀 Dispatching GitHub Actions Workflow: {' '.join(cmd)}")
    try:
        res = subprocess.run(cmd, cwd=QUIZ_ROOT, env=env, capture_output=True, text=True)
        if res.returncode == 0:
            print("✓ GitHub Actions workflow '02 - Quiz Video Rendering & Auto-QC' successfully dispatched!")
            return True
        else:
            print(f"❌ Failed to dispatch GHA workflow: {res.stderr or res.stdout}")
            return False
    except Exception as e:
        print(f"❌ Error invoking gh CLI: {e}")
        return False


def execute_rendering_in_gha(tab: str, row: str, quality: str, dry_run: bool = False) -> bool:
    """Executes rendering batch and QC locally inside GitHub Actions runner."""
    tab_lower = tab.strip().lower()
    if tab_lower == "all":
        targets = ["pinyinquiz", "vocabCNquiz", "vocabVNquiz", "multilevelsquiz"]
    else:
        target_name = PIPELINE_MAP.get(tab, PIPELINE_MAP.get(tab_lower, tab))
        targets = [target_name]

    overall_success = True
    clean_row = str(row).replace("#", "").strip() if row else ""

    for p in targets:
        pipe_dir = os.path.join(QUIZ_ROOT, p)
        batch_script = os.path.join(pipe_dir, "scripts", "run_batch.py")
        qc_script = os.path.join(pipe_dir, "scripts", "run_qc.py")

        if not os.path.exists(batch_script):
            print(f"⚠ Batch script not found for pipeline {p}: {batch_script}")
            continue

        # Case 1: pinyinquiz
        if p == "pinyinquiz":
            cmd = [sys.executable, batch_script, "--from-sheet", "--quality", quality, "--upload-gdrive"]
            if clean_row:
                cmd.extend(["--row-id", clean_row])

            if dry_run:
                print(f"[DRY-RUN] [{p}] Would run batch render: {' '.join(cmd)}")
            else:
                print(f"\n🎬 Running batch render for pipeline '{p}'...")
                res = subprocess.run(cmd, cwd=pipe_dir)
                if res.returncode != 0:
                    overall_success = False
                    print(f"❌ Render batch failed for {p}")

            if os.path.exists(qc_script):
                qc_cmd = [sys.executable, qc_script]
                if clean_row:
                    qc_cmd.extend(["--row-id", clean_row])
                if dry_run:
                    print(f"[DRY-RUN] [{p}] Would run Auto-QC: {' '.join(qc_cmd)}")
                else:
                    print(f"🔍 Running Auto-QC for pipeline '{p}'...")
                    qc_res = subprocess.run(qc_cmd, cwd=pipe_dir)
                    if qc_res.returncode != 0:
                        overall_success = False
                        print(f"❌ QC failed for {p}")

        # Case 2: vocabCNquiz or vocabVNquiz
        elif p in ["vocabCNquiz", "vocabVNquiz"]:
            cmd = [sys.executable, batch_script, "--quality", quality]
            if clean_row:
                cmd.extend(["--row_id", clean_row])

            if dry_run:
                print(f"[DRY-RUN] [{p}] Would run batch render: {' '.join(cmd)}")
            else:
                print(f"\n🎬 Running batch render for pipeline '{p}'...")
                res = subprocess.run(cmd, cwd=pipe_dir)
                if res.returncode != 0:
                    overall_success = False
                    print(f"❌ Render batch failed for {p}")

            if os.path.exists(qc_script):
                qc_cmd = [sys.executable, qc_script]
                if clean_row:
                    qc_cmd.extend(["--row-id", clean_row])
                if dry_run:
                    print(f"[DRY-RUN] [{p}] Would run Auto-QC: {' '.join(qc_cmd)}")
                else:
                    print(f"🔍 Running Auto-QC for pipeline '{p}'...")
                    qc_res = subprocess.run(qc_cmd, cwd=pipe_dir)
                    if qc_res.returncode != 0:
                        overall_success = False
                        print(f"❌ QC failed for {p}")

        # Case 3: multilevelsquiz
        elif p == "multilevelsquiz":
            if clean_row:
                target_ids = [clean_row]
            else:
                target_ids = []
                try:
                    from multilevelsquiz.src.gsheet_manager import GSheetManager as MLGSheetManager
                    mgr = MLGSheetManager()
                    pending = mgr.get_pending_batches()
                    target_ids = [
                        str(b.get("_row_number", b.get("row_index", b.get("#", "")))).replace("#", "").strip()
                        for b in pending
                    ]
                    target_ids = [t for t in target_ids if t]
                    print(f"Pending scan for multilevelsquiz found {len(target_ids)} batch(es): {target_ids}")
                except Exception as e:
                    print(f"Warning: could not auto-fetch pending multilevels batches: {e}")
                    target_ids = []

            if not target_ids:
                print(f"ℹ No target rows to process for multilevelsquiz.")
            else:
                for tid in target_ids:
                    cmd = [sys.executable, batch_script, "--id", tid, "--quality", quality, "--force"]
                    if dry_run:
                        print(f"[DRY-RUN] [multilevelsquiz] Would run batch render for row #{tid}: {' '.join(cmd)}")
                    else:
                        print(f"\n🎬 Running batch render for multilevelsquiz row #{tid}...")
                        res = subprocess.run(cmd, cwd=pipe_dir)
                        if res.returncode != 0:
                            overall_success = False
                            print(f"❌ Render batch failed for multilevelsquiz row #{tid}")
                            continue

                    if os.path.exists(qc_script):
                        qc_cmd = [sys.executable, qc_script, "--id", tid]
                        if dry_run:
                            print(f"[DRY-RUN] [multilevelsquiz] Would run Auto-QC for row #{tid}: {' '.join(qc_cmd)}")
                        else:
                            print(f"🔍 Running Auto-QC for multilevelsquiz row #{tid}...")
                            qc_res = subprocess.run(qc_cmd, cwd=pipe_dir)
                            if qc_res.returncode != 0:
                                overall_success = False
                                print(f"❌ QC failed for multilevelsquiz row #{tid}")

    return overall_success


def main():
    parser = argparse.ArgumentParser(description="Quiz Render Dispatcher")
    parser.add_argument("--tab", "-t", default="all", choices=[
        "all", "pinyin", "vocabCN", "vocabVN", "multilevels",
        "pinyinquiz", "vocabCNquiz", "vocabVNquiz", "multilevelsquiz",
        "vocabcn", "vocabvn"
    ])
    parser.add_argument("--row", "-r", default="", help="Specific Row ID or empty for all pending")
    parser.add_argument("--quality", "-q", default="qh", choices=["ql", "qm", "qh", "qk"])
    parser.add_argument("--local", action="store_true", help="Execute rendering locally instead of dispatching to GitHub Actions")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without running renders")
    args = parser.parse_args()

    print(f"🎬 === Starting Quiz Video Render Dispatcher (Tab: {args.tab}, Row: {args.row or 'ALL_PENDING'}, Quality: {args.quality}) ===")

    in_gha = os.getenv("GITHUB_ACTIONS") == "true" or args.local or args.dry_run

    if not in_gha:
        success = dispatch_via_gha(tab=args.tab, row=args.row, quality=args.quality)
    else:
        success = execute_rendering_in_gha(tab=args.tab, row=args.row, quality=args.quality, dry_run=args.dry_run)

    if not args.dry_run:
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
