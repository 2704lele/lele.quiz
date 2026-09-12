#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Suite for Universal Auto-Healing Engine (scripts/auto_heal.py & ./auto_heal.sh).
Verifies:
1. GDrive Connection & 6 target folders diagnostics.
2. GSheets State DB 16 standard columns & 21px row height invariant.
3. Buffer Social API Buffer 1 channels & vault isolation.
4. Google Colab CLI Pool (5 Accounts) & aleron.dt blacklist & hung VM release.
5. Code sync & exFAT bytecode hygiene.
6. CLI flags: --check, --heal, --json.
7. Menu option [a] integration.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

QUIZ_ROOT = Path(__file__).resolve().parent.parent
if str(QUIZ_ROOT) not in sys.path:
    sys.path.insert(0, str(QUIZ_ROOT))

from scripts.auto_heal import (
    AutoHealEngine,
    TARGET_GDRIVE_FOLDERS,
    BUFFER_1_TARGET_CHANNELS,
    STANDARD_16_COLUMNS,
    COLAB_EXECUTION_TIMEOUT_SEC
)
import menu


def test_auto_heal_constants_completeness():
    """Verify all 6 target GDrive folders and 3 Buffer channels are defined."""
    assert len(TARGET_GDRIVE_FOLDERS) == 6
    assert "00.codebases" in TARGET_GDRIVE_FOLDERS
    assert "Backups" in TARGET_GDRIVE_FOLDERS
    assert "01.pinyinquiz" in TARGET_GDRIVE_FOLDERS
    assert "02.vocabCNquiz" in TARGET_GDRIVE_FOLDERS
    assert "03.vocabVNquiz" in TARGET_GDRIVE_FOLDERS
    assert "04.multilevelsquiz" in TARGET_GDRIVE_FOLDERS

    assert TARGET_GDRIVE_FOLDERS["00.codebases"]["id"] == "1C-n3Un-D6Teu4LapgIWWeVZ6l7toH8lm"
    assert TARGET_GDRIVE_FOLDERS["Backups"]["id"] == "1QHYaOfvE8yoShR4UcM0o3zd0uOh7rhaK"

    assert len(BUFFER_1_TARGET_CHANNELS) == 3
    assert BUFFER_1_TARGET_CHANNELS["youtube_shorts"] == "6a83dda0ccaf649a67c8cb92"
    assert BUFFER_1_TARGET_CHANNELS["tiktok"] == "6a83dc5bccaf649a67c8b30f"
    assert BUFFER_1_TARGET_CHANNELS["facebook_fanpage"] == "6a871331ccaf649a67e1b724"

    assert len(STANDARD_16_COLUMNS) == 16
    assert STANDARD_16_COLUMNS[0] == "#"
    assert STANDARD_16_COLUMNS[-1] == "Notes"


def test_auto_heal_engine_initialization():
    """Verify AutoHealEngine initializes with proper workspace."""
    engine = AutoHealEngine(workspace_dir=QUIZ_ROOT)
    assert engine.workspace_dir == QUIZ_ROOT
    assert isinstance(engine.actions_taken, list)


def test_diagnose_gdrive_folders_live():
    """Verify live GDrive diagnosis checks all 6 target folders successfully."""
    engine = AutoHealEngine(workspace_dir=QUIZ_ROOT)
    res = engine.diagnose_and_heal_gdrive(heal=False)

    assert res["status"] in ("HEALTHY", "WARNING")
    assert len(res["target_folders"]) == 6
    for key in TARGET_GDRIVE_FOLDERS.keys():
        assert key in res["target_folders"]
        folder_res = res["target_folders"][key]
        assert folder_res.get("accessible") is True
        assert folder_res.get("is_folder") is True


def test_diagnose_gsheets_state_db_live():
    """Verify GSheets diagnostics audits 16 standard columns & 21px row height."""
    engine = AutoHealEngine(workspace_dir=QUIZ_ROOT)
    res = engine.diagnose_and_heal_gsheets(heal=False)

    assert res["status"] in ("HEALTHY", "WARNING")
    # 4 tabs check
    tabs_check = res["tabs_columns_check"]
    assert len(tabs_check) == 4
    for tab in ["pinyin", "vocabCN", "vocabVN", "multilevels"]:
        assert tab in tabs_check
        assert tabs_check[tab]["columns_count"] == 16
        assert tabs_check[tab]["valid"] is True

    # 21px row height check
    rh = res["row_height_21px"]
    assert rh["total_rows"] > 0
    assert rh["non_target_rows"] == 0
    assert rh["all_target"] is True


