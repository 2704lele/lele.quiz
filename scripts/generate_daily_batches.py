#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Root Daily Batch Generator for LeLe Chinese Quiz Automation System.
Dispatches batch generation and Gatekeeper 1 ideation across all 3 sub-pipelines:
- pinyin (pinyinquiz): Hanzi ➔ Guess Pinyin (tab: 'pinyin')
- vocabCN (vocabCNquiz): Hanzi ➔ Guess Vietnamese Meaning (tab: 'vocabCN')
- vocabVN (vocabVNquiz): Vietnamese Meaning ➔ Guess Hanzi (tab: 'vocabVN')
"""

import os
import sys
import argparse
import logging
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("RootBatchGenerator")

PIPELINE_SCRIPT_MAP = {
    "pinyin": os.path.join(PROJECT_ROOT, "pinyinquiz", "scripts", "generate_daily_batches.py"),
    "vocabcn": os.path.join(PROJECT_ROOT, "vocabCNquiz", "scripts", "generate_daily_batches.py"),
    "vocabvn": os.path.join(PROJECT_ROOT, "vocabVNquiz", "scripts", "generate_daily_batches.py"),
    "multilevels": os.path.join(PROJECT_ROOT, "multilevelsquiz", "scripts", "generate_daily_batches.py")
}


def run_subpipeline(pipeline_name: str, passthrough_args: list) -> int:
    """Execute the appropriate sub-pipeline generator script."""
    key = pipeline_name.lower().strip()
    if key not in PIPELINE_SCRIPT_MAP:
        logger.error(f"Unknown pipeline: '{pipeline_name}'. Valid options: {list(PIPELINE_SCRIPT_MAP.keys())}")
        return 1

    target_script = PIPELINE_SCRIPT_MAP[key]
    if not os.path.exists(target_script):
        logger.error(f"Target script not found: {target_script}")
        return 1

    cmd = [sys.executable, target_script] + passthrough_args
    logger.info(f"=== [Root Dispatcher] Running pipeline '{pipeline_name}' via: {' '.join(cmd[:3])} ... ===")

    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.dirname(target_script)))
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Unified Root Daily Batch Generator for LeLe Chinese Quiz Automation System",
        add_help=False
    )
    parser.add_argument(
        "--pipeline",
        type=str,
        default=os.getenv("TARGET_PIPELINE", "all"),
        help="Target quiz sub-pipeline: 'pinyin', 'vocabCN', 'vocabVN', 'multilevels', or 'all' (default: all)"
    )

    known_args, remaining_args = parser.parse_known_args()

    pipeline_target = (known_args.pipeline or "all").lower().strip()

    if pipeline_target == "all":
        exit_codes = []
        for pl in ["pinyin", "vocabcn", "vocabvn", "multilevels"]:
            logger.info(f"\n{'=' * 60}\n🚀 Launching Generator for pipeline: {pl.upper()}\n{'=' * 60}")
            code = run_subpipeline(pl, remaining_args)
            exit_codes.append(code)

        sys.exit(max(exit_codes) if exit_codes else 0)
    else:
        code = run_subpipeline(pipeline_target, remaining_args)
        sys.exit(code)


if __name__ == "__main__":
    main()
