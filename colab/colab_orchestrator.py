#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Master Colab Quiz Orchestrator for LeLe Chinese Automation.
Dispatches Manim video rendering and Auto-QC tasks to Google Colab Cloud VMs using google-colab-cli,
with automatic multi-account Gmail rotation, warm session reuse, 3-retry connection policy,
automatic CPU fallback, strict 30-minute cooldown (1800s), and continuous batch processing.

STRICT POLICY:
The account "aleron.dt@gmail.com" is PERMANENTLY FORBIDDEN and BLACKLISTED.
"""

import os
import sys
import json
import time
import tempfile
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

CURRENT_DIR = Path(__file__).resolve().parent
QUIZ_ROOT = CURRENT_DIR.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
if str(QUIZ_ROOT) not in sys.path:
    sys.path.insert(0, str(QUIZ_ROOT))

from colab_rotator import ColabAccountManager, BLACKLISTED_EMAILS, DEFAULT_COOLDOWN_SECONDS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ColabQuizOrchestrator")

DEFAULT_SA_PATH = Path.home() / ".cloud-profiles/lelehoctiengtrung/google_sa/service_account.json"
DEFAULT_OAUTH_PATH = Path.home() / ".cloud-profiles/lelehoctiengtrung/google_oauth/user_oauth2.json"
WORKER_SCRIPT = CURRENT_DIR / "colab_worker_quiz.py"

DEFAULT_TELEGRAM_ENV_PATH = Path.home() / ".cloud-profiles/lelehoctiengtrung/telegram/telegram.env"
DEFAULT_TELEGRAM_CHAT_ID = "-1004392602002"


def resolve_telegram_creds() -> Tuple[str, str]:
    """Dynamically resolves Telegram credentials from environment or ~/.cloud-profiles vault.

    Never hardcodes secret fallback strings. If token is not set, returns empty string and logs warning.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip() or DEFAULT_TELEGRAM_CHAT_ID

    if not token and DEFAULT_TELEGRAM_ENV_PATH.exists():
        try:
            with open(DEFAULT_TELEGRAM_ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("TELEGRAM_BOT_TOKEN="):
                        token = line.split("=", 1)[1].strip().strip('"').strip("'")
                    elif line.startswith("TELEGRAM_CHAT_ID=") and not os.getenv("TELEGRAM_CHAT_ID"):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            chat_id = val
        except Exception as e:
            logger.warning(f"Failed to read Telegram credentials from vault '{DEFAULT_TELEGRAM_ENV_PATH}': {e}")

    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not found in environment or vault (~/.cloud-profiles/lelehoctiengtrung/telegram/telegram.env)")

    return token, chat_id

# Safety timeout protection against permanent VM hangs: 80 minutes (4800s)
DEFAULT_EXECUTION_TIMEOUT_SECONDS = 4800
DEFAULT_SUBPROCESS_TIMEOUT_SECONDS = 4900

QUIZ_TABS = ["pinyin", "vocabCN", "vocabVN", "multilevels"]



class ColabQuizOrchestrator:
    """Manages remote job dispatch to Google Colab VMs with multi-account rotation."""

    def __init__(self, manager: Optional[ColabAccountManager] = None):
        self.mgr = manager or ColabAccountManager()
        self.active_session_name = None
        self.active_alias = None

    def get_pool_status(self) -> List[Dict[str, Any]]:
        """Returns current status of all registered Colab accounts."""
        return self.mgr.list_accounts()

    def enforce_row_height(self) -> None:
        """Invokes the 21px row height invariant enforcer."""
        try:
            from scripts.enforce_row_height_21px import audit_and_enforce_row_height
            logger.info("Enforcing strict 21px row height invariant across all tabs...")
            audit_and_enforce_row_height()
        except Exception as e:
            logger.warning(f"Could not run row height enforcer: {e}")

    def prepare_bundle(self, pipeline: str) -> Path:
        """
        Packages the quiz codebase from VPS into a tarball to upload directly to Colab VM.
        Eliminates dependency on GitHub or git credentials.
        """
        bundle_path = Path("/tmp/quiz_bundle.tar.gz")
        target_raw = pipeline.lower()
        logger.info(f"📦 Preparing codebase tarball bundle for pipeline '{pipeline}'...")

        if target_raw in ["multilevels", "ml", "multilevelsquiz"]:
            cmd = [
                "tar",
                "--exclude=multilevelsquiz/output",
                "--exclude=__pycache__",
                "--exclude=*.pyc",
                "-czf", str(bundle_path),
                "-C", str(QUIZ_ROOT),
                "multilevelsquiz"
            ]
        elif target_raw in ["vocabcn", "vocabcnquiz"]:
            cmd = [
                "tar",
                "--exclude=vocabCNquiz/output",
                "--exclude=__pycache__",
                "--exclude=*.pyc",
                "-czf", str(bundle_path),
                "-C", str(QUIZ_ROOT),
                "vocabCNquiz"
            ]
        elif target_raw in ["vocabvn", "vocabvnquiz"]:
            cmd = [
                "tar",
                "--exclude=vocabVNquiz/output",
                "--exclude=__pycache__",
                "--exclude=*.pyc",
                "-czf", str(bundle_path),
                "-C", str(QUIZ_ROOT),
                "vocabVNquiz"
            ]
        elif target_raw in ["pinyin", "pinyinquiz"]:
            cmd = [
                "tar",
                "--exclude=pinyinquiz/output",
                "--exclude=__pycache__",
                "--exclude=*.pyc",
                "-czf", str(bundle_path),
                "-C", str(QUIZ_ROOT),
                "pinyinquiz"
            ]
        else:
            cmd = [
                "tar",
                "--exclude=*/output",
                "--exclude=.venv",
                "--exclude=.git",
                "--exclude=.pytest_cache",
                "--exclude=artifacts",
                "--exclude=__pycache__",
                "--exclude=*.pyc",
                "--exclude=.agents",
                "--exclude=vocabCNquiz/assets/fonts/Noto*",
                "--exclude=vocabVNquiz/assets/fonts/Noto*",
                "--exclude=pinyinquiz/assets/fonts/NotoSansSC-Bold.otf",
                "-czf", str(bundle_path),
                "-C", str(QUIZ_ROOT),
                "."
            ]

        subprocess.run(cmd, check=True)
        size_mb = bundle_path.stat().st_size / (1024 * 1024)
        logger.info(f"✓ Codebase bundle ready: {bundle_path} ({size_mb:.2f} MB)")
        return bundle_path

    def find_pending_rows_across_tabs(self) -> Dict[str, List[int]]:
        """Scans all 4 quiz tabs to find row numbers with Status == 'Pending'."""
        pending_map: Dict[str, List[int]] = {}
        try:
            from monitor import fetch_tab_raw_values
        except ImportError:
            logger.warning("Could not import fetch_tab_raw_values from monitor.")
            return {tab: [] for tab in QUIZ_TABS}

        for tab in QUIZ_TABS:
            pending_rows = []
            try:
                res = fetch_tab_raw_values(tab)
                if isinstance(res, tuple) and len(res) >= 2:
                    ok, rows = res[0], res[1]
                else:
                    ok, rows = True, res

                if ok and rows and len(rows) > 1:
                    for idx, r in enumerate(rows[1:], start=2):
                        if isinstance(r, list) and len(r) > 3:
                            status = str(r[3]).strip().lower()
                            if status == "pending":
                                pending_rows.append(idx)
            except Exception as e:
                logger.warning(f"Error checking pending rows in tab '{tab}': {e}")
            pending_map[tab] = pending_rows
        return pending_map

    def ensure_active_session(
        self,
        account_alias: str,
        force_gpu: bool = True,
        max_retries: int = 3
    ) -> str:
        """
        Provisions or reuses an active Colab session for the specified account.
        Enforces maximum 3 retries and automatic fallback to CPU if GPU is unavailable or fails.
        """
        # 1. Check existing active sessions
        code, stdout, stderr = self.mgr.run_colab_command(account_alias, ["sessions"], timeout=30)
        if code == 0 and stdout:
            for line in stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and not line.startswith("[colab] No active"):
                    sess_name = parts[0]
                    if not sess_name.startswith("[") and not sess_name.startswith("NAME"):
                        logger.info(f"[{account_alias}] Reusing existing warm Colab session: {sess_name}")
                        self.active_session_name = sess_name
                        self.active_alias = account_alias
                        return sess_name

        # 2. Provision new session with 3 retries and CPU fallback
        last_err = ""
        for attempt in range(1, max_retries + 1):
            session_name = f"quiz_worker_{int(time.time()) % 10000}"
            logger.info(f"[{account_alias}] Connection attempt {attempt}/{max_retries}: Provisioning session '{session_name}'...")

            # Step 2a: Try GPU if requested
            if force_gpu:
                logger.info(f"[{account_alias}] Requesting GPU T4 accelerator...")
                code, stdout, stderr = self.mgr.run_colab_command(
                    account_alias,
                    ["new", "-s", session_name, "--gpu", "T4"],
                    timeout=90
                )
                if code == 0:
                    logger.info(f"[{account_alias}] ✓ Colab VM provisioned with GPU T4: {session_name}")
                    self.active_session_name = session_name
                    self.active_alias = account_alias
                    return session_name

                last_err = stderr or stdout
                logger.warning(f"[{account_alias}] GPU T4 request failed (code {code}): {last_err[-300:]}")
                logger.info(f"[{account_alias}] ⚡ Immediate Fallback: Attempting High-Speed CPU VM...")

            # Step 2b: Fallback to CPU VM
            # Use distinct session name with quiz_worker_ prefix to avoid collisions
            cpu_session_name = f"{session_name}_cpu" if force_gpu else session_name
            code, stdout, stderr = self.mgr.run_colab_command(
                account_alias,
                ["new", "-s", cpu_session_name],
                timeout=90
            )
            if code == 0:
                logger.info(f"[{account_alias}] ✓ Colab High-Speed CPU VM provisioned: {cpu_session_name} (CPU Fallback Active)")
                self.active_session_name = cpu_session_name
                self.active_alias = account_alias
                return cpu_session_name

            last_err = stderr or stdout
            logger.warning(f"[{account_alias}] CPU VM provisioning attempt {attempt}/{max_retries} failed: {last_err[-300:]}")
            if attempt < max_retries:
                logger.info(f"[{account_alias}] Backing off 5 seconds before retry {attempt + 1}...")
                time.sleep(5)

        # If all 3 attempts failed: mark cooldown 30m and raise error
        self.mgr.mark_cooldown(
            account_alias,
            duration_seconds=DEFAULT_COOLDOWN_SECONDS,
            reason=f"Failed {max_retries} connection attempts: {last_err[-200:]}"
        )
        raise RuntimeError(f"Colab provisioning failed on [{account_alias}] after {max_retries} retries: {last_err[-200:]}")

    def run_all_pending(
        self,
        quality: str = "qh",
        force_gpu: bool = True,
        max_rotations: int = 5
    ) -> bool:
        """
        Batch Continuity Engine:
        Once an account mounts successfully, keeps generating ALL rows with status needing generation (Pending)
        across all 4 tabs until 0 pending rows remain.
        Enforces 3-retry connection, CPU fallback, and 30-minute cooldown per email.
        """
        logger.info("=== Batch Continuity Engine: Scanning for Pending Rows Across All Tabs ===")
        pending_map = self.find_pending_rows_across_tabs()
        total_pending = sum(len(v) for v in pending_map.values())

        if total_pending == 0:
            logger.info("✓ 0 pending rows found across all 4 quiz tabs. Nothing to process.")
            return True

        logger.info(f"Found {total_pending} pending batch(es) to process: {pending_map}")

        rotation_round = 0
        while rotation_round < max_rotations:
            active_alias = self.mgr.select_active_account()
            if not active_alias:
                earliest, wait_sec = self.mgr.get_earliest_available_account()
                logger.error(f"❌ No active accounts available in Colab pool! Earliest [{earliest}] ready in {wait_sec}s.")
                return False

            rotation_round += 1
            logger.info(f"=== [Rotation Round {rotation_round}/{max_rotations}] Active Account: [{active_alias}] ===")

            try:
                # 3-retry connection + CPU fallback
                session_name = self.ensure_active_session(active_alias, force_gpu=force_gpu, max_retries=3)
            except RuntimeError as re:
                logger.warning(f"Skipping [{active_alias}] due to connection failure: {re}. Rotating to next account...")
                continue

            # Session is mounted! Now use it to render ALL pending rows
            try:
                logger.info(f"[{active_alias}] 🚀 Mounted Colab VM: '{session_name}'. Beginning continuous batch processing...")

                # Prepare Job Specification JSON for ALL pipelines
                tg_token, tg_chat_id = resolve_telegram_creds()
                job_spec = {
                    "pipeline": "all",
                    "row_id": "",
                    "quality": quality,
                    "action": "all",
                    "telegram_token": tg_token,
                    "telegram_chat_id": tg_chat_id,
                    "timestamp": time.time()
                }

                with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
                    json.dump(job_spec, tmp, indent=2)
                    tmp_spec_path = tmp.name

                # Upload files to Colab VM
                logger.info(f"[{active_alias}] Uploading job specification, bundle, and worker...")
                self.mgr.run_colab_command(active_alias, ["upload", "-s", session_name, tmp_spec_path, "quiz_job.json"], timeout=30)
                try:
                    os.unlink(tmp_spec_path)
                except Exception:
                    pass

                bundle_path = self.prepare_bundle("all")
                up_code, up_out, up_err = self.mgr.run_colab_command(active_alias, ["upload", "-s", session_name, str(bundle_path), "quiz_bundle.tar.gz"], timeout=180)
                if up_code != 0:
                    raise RuntimeError(f"Failed to upload quiz_bundle.tar.gz to Colab VM: {up_err or up_out}")

                if DEFAULT_SA_PATH.exists():
                    self.mgr.run_colab_command(active_alias, ["upload", "-s", session_name, str(DEFAULT_SA_PATH), "service_account.json"], timeout=30)

                if DEFAULT_OAUTH_PATH.exists():
                    self.mgr.run_colab_command(active_alias, ["upload", "-s", session_name, str(DEFAULT_OAUTH_PATH), "oauth_credentials.json"], timeout=30)

                self.mgr.run_colab_command(active_alias, ["upload", "-s", session_name, str(WORKER_SCRIPT), "colab_worker_quiz.py"], timeout=30)

                # Execute Continuous Worker
                logger.info(f"[{active_alias}] 🎬 Executing Continuous Worker on Colab VM (Zero VPS Compute)...")
                code, stdout, stderr = self.mgr.run_colab_command(
                    active_alias,
                    ["exec", "-s", session_name, "-f", str(WORKER_SCRIPT), "--timeout", str(DEFAULT_EXECUTION_TIMEOUT_SECONDS)],
                    timeout=DEFAULT_SUBPROCESS_TIMEOUT_SECONDS
                )

                print(stdout)
                if code == 0 and "[COLAB_QUIZ_COMPLETE]" in stdout:
                    logger.info(f"🎉 [{active_alias}] Session execution completed successfully!")
                    self.stop_session(active_alias)
                    self.mgr.mark_success(active_alias, cooldown_seconds=DEFAULT_COOLDOWN_SECONDS)

                    # Re-check if any pending rows remain
                    rem_map = self.find_pending_rows_across_tabs()
                    rem_total = sum(len(v) for v in rem_map.values())
                    if rem_total == 0:
                        logger.info("🎉 100% COMPLETE! All pending rows across all tabs have been rendered and verified!")
                        self.enforce_row_height()
                        return True
                    else:
                        logger.info(f"Remaining pending rows: {rem_total} ({rem_map}). Continuing to next available account...")
                else:
                    err_summary = stderr or stdout
                    raise RuntimeError(f"Colab execution returned code {code}: {err_summary[-400:] if err_summary else 'Unknown error'}")

            except Exception as exc:
                err_msg = str(exc)
                logger.warning(f"Batch execution failed or dropped on [{active_alias}]: {err_msg}")
                self.stop_session(active_alias)
                self.mgr.mark_cooldown(active_alias, duration_seconds=DEFAULT_COOLDOWN_SECONDS, reason=err_msg)

        logger.error("❌ Batch processing loop concluded with pending rows still remaining.")
        self.enforce_row_height()
        return False

    def dispatch_quiz_job(
        self,
        pipeline: str,
        row_id: str = "",
        quality: str = "qh",
        action: str = "all",
        force_gpu: bool = True,
        max_rotations: int = 5
    ) -> bool:
        """
        Dispatches a specific quiz batch job with automatic multi-account rotation,
        3-retries connection, CPU fallback, and 30-min cooldown.
        """
        if pipeline.lower() in ["all", "all_pending", "all_tabs"]:
            return self.run_all_pending(quality=quality, force_gpu=force_gpu, max_rotations=max_rotations)

        logger.info(f"=== Dispatching Quiz Job: Pipeline={pipeline.upper()} | Row={row_id or 'ALL_PENDING'} | Action={action} ===")

        rotation_attempt = 0
        while rotation_attempt < max_rotations:
            active_alias = self.mgr.select_active_account()
            if not active_alias:
                earliest, wait_sec = self.mgr.get_earliest_available_account()
                logger.error(f"❌ No active accounts available in Colab pool! Earliest [{earliest}] ready in {wait_sec}s.")
                return False

            rotation_attempt += 1
            logger.info(f"--- Attempt {rotation_attempt}/{max_rotations} using account: [{active_alias}] ---")

            try:
                session_name = self.ensure_active_session(active_alias, force_gpu=force_gpu, max_retries=3)

                tg_token, tg_chat_id = resolve_telegram_creds()
                job_spec = {
                    "pipeline": pipeline,
                    "row_id": str(row_id),
                    "quality": quality,
                    "action": action,
                    "telegram_token": tg_token,
                    "telegram_chat_id": tg_chat_id,
                    "timestamp": time.time()
                }

                with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
                    json.dump(job_spec, tmp, indent=2)
                    tmp_spec_path = tmp.name

                self.mgr.run_colab_command(active_alias, ["upload", "-s", session_name, tmp_spec_path, "quiz_job.json"], timeout=30)
                try:
                    os.unlink(tmp_spec_path)
                except Exception:
                    pass

                bundle_path = self.prepare_bundle(pipeline)
                up_code, up_out, up_err = self.mgr.run_colab_command(active_alias, ["upload", "-s", session_name, str(bundle_path), "quiz_bundle.tar.gz"], timeout=120)
                if up_code != 0:
                    raise RuntimeError(f"Failed to upload quiz_bundle.tar.gz to Colab VM: {up_err or up_out}")

                if DEFAULT_SA_PATH.exists():
                    self.mgr.run_colab_command(active_alias, ["upload", "-s", session_name, str(DEFAULT_SA_PATH), "service_account.json"], timeout=30)

                if DEFAULT_OAUTH_PATH.exists():
                    self.mgr.run_colab_command(active_alias, ["upload", "-s", session_name, str(DEFAULT_OAUTH_PATH), "oauth_credentials.json"], timeout=30)

                self.mgr.run_colab_command(active_alias, ["upload", "-s", session_name, str(WORKER_SCRIPT), "colab_worker_quiz.py"], timeout=30)

                logger.info(f"[{active_alias}] 🚀 Executing Quiz Worker on Colab VM...")
                code, stdout, stderr = self.mgr.run_colab_command(
                    active_alias,
                    ["exec", "-s", session_name, "-f", str(WORKER_SCRIPT), "--timeout", str(DEFAULT_EXECUTION_TIMEOUT_SECONDS)],
                    timeout=DEFAULT_SUBPROCESS_TIMEOUT_SECONDS
                )

                print(stdout)
                if code == 0 and "[COLAB_QUIZ_COMPLETE]" in stdout:
                    logger.info(f"🎉 [{active_alias}] JOB SUCCESS! Pipeline={pipeline} Row={row_id} completed successfully.")
                    self.stop_session(active_alias)
                    self.mgr.mark_success(active_alias, cooldown_seconds=DEFAULT_COOLDOWN_SECONDS)
                    self.enforce_row_height()
                    return True
                else:
                    err_summary = stderr or stdout
                    raise RuntimeError(f"Colab execution returned code {code}: {err_summary[-400:] if err_summary else 'Unknown error'}")

            except Exception as exc:
                err_msg = str(exc)
                logger.warning(f"Job execution failed on account [{active_alias}]: {err_msg}")
                self.stop_session(active_alias)
                self.mgr.mark_cooldown(active_alias, duration_seconds=DEFAULT_COOLDOWN_SECONDS, reason=err_msg)

        logger.error("❌ Job failed across all available Colab accounts.")
        self.enforce_row_height()
        return False

    def render_and_qc(self, pipeline: str, row_id: str, quality: str = "qh", force_gpu: bool = True) -> bool:
        """Executes full video render and automated QC on Colab."""
        return self.dispatch_quiz_job(pipeline=pipeline, row_id=row_id, quality=quality, action="all", force_gpu=force_gpu)

    def render_only(self, pipeline: str, row_id: str, quality: str = "qh", force_gpu: bool = True) -> bool:
        """Executes video render only."""
        return self.dispatch_quiz_job(pipeline=pipeline, row_id=row_id, quality=quality, action="render", force_gpu=force_gpu)

    def qc_only(self, pipeline: str, row_id: str) -> bool:
        """Executes QC inspection only."""
        return self.dispatch_quiz_job(pipeline=pipeline, row_id=row_id, action="qc")

    def stop_session(self, account_alias: Optional[str] = None):
        """Stops the active Colab session to release compute."""
        alias = account_alias or self.active_alias or self.mgr.select_active_account()
        if alias and self.active_session_name:
            logger.info(f"[{alias}] Stopping session {self.active_session_name}...")
            self.mgr.run_colab_command(alias, ["stop", "-s", self.active_session_name], timeout=30)
            self.active_session_name = None


if __name__ == "__main__":
    orch = ColabQuizOrchestrator()
    print("Colab Accounts Status:")
    for a in orch.get_pool_status():
        cd_str = f" | Cooldown: {a['cooldown_remaining_sec']}s" if a['cooldown_remaining_sec'] > 0 else ""
        print(f"  - [{a['status']}] {a['alias']} ({a['email']}) | Success: {a['success_count']}{cd_str}")

    pending = orch.find_pending_rows_across_tabs()
    print(f"\nCurrent Pending Rows Across Tabs: {pending}")
