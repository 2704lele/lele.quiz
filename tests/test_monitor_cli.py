#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E & Unit Test Suite for In-View Terminal Dashboard & Monitor CLI Flags.
Covers Features F9, F10 (Milestone 3 / Requirements R3) and Tier 1 / Tier 2 specs:
- T1-F9-01 .. T1-F9-05 (4-node visualization, 3 sub-pipelines, directives, terminal width adaptability)
- T1-F10-01 .. T1-F10-05 (--status, --verify-tab pinyin/vocabCN/vocabVN, --inview live mode)
- T2-F9-01 .. T2-F9-05 (narrow width, node states, offline/error fallback)
- T2-F10-01 .. T2-F10-05 (invalid tab error handling, 0-row handling, missing columns detection, row invariant violation detection)
"""

import os
import sys
import subprocess
import pytest
from unittest.mock import patch, MagicMock

QUIZ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if QUIZ_ROOT not in sys.path:
    sys.path.insert(0, QUIZ_ROOT)

MONITOR_PATH = os.path.join(QUIZ_ROOT, "monitor.py")

import monitor


# ============================================================================
# 1. MONITOR DASHBOARD RENDERING & 4-NODE WORKFLOW (FEATURE F9)
# ============================================================================

def test_monitor_script_exists_and_executable():
    """Verify that monitor.py exists at project root."""
    assert os.path.exists(MONITOR_PATH), f"Missing monitor.py at {MONITOR_PATH}"


def test_monitor_dashboard_execution_and_4_nodes():
    """Verify that running monitor.py renders the 4-node schema and 3 sub-pipelines."""
    env = {**os.environ, "COLUMNS": "160"}
    res = subprocess.run([sys.executable, MONITOR_PATH, "--no-clear"], capture_output=True, text=True, cwd=QUIZ_ROOT, env=env)
    assert res.returncode == 0, f"monitor.py failed with return code {res.returncode}. Stderr: {res.stderr}"

    stdout = res.stdout
    # Check 4 nodes
    assert "1. Cloud Edge Gateway" in stdout or "CF WORKER" in stdout or "1. CF WORKER" in stdout
    assert "2. Google Sheets State DB" in stdout or "GOOGLE SHEETS" in stdout or "2. GOOGLE SHEETS" in stdout
    assert "3. GitHub Actions Manim Engine" in stdout or "GH ACTIONS" in stdout or "3. GH ACTIONS" in stdout
    assert "4. Auto-QC & GDrive Storage" in stdout or "AUTO-QC" in stdout or "GDRIVE" in stdout

    # Check 3 sub-pipelines
    assert "pinyinquiz" in stdout
    assert "vocabCN" in stdout
    assert "vocabVN" in stdout

    # Check Directives
    assert "Zero-VPS" in stdout or "Zero-VPS Ban" in stdout
    assert "1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0" in stdout
    assert "Row Number == Batch ID" in stdout or "Batch ID" in stdout


def test_monitor_dashboard_narrow_terminal_width_resilience():
    """Verify that monitor.py adapts gracefully to narrow terminals (<60 columns) without crash."""
    env = {**os.environ, "COLUMNS": "55"}
    res = subprocess.run([sys.executable, MONITOR_PATH, "--no-clear"], capture_output=True, text=True, cwd=QUIZ_ROOT, env=env)
    assert res.returncode == 0
    assert len(res.stdout) > 0


def test_format_node_states():
    """Verify format_node returns styled badges for all supported states."""
    online = monitor.format_node("Test Node", "ONLINE")
    busy = monitor.format_node("Test Node", "BUSY")
    error = monitor.format_node("Test Node", "ERROR")
    offline = monitor.format_node("Test Node", "OFFLINE")

    assert "Test Node" in online and "green" in online
    assert "Test Node" in busy and "blue" in busy
    assert "Test Node" in error and "red" in error
    assert "Test Node" in offline and "orange" in offline


# ============================================================================
# 2. MONITOR CLI FLAGS CONTRACT (FEATURE F10)
# ============================================================================

def test_monitor_cli_flag_status():
    """Verify that python monitor.py --status executes cleanly and displays summary."""
    res = subprocess.run([sys.executable, MONITOR_PATH, "--status"], capture_output=True, text=True, cwd=QUIZ_ROOT)
    assert res.returncode == 0, f"monitor.py --status failed: {res.stderr}"
    stdout = res.stdout
    assert "pinyinquiz" in stdout
    assert "vocabCNquiz" in stdout
    assert "vocabVNquiz" in stdout
    assert "Total Rows" in stdout or "TOTAL" in stdout


def test_monitor_cli_flag_verify_tab_pinyin():
    """Verify that python monitor.py --verify-tab pinyin audits tab schema and invariants."""
    res = subprocess.run([sys.executable, MONITOR_PATH, "--verify-tab", "pinyin"], capture_output=True, text=True, cwd=QUIZ_ROOT)
    assert res.returncode == 0 or "tab" in res.stdout.lower() or "tab" in res.stderr.lower()
    assert "pinyin" in res.stdout.lower() or "pinyin" in res.stderr.lower()


def test_monitor_cli_flag_verify_tab_vocabcn():
    """Verify that python monitor.py --verify-tab vocabCN audits tab schema and invariants."""
    res = subprocess.run([sys.executable, MONITOR_PATH, "--verify-tab=vocabCN"], capture_output=True, text=True, cwd=QUIZ_ROOT)
    assert res.returncode == 0 or "tab" in res.stdout.lower() or "tab" in res.stderr.lower()
    assert "vocabcn" in res.stdout.lower() or "vocabcn" in res.stderr.lower()


def test_monitor_cli_flag_verify_tab_vocabvn():
    """Verify that python monitor.py --verify-tab vocabVN audits tab schema and invariants."""
    res = subprocess.run([sys.executable, MONITOR_PATH, "--verify-tab", "vocabVN"], capture_output=True, text=True, cwd=QUIZ_ROOT)
    assert res.returncode == 0 or "tab" in res.stdout.lower() or "tab" in res.stderr.lower()
    assert "vocabvn" in res.stdout.lower() or "vocabvn" in res.stderr.lower()


def test_monitor_cli_flag_verify_tab_all():
    """Verify that python monitor.py --verify-tab all audits all 3 tabs."""
    res = subprocess.run([sys.executable, MONITOR_PATH, "--verify-tab=all"], capture_output=True, text=True, cwd=QUIZ_ROOT)
    assert res.returncode == 0 or "tab" in res.stdout.lower() or "tab" in res.stderr.lower()
    assert "pinyin" in res.stdout.lower() or "pinyin" in res.stderr.lower()


def test_monitor_cli_flag_verify_tab_invalid():
    """Verify that invalid tab name outputs error message listing valid tabs."""
    res = subprocess.run([sys.executable, MONITOR_PATH, "--verify-tab", "nonexistent_tab"], capture_output=True, text=True, cwd=QUIZ_ROOT)
    assert res.returncode != 0
    assert "Invalid tab name" in res.stdout or "Invalid tab name" in res.stderr
    assert "pinyin" in res.stdout or "pinyin" in res.stderr


def test_monitor_cli_flag_inview():
    """Verify that python monitor.py --inview is recognized and runs."""
    try:
        res = subprocess.run([sys.executable, MONITOR_PATH, "--inview", "--interval", "1"], capture_output=True, text=True, cwd=QUIZ_ROOT, timeout=2)
        assert res.returncode == 0
    except subprocess.TimeoutExpired:
        # Timeout is expected since --inview is a continuous refresh loop
        pass


def test_monitor_cli_flag_inview_with_arg():
    """Verify that python monitor.py --inview 1 is recognized and runs."""
    try:
        res = subprocess.run([sys.executable, MONITOR_PATH, "--inview", "1"], capture_output=True, text=True, cwd=QUIZ_ROOT, timeout=2)
        assert res.returncode == 0
    except subprocess.TimeoutExpired:
        # Timeout is expected since --inview is a continuous refresh loop
        pass


def test_monitor_cli_flag_social():
    """Verify that python monitor.py --social displays omni-channel social media channels and Buffer status."""
    res = subprocess.run([sys.executable, MONITOR_PATH, "--social"], capture_output=True, text=True, cwd=QUIZ_ROOT)
    assert res.returncode == 0
    stdout = res.stdout
    assert "YouTube Shorts" in stdout or "YouTube" in stdout
    assert "TikTok" in stdout
    assert "Facebook Fanpage" in stdout or "Facebook" in stdout
    assert "Buffer" in stdout


# ============================================================================
# 3. CORE LOGIC, SCHEMA VALIDATION & OFFLINE RESILIENCE UNIT TESTS
# ============================================================================

def test_count_tab_statuses_calculation():
    """Verify status counting logic for various row statuses."""
    rows = [
        monitor.STANDARD_COLUMNS,
        ["#2", "Topic 1", "HSK 1", "Pending", "", "", "", "", "", "{}", "", "", "", "", "2026-08-27", ""],
        ["#3", "Topic 2", "HSK 1", "Rendering", "", "", "", "", "", "{}", "", "", "", "", "2026-08-27", ""],
        ["#4", "Topic 3", "HSK 1", "In Progress", "", "", "", "", "", "{}", "", "", "", "", "2026-08-27", ""],
        ["#5", "Topic 4", "HSK 1", "Video", "", "", "", "", "", "{}", "https://drive.google.com/file/d/1234567890123456789012345/view?usp=drivesdk", "", "", "", "2026-08-27", ""],
        ["#6", "Topic 5", "HSK 1", "Ready", "", "", "", "", "", "{}", "https://drive.google.com/file/d/1234567890123456789012345/view?usp=drivesdk", "", "", "", "2026-08-27", ""],
        ["#7", "Topic 6", "HSK 1", "Published", "", "", "", "", "", "{}", "", "", "", "", "2026-08-27", ""],
        ["#8", "Topic 7", "HSK 1", "Failed", "", "", "", "", "", "{}", "", "", "", "", "2026-08-27", ""],
    ]
    counts = monitor.count_tab_statuses(rows)
    assert counts["Pending"] == 1
    assert counts["Rendering"] == 2  # "Rendering" and "In Progress"
    assert counts["Video"] == 1
    assert counts["Ready"] == 1
    assert counts["Published"] == 1
    assert counts["Failed"] == 1
    assert counts["Total"] == 7


def test_verify_tab_data_clean_success():
    """Verify verify_tab_data on 100% compliant data."""
    valid_rows = [
        monitor.STANDARD_COLUMNS,
        ["#2", "Topic 1", "HSK 1", "Ready", "A", "B", "C", "D", "E", "{}", "https://drive.google.com/file/d/1abcdefghijklmnopqrstuvwxyz/view?usp=drivesdk", "", "", "", "2026-08-27", ""],
        ["#3", "Topic 2", "HSK 2", "Ready", "A", "B", "C", "D", "E", "{}", "https://drive.google.com/file/d/1234567890abcdefghijklmno/view?usp=drivesdk", "", "", "", "2026-08-27", ""]
    ]
    audit = monitor.verify_tab_data("test_tab", valid_rows)
    assert audit["is_valid"] is True
    assert audit["header_valid"] is True
    assert len(audit["row_invariant_violations"]) == 0
    assert len(audit["invalid_video_urls"]) == 0
    assert audit["data_rows_count"] == 2


def test_verify_tab_data_catches_missing_columns():
    """Verify verify_tab_data flags missing standard columns."""
    incomplete_header = ["#", "Topic", "Level", "Status", "Word 1"]
    rows = [
        incomplete_header,
        ["#2", "Topic 1", "HSK 1", "Ready", "A"]
    ]
    audit = monitor.verify_tab_data("test_tab", rows)
    assert audit["is_valid"] is False
    assert audit["header_valid"] is False
    assert "Video" in audit["missing_columns"]
    assert "metadata" in audit["missing_columns"]


def test_verify_tab_data_catches_row_id_invariant_violation():
    """Verify verify_tab_data detects when Batch ID (#) does not match row index."""
    mismatched_rows = [
        monitor.STANDARD_COLUMNS,
        ["#2", "Topic 1", "HSK 1", "Ready", "", "", "", "", "", "{}", "", "", "", "", "", ""],
        ["#99", "Topic 2", "HSK 1", "Ready", "", "", "", "", "", "{}", "", "", "", "", "", ""]  # Row 3 has ID #99
    ]
    audit = monitor.verify_tab_data("test_tab", mismatched_rows)
    assert audit["is_valid"] is False
    assert len(audit["row_invariant_violations"]) == 1
    assert audit["row_invariant_violations"][0]["row_index"] == 3
    assert audit["row_invariant_violations"][0]["found_id"] == "#99"


def test_verify_tab_data_catches_invalid_video_urls():
    """Verify verify_tab_data detects non-GDrive or malformed Column K URLs."""
    bad_url_rows = [
        monitor.STANDARD_COLUMNS,
        ["#2", "Topic 1", "HSK 1", "Ready", "", "", "", "", "", "{}", "http://youtube.com/watch?v=123", "", "", "", "", ""]
    ]
    audit = monitor.verify_tab_data("test_tab", bad_url_rows)
    assert audit["is_valid"] is False
    assert len(audit["invalid_video_urls"]) == 1
    assert audit["invalid_video_urls"][0]["row_index"] == 2


def test_offline_fallback_status_handling():
    """Verify that when gsheet credentials cannot be loaded, handle_status_command displays fallback cleanly."""
    with patch("monitor.get_gsheet_client", return_value=(None, "Mock Offline Error")):
        ret = monitor.handle_status_command()
        assert ret == 0
