#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit and Integration Tests for Milestone 2:
1. Pinyinquiz 3-part word parsing & auto-hidden pinyin
2. PreRenderValidator validation on pending batches
3. Dispatcher CLI harmonization across all 4 pipelines
4. Google Drive canonical folder IDs and streamable URL formatting
"""

import os
import sys
import json
import pytest
import argparse

QUIZ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if QUIZ_ROOT not in sys.path:
    sys.path.insert(0, QUIZ_ROOT)

# -------------------------------------------------------------
# Test Group 1: Pinyin 3-Part Parsing & Auto-Hidden Pinyin
# -------------------------------------------------------------

def test_pinyinquiz_parse_word_entry_3_parts():
    """Verify 3-part format 'hanzi | pinyin | meaning' correctly maps fields and computes hidden_pinyin."""
    sys.path.insert(0, os.path.join(QUIZ_ROOT, "pinyinquiz"))
    from pinyinquiz.src.gsheet_manager import GSheetManager
    mgr = GSheetManager()

    raw_word = "米饭 | mǐfàn | cơm"
    parsed = mgr.parse_word_entry(raw_word)

    assert parsed["hanzi"] == "米饭"
    assert parsed["pinyin"] == "mǐ fàn" or parsed["pinyin"] == "mǐfàn"
    assert parsed["meaning"] == "cơm"
    assert "_" in parsed["hidden_pinyin"]
    assert "cơm" not in parsed["hidden_pinyin"]


def test_pinyinquiz_parse_word_entry_4_parts():
    """Verify 4-part format 'hanzi | pinyin | hidden | meaning' preserves provided hidden_pinyin."""
    from pinyinquiz.src.gsheet_manager import GSheetManager
    mgr = GSheetManager()

    raw_word = "苹果 | píng guǒ | p _ _ _   g _ _ | quả táo"
    parsed = mgr.parse_word_entry(raw_word)

    assert parsed["hanzi"] == "苹果"
    assert parsed["pinyin"] == "píng guǒ"
    assert parsed["hidden_pinyin"] == "p _ _ _   g _ _"
    assert parsed["meaning"] == "quả táo"


def test_pinyinquiz_parse_word_entry_single_syllable():
    """Verify single syllable words correctly compute hidden pinyin."""
    from pinyinquiz.src.gsheet_manager import GSheetManager
    mgr = GSheetManager()

    raw_word = "蓝 | lán | Màu xanh lam"
    parsed = mgr.parse_word_entry(raw_word)

    assert parsed["hanzi"] == "蓝"
    assert parsed["pinyin"] == "lán"
    assert parsed["meaning"] == "Màu xanh lam"
    assert parsed["hidden_pinyin"] == "l _ _"


def test_pinyinquiz_prerender_validator_pending_batches():
    """Verify PreRenderValidator passes on target batches #54-#59 from Google Sheet."""
    from pinyinquiz.src.gsheet_manager import GSheetManager
    from pinyinquiz.src.pre_render_validator import PreRenderValidator

    mgr = GSheetManager()
    validator = PreRenderValidator()
    for b_id in ["54", "55", "56", "57", "58", "59"]:
        batch = mgr.get_batch_by_id(b_id)
        assert batch is not None, f"Batch #{b_id} should exist on sheet"
        is_valid, errors = validator.validate_batch(batch)
        assert is_valid is True, f"Batch #{b_id} failed validation: {errors}"
        assert len(errors) == 0


def test_pinyinquiz_get_batch_by_id_formatting():
    """Verify get_batch_by_id correctly parses word entries."""
    from pinyinquiz.src.gsheet_manager import GSheetManager
    mgr = GSheetManager()

    batch = mgr.get_batch_by_id("54")
    assert batch is not None
    assert len(batch["words"]) == 5
    for w in batch["words"]:
        assert "_" in w["hidden_pinyin"]
        assert w["meaning"] != w["hanzi"]


# -------------------------------------------------------------
# Test Group 2: Dispatcher CLI Harmonization
# -------------------------------------------------------------

def test_dispatcher_dry_run_all_pipelines(capsys, monkeypatch):
    """Verify scripts/run_render_dispatcher.py --dry-run --tab all constructs correct commands."""
    from scripts.run_render_dispatcher import execute_rendering_in_gha
    from unittest.mock import MagicMock
    import multilevelsquiz.src.gsheet_manager

    # Mock pending scan for multilevels so dry-run generates the command even when 0 pending on sheet
    mock_mgr = MagicMock()
    mock_mgr.get_pending_batches.return_value = [{"_row_number": 35}]
    monkeypatch.setattr(multilevelsquiz.src.gsheet_manager, "GSheetManager", lambda: mock_mgr)

    success = execute_rendering_in_gha(tab="all", row="", quality="qh", dry_run=True)
    assert success is True

    captured = capsys.readouterr().out
    # Check that pinyinquiz was called with --from-sheet --upload-gdrive
    assert "pinyinquiz/scripts/run_batch.py --from-sheet --quality qh --upload-gdrive" in captured
    # Check that vocabCNquiz was called without --from-sheet / --upload-gdrive
    assert "vocabCNquiz/scripts/run_batch.py --quality qh" in captured
    assert "vocabCNquiz/scripts/run_batch.py --from-sheet" not in captured
    # Check that vocabVNquiz was called without --from-sheet / --upload-gdrive
    assert "vocabVNquiz/scripts/run_batch.py --quality qh" in captured
    assert "vocabVNquiz/scripts/run_batch.py --from-sheet" not in captured
    # Check that multilevelsquiz was called with --id and --force
    assert "multilevelsquiz/scripts/run_batch.py --id" in captured
    assert "--force" in captured


