#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Autonomous Self-Healing Bridge between Hermes Agent and Antigravity (agy) CLI.
Enables Hermes on vpsg16gb to detect pipeline errors, package context, and dispatch
targeted non-interactive code repair and regression testing to Antigravity.
"""

import os
import sys
import argparse
import subprocess
import json
import time
from typing import Dict, Any, Optional, Tuple

QUIZ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if QUIZ_ROOT not in sys.path:
    sys.path.insert(0, QUIZ_ROOT)

AGY_BINARY = os.path.expanduser("~/.local/bin/agy")


class HermesAgyRepairBridge:
    """
    Autonomous healing bridge: isolates failures, invokes Antigravity CLI,
    and verifies that system tests achieve 100% GREEN status.
    """

    def __init__(self, workspace_dir: str = QUIZ_ROOT):
        self.workspace_dir = workspace_dir
        self.agy_bin = AGY_BINARY if os.path.isfile(AGY_BINARY) else "agy"

    def format_repair_prompt(
        self,
        error_context: str,
        failing_file: Optional[str] = None,
        task_goal: Optional[str] = None,
        row_id: Optional[int] = None,
        tab_name: Optional[str] = None
    ) -> str:
        prompt = [
            "🚨 [HERMES AUTONOMOUS SELF-HEALING DISPATCH]",
            "An error occurred during pipeline execution on vpsg16gb. Please diagnose, repair the root cause, and verify 100% green tests.",
            "",
            "=== ERROR CONTEXT & TRACEBACK ===",
            error_context.strip(),
            ""
        ]

        if failing_file:
            prompt.append(f"Failing File / Component: {failing_file}")
        if row_id is not None:
            prompt.append(f"Impacted Row ID: {row_id}")
        if tab_name:
            prompt.append(f"Impacted Google Sheets Tab: {tab_name}")
        if task_goal:
            prompt.append(f"Target Goal: {task_goal}")

        prompt.extend([
            "",
            "=== MANDATORY SYSTEM INVARIANTS ===",
            "1. ZERO-VPS BAN: Do NOT execute heavy Manim rendering on local VPS. Only GitHub Actions cloud runners render.",
            "2. SHEET INVARIANT: Sheet Row Number == Batch ID (#) across all tabs (pinyin, vocabCN, vocabVN).",
            "3. COLUMN K INVARIANT: Video URL must be direct playable file link: https://drive.google.com/file/d/{FILE_ID}/view?usp=drivesdk",
            "4. LINGUISTIC INVARIANTS: 100% Simplified Chinese, 100% concise Vietnamese (no English filler words), 1:1 Pinyin tone match.",
            "5. TEST SUITE PASS: You MUST run pytest tests/ and ensure all 236+ test cases pass without regressions.",
            "",
            "=== ACTION REQUIRED ===",
            "1. Inspect the codebase and locate the defect.",
            "2. Apply targeted, precise code modifications.",
            "3. Run pytest tests/ and debug in loop until 100% PASS.",
            "4. Provide a concise summary of the fix."
        ])

        return "\n".join(prompt)

    def run_pytest_verification(self, timeout_sec: int = 120) -> Tuple[bool, str]:
        try:
            res = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-q"],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=timeout_sec
            )
            passed = (res.returncode == 0)
            output = res.stdout if passed else (res.stdout + "\n" + res.stderr)
            return passed, output.strip()
        except subprocess.TimeoutExpired:
            return False, "Pytest verification timed out."
        except Exception as e:
            return False, f"Pytest verification error: {str(e)}"

    def dispatch_repair(
        self,
        error_context: str,
        failing_file: Optional[str] = None,
        task_goal: Optional[str] = None,
        row_id: Optional[int] = None,
        tab_name: Optional[str] = None,
        timeout_sec: int = 600
    ) -> Dict[str, Any]:
        prompt = self.format_repair_prompt(
            error_context=error_context,
            failing_file=failing_file,
            task_goal=task_goal,
            row_id=row_id,
            tab_name=tab_name
        )

        cmd = [
            self.agy_bin,
            "-p", prompt,
            "--dangerously-skip-permissions",
            "--effort", "high"
        ]

        print(f"\n [1;33m🤖 [HERMES SELF-HEAL] Giao nhiệm vụ sửa lỗi cho Antigravity CLI (agy)... [0m")
        start_time = time.time()
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=timeout_sec
            )
            elapsed = time.time() - start_time
            agy_exit_code = proc.returncode
            agy_output = proc.stdout

            print(f" [1;32m✓ AGY hoàn tất trong {elapsed:.1f}s (Exit Code: {agy_exit_code}) [0m")

            # Verify pytest suite after fix
            print(f" [1;33m🧪 Kiểm thử hồi quy toàn diện hệ thống (pytest)... [0m")
            test_passed, test_output = self.run_pytest_verification()

            success = (agy_exit_code == 0) and test_passed

            return {
                "success": success,
                "agy_exit_code": agy_exit_code,
                "pytest_passed": test_passed,
                "elapsed_seconds": round(elapsed, 2),
                "pytest_summary": test_output.splitlines()[-1] if test_output else "",
                "agy_output_snippet": agy_output[-500:] if agy_output else "",
                "error_details": proc.stderr if proc.stderr else None
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"AGY repair timed out after {timeout_sec}s",
                "pytest_passed": False
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to dispatch to AGY: {str(e)}",
                "pytest_passed": False
            }


def trigger_agy_self_heal(
    error_context: str,
    failing_file: Optional[str] = None,
    task_goal: Optional[str] = None,
    row_id: Optional[int] = None,
    tab_name: Optional[str] = None
) -> Dict[str, Any]:
    bridge = HermesAgyRepairBridge()
    return bridge.dispatch_repair(
        error_context=error_context,
        failing_file=failing_file,
        task_goal=task_goal,
        row_id=row_id,
        tab_name=tab_name
    )


def main():
    parser = argparse.ArgumentParser(description="Hermes to Antigravity CLI Self-Healing Bridge")
    parser.add_argument("--error", required=True, help="Error message, traceback, or failure description")
    parser.add_argument("--file", default=None, help="Path to the suspected failing file")
    parser.add_argument("--goal", default=None, help="Target repair goal")
    parser.add_argument("--row-id", type=int, default=None, help="Impacted row ID")
    parser.add_argument("--tab", default=None, help="Impacted tab name (pinyin, vocabCN, vocabVN)")
    parser.add_argument("--timeout", type=int, default=600, help="Max execution timeout in seconds")

    args = parser.parse_args()

    result = trigger_agy_self_heal(
        error_context=args.error,
        failing_file=args.file,
        task_goal=args.goal,
        row_id=args.row_id,
        tab_name=args.tab
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