def test_diagnose_buffer_social_api():
    """Verify Buffer Social API credentials and 3 channel mappings."""
    engine = AutoHealEngine(workspace_dir=QUIZ_ROOT)
    res = engine.diagnose_and_heal_buffer_social(heal=False)

    assert res["status"] == "HEALTHY"
    assert res["credentials_file"] == "VALID"
    assert len(res["channels"]) == 3
    for ch_name in ["youtube_shorts", "tiktok", "facebook_fanpage"]:
        assert ch_name in res["channels"]
        assert res["channels"][ch_name]["token_mapped"] is True

    assert res["credential_isolation"]["vault_permissions_ok"] is True
    assert res["credential_isolation"]["stray_leaks_count"] == 0


def test_diagnose_colab_pool_5_accounts_and_blacklist():
    """Verify 5 accounts registered and blacklist of aleron.dt strictly enforced."""
    engine = AutoHealEngine(workspace_dir=QUIZ_ROOT)
    res = engine.diagnose_and_heal_colab_pool(heal=False)

    assert res["status"] in ("HEALTHY", "WARNING")
    assert res["accounts_registered"] >= 5
    assert res["blacklist_enforced"] is True

    for alias in ["gmail_1", "gmail_2", "gmail_3", "gmail_4", "gmail_5"]:
        assert alias in res["accounts"]
        acc_info = res["accounts"][alias]
        assert "aleron.dt" not in acc_info["email"].lower()


def test_colab_hung_session_detection_mock(tmp_path):
    """Verify that sessions older than 4800s are detected as hung and cleaned in heal mode."""
    engine = AutoHealEngine(workspace_dir=QUIZ_ROOT)

    # Mock ColabAccountManager
    with patch("scripts.auto_heal.ColabAccountManager") as MockMgr:
        mock_mgr_instance = MagicMock()
        MockMgr.return_value = mock_mgr_instance

        # Return active session 'quiz_worker_old'
        mock_mgr_instance.run_colab_command.return_value = (0, "[quiz_worker_old] https://colab...", "")

        # Create dummy profile dir with aged sessions.json
        prof_dir = tmp_path / "gmail_1"
        cli_dir = prof_dir / ".config" / "colab-cli"
        cli_dir.mkdir(parents=True, exist_ok=True)
        sess_file = cli_dir / "sessions.json"
        with open(sess_file, "w") as f:
            json.dump({"quiz_worker_old": {"name": "quiz_worker_old"}}, f)

        # Set file mtime to 5000s ago (> 4800s)
        old_time = time.time() - 5000
        os.utime(sess_file, (old_time, old_time))

        mock_mgr_instance.get_account_profile_dir.return_value = prof_dir

        res = engine.diagnose_and_heal_colab_pool(heal=True)
        assert res["hung_sessions_detected"] >= 1
        assert res["hung_sessions_released"] >= 1
        mock_mgr_instance.run_colab_command.assert_any_call("gmail_1", ["stop", "-s", "quiz_worker_old"], timeout=30)


def test_code_sync_and_exfat_hygiene_clean():
    """Verify scripts exist, compile, and exFAT has 0 bytecode."""
    engine = AutoHealEngine(workspace_dir=QUIZ_ROOT)
    res = engine.diagnose_and_heal_code_sync_and_hygiene(heal=True)

    assert res["status"] == "HEALTHY"
    assert res["sync_code_to_gdrive_script"]["exists"] is True
    assert res["sync_code_to_gdrive_script"]["syntax_valid"] is True
    assert res["auto_backup_script"]["exists"] is True
    assert res["auto_backup_script"]["syntax_valid"] is True
    assert res["exfat_bytecode_hygiene"]["stray_pyc_count"] == 0
    assert res["exfat_bytecode_hygiene"]["stray_pycache_dirs"] == 0


def test_cli_wrapper_check_exit_zero():
    """Verify ./auto_heal.sh --check executes cleanly with exit code 0."""
    wrapper_path = QUIZ_ROOT / "auto_heal.sh"
    assert wrapper_path.exists()
    assert os.access(wrapper_path, os.X_OK)

    res = subprocess.run([str(wrapper_path), "--check"], cwd=QUIZ_ROOT, capture_output=True, text=True)
    assert res.returncode == 0, f"auto_heal.sh --check failed: {res.stderr}"
    assert "LELE QUIZ UNIVERSAL AUTO-HEALING" in res.stdout


def test_cli_wrapper_json_output_valid():
    """Verify ./auto_heal.sh --check --json returns valid parseable JSON."""
    wrapper_path = QUIZ_ROOT / "auto_heal.sh"
    res = subprocess.run([str(wrapper_path), "--check", "--json"], cwd=QUIZ_ROOT, capture_output=True, text=True)
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["overall_healthy"] is True
    assert "subsystems" in data
    assert len(data["subsystems"]) == 5


def test_menu_integration_option_a():
    """Verify menu.py prints option [a] and has action_auto_heal function."""
    assert hasattr(menu, "action_auto_heal")
    import io
    from contextlib import redirect_stdout
    f = io.StringIO()
    with redirect_stdout(f):
        menu.print_banner()
    out = f.getvalue()
    assert "[a]" in out
    assert "Auto-Healing Engine" in out