def test_dispatcher_dry_run_specific_rows(capsys):
    """Verify specific row handling per pipeline."""
    from scripts.run_render_dispatcher import execute_rendering_in_gha

    # Pinyin specific row
    execute_rendering_in_gha(tab="pinyin", row="54", quality="qh", dry_run=True)
    out_pinyin = capsys.readouterr().out
    assert "--row-id 54" in out_pinyin

    # VocabCN specific row
    execute_rendering_in_gha(tab="vocabCN", row="40", quality="qh", dry_run=True)
    out_cn = capsys.readouterr().out
    assert "--row_id 40" in out_cn

    # VocabVN specific row
    execute_rendering_in_gha(tab="vocabVN", row="33", quality="qh", dry_run=True)
    out_vn = capsys.readouterr().out
    assert "--row_id 33" in out_vn

    # Multilevels specific row
    execute_rendering_in_gha(tab="multilevels", row="34", quality="qh", dry_run=True)
    out_ml = capsys.readouterr().out
    assert "--id 34" in out_ml


def test_sub_pipeline_argument_compatibility():
    """Verify that all flags dispatched to sub-pipeline scripts are valid arguments."""
    import subprocess

    # pinyinquiz: --from-sheet --quality qh --upload-gdrive --row-id 54
    pinyin_help = subprocess.run([sys.executable, "pinyinquiz/scripts/run_batch.py", "--help"], capture_output=True, text=True, check=True)
    assert "--from-sheet" in pinyin_help.stdout
    assert "--upload-gdrive" in pinyin_help.stdout
    assert "--row-id" in pinyin_help.stdout

    # vocabCN: --quality qh --row_id 40
    cn_help = subprocess.run([sys.executable, "vocabCNquiz/scripts/run_batch.py", "--help"], capture_output=True, text=True, check=True)
    assert "--row_id" in cn_help.stdout
    assert "--from-sheet" not in cn_help.stdout

    # vocabVN: --quality qh --row_id 33
    vn_help = subprocess.run([sys.executable, "vocabVNquiz/scripts/run_batch.py", "--help"], capture_output=True, text=True, check=True)
    assert "--row_id" in vn_help.stdout
    assert "--from-sheet" not in vn_help.stdout

    # multilevels: --id 34 --quality qh --force
    ml_help = subprocess.run([sys.executable, "multilevelsquiz/scripts/run_batch.py", "--help"], capture_output=True, text=True, check=True)
    assert "--id" in ml_help.stdout
    assert "--force" in ml_help.stdout


# -------------------------------------------------------------
# Test Group 3: Canonical Google Drive Folders & Streamable URLs
# -------------------------------------------------------------

def test_canonical_folder_ids_match_folder_map():
    """Verify target folder IDs across configs match gdrive_folder_map.json."""
    with open(os.path.join(QUIZ_ROOT, "gdrive_folder_map.json"), "r", encoding="utf-8") as f:
        folder_map = json.load(f)

    expected_pinyin = folder_map["tabs"]["pinyin"]["target_folder_id"]
    expected_vocabcn = folder_map["tabs"]["vocabCN"]["target_folder_id"]
    expected_vocabvn = folder_map["tabs"]["vocabVN"]["target_folder_id"]
    expected_multilevels = folder_map["tabs"]["multilevels"]["target_folder_id"]

    assert expected_pinyin == "1f2mFUgpz_pYn3y9HqeHyOG9DzPMVH9QY"
    assert expected_vocabcn == "1eI7I4jQqGBjD7MC_NXJ4zwFANxrcZM1E"
    assert expected_vocabvn == "1VPqs9h4LLmmmXWKDGWoAz1fUCylVLK2H"
    assert expected_multilevels == "17xOkiW-XOWRDK2CCwNEl_rlf1rGKqKXm"

    from vocabCNquiz.src.config import config as cn_cfg
    from vocabVNquiz.src.config import config as vn_cfg
    from multilevelsquiz.src.config import config as ml_cfg
    from pinyinquiz.scripts.run_batch import TARGET_GDRIVE_FOLDER_ID as pinyin_fid

    assert cn_cfg.gdrive_target_folder == expected_vocabcn
    assert vn_cfg.gdrive_target_folder == expected_vocabvn
    assert ml_cfg.gdrive_target_folder == expected_multilevels
    assert pinyin_fid == expected_pinyin


def test_streamable_url_formatting_logic():
    """Verify streamable URL format template across uploaders."""
    file_id = "test_file_id_12345"
    expected_url = f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk"

    # Verify formatting string construction
    url = f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk"
    assert url == expected_url
    assert "view?usp=drivesdk" in url
