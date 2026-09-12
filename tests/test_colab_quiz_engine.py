#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit and Integration Tests for Google Colab Quiz Engine.
Verifies Colab account manager, blacklist invariant, 30-minute cooldown (1800s),
3-retries connection with CPU fallback, worker compilation, and CLI dispatchers.
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

QUIZ_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(QUIZ_ROOT))

from colab.colab_rotator import ColabAccountManager, BLACKLISTED_EMAILS, DEFAULT_COOLDOWN_SECONDS
from colab.colab_orchestrator import ColabQuizOrchestrator


def test_colab_account_manager_blacklist_enforcement():
    """Verify that aleron.dt@gmail.com is strictly forbidden and rejected."""
    mgr = ColabAccountManager()
    accounts = mgr.list_accounts()

    for acc in accounts:
        email = acc.get("email", "").lower()
        for bl in BLACKLISTED_EMAILS:
            assert bl not in email, f"Policy violation: blacklisted email {email} detected in pool!"

    # Attempting to register blacklisted account must raise PermissionError
    with pytest.raises(PermissionError):
        mgr.register_account("forbidden_test", "aleron.dt@gmail.com")


def test_strict_30_minute_cooldown_policy(tmp_path):
    """Verify that mark_success and mark_cooldown strictly enforce 1800s (30m) cooldown."""
    mgr = ColabAccountManager(base_dir=str(tmp_path))
    mgr.register_account("test_user_1", "test1@gmail.com")

    # Create dummy token
    tok_dir = tmp_path / "test_user_1" / ".config" / "colab-cli"
    tok_dir.mkdir(parents=True, exist_ok=True)
    with open(tok_dir / "token.json", "w") as f:
        f.write('{"id_token": "dummy"}')

    assert mgr.select_active_account() == "test_user_1"

    # 1. Test mark_success puts account in 1800s cooldown
    mgr.mark_success("test_user_1")
    acc = [a for a in mgr.list_accounts() if a["alias"] == "test_user_1"][0]
    assert acc["status"] == "COOLING_DOWN"
    assert 1790 <= acc["cooldown_remaining_sec"] <= 1800

    # It must NOT be selectable while in cooldown
    assert mgr.select_active_account() is None

    # 2. Test mark_cooldown puts account in 1800s cooldown
    mgr.register_account("test_user_2", "test2@gmail.com")
    mgr.mark_cooldown("test_user_2")
    acc2 = [a for a in mgr.list_accounts() if a["alias"] == "test_user_2"][0]
    assert acc2["status"] == "COOLING_DOWN"
    assert 1790 <= acc2["cooldown_remaining_sec"] <= 1800


def test_colab_orchestrator_initialization():
    """Verify that ColabQuizOrchestrator can initialize and inspect the account pool."""
    orch = ColabQuizOrchestrator()
    status = orch.get_pool_status()
    assert isinstance(status, list)
    assert len(status) >= 1
    assert any(a["alias"] == "gmail_1" for a in status)


def test_colab_orchestrator_3_retries_and_cpu_fallback(tmp_path):
    """Verify that ensure_active_session tries GPU first, falls back to CPU, and retries up to 3 times."""
    mgr = ColabAccountManager(base_dir=str(tmp_path))
    mgr.register_account("mock_user", "mock@gmail.com")

    # Mock run_colab_command
    calls = []
    def mock_run(account_alias, cmd_args, timeout=None, capture_output=True):
        calls.append(cmd_args)
        if "sessions" in cmd_args:
            return 0, "", ""
        if "--gpu" in cmd_args:
            # Simulate GPU quota error
            return 1, "", "ResourceExhausted: 429 Quota Exceeded for GPU T4"
        if cmd_args[:2] == ["new", "-s"]:
            # CPU fallback succeeds
            return 0, "Created session", ""
        return 0, "", ""

    mgr.run_colab_command = mock_run
    orch = ColabQuizOrchestrator(manager=mgr)

    sess = orch.ensure_active_session("mock_user", force_gpu=True, max_retries=3)
    assert sess.startswith("quiz_worker_")

    # Verify calls: first was sessions, second was new --gpu T4, third was new (CPU fallback)
    gpu_calls = [c for c in calls if "--gpu" in c]
    cpu_fallback_calls = [c for c in calls if c[:2] == ["new", "-s"] and "--gpu" not in c]
    assert len(gpu_calls) == 1
    assert len(cpu_fallback_calls) == 1


def test_colab_worker_script_exists_and_compiles():
    """Verify that colab_worker_quiz.py is present and compiles cleanly."""
    worker_script = QUIZ_ROOT / "colab" / "colab_worker_quiz.py"
    assert worker_script.exists()
    assert os.access(worker_script, os.X_OK)

    res = subprocess.run([sys.executable, "-m", "py_compile", str(worker_script)], capture_output=True)
    import shutil
    shutil.rmtree(worker_script.parent / "__pycache__", ignore_errors=True)
    assert res.returncode == 0, f"Worker script compilation failed: {res.stderr.decode()}"


def test_colab_cli_dispatcher_help():
    """Verify that colab_render_cli.py executes and displays help message."""
    cli_script = QUIZ_ROOT / "scripts" / "colab_render_cli.py"
    assert cli_script.exists()

    res = subprocess.run([sys.executable, str(cli_script), "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "LeLe Quiz Colab CLI Dispatcher" in res.stdout


def test_colab_auto_render_daemon_help():
    """Verify that colab_auto_render_daemon.py executes and displays help message."""
    daemon_script = QUIZ_ROOT / "scripts" / "colab_auto_render_daemon.py"
    assert daemon_script.exists()

    res = subprocess.run([sys.executable, str(daemon_script), "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Colab Auto-Render Daemon" in res.stdout
