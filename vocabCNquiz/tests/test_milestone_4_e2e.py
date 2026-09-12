#!/usr/bin/env python3
"""
Comprehensive Verification Suite for Milestone 4: Full End-to-End Online Production & QC Execution
Requirement R4 & R5
"""

import os
import sys
import re
import pytest

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from src.gsheet_manager import GSheetManager, STANDARD_COLUMNS
from src.pre_render_validator import PreRenderValidator

DRIVE_URL_REGEX = re.compile(r"^https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)/view(\?usp=drivesdk)?$")


@pytest.fixture(scope="module")
def gsheet_live():
    gm = GSheetManager()
    return gm.worksheet


def test_m4_row_4_existence_and_schema(gsheet_live):
    """Verify that Row #4 exists on Google Sheets tab vocabCN and has 16 columns."""
    rows = gsheet_live.get_all_values()
    assert len(rows) >= 4, f"Expected at least 4 rows (Header + #2 + #3 + #4), got {len(rows)}"
    
    header = rows[0]
    assert header == STANDARD_COLUMNS, f"Header mismatch! Expected {STANDARD_COLUMNS}, got {header}"
    
    row_4 = rows[3]
    assert len(row_4) == 16, f"Row 4 must have 16 columns, got {len(row_4)}"
    assert row_4[0] == "#4", f"Row 4 '#' column must be '#4', got '{row_4[0]}'"


def test_m4_row_4_linguistic_and_topic_validity(gsheet_live):
    """Verify that Row #4 topic, level, and words pass Gatekeeper 1 deterministic rules."""
    rows = gsheet_live.get_all_values()
    assert len(rows) >= 4
    row_4 = rows[3]
    
    topic = row_4[1].strip()
    level = row_4[2].strip()
    assert topic == "Hành Động Cơ Bản", f"Expected topic 'Hành Động Cơ Bản', got '{topic}'"
    assert level == "HSK 1", f"Expected level 'HSK 1', got '{level}'"
    
    words = []
    for col_idx in range(4, 9):
        cell_val = row_4[col_idx].strip()
        assert cell_val != "", f"Word column at index {col_idx} is empty"
        parts = [p.strip() for p in cell_val.split("|")]
        assert len(parts) >= 3, f"Word entry '{cell_val}' does not have at least 3 parts"
        hanzi, pinyin, meaning = parts[0], parts[1], parts[-1]
        words.append({"hanzi": hanzi, "pinyin": pinyin, "meaning": meaning})
    
    assert len(words) == 5, f"Expected exactly 5 words, got {len(words)}"
    
    # Audit with deterministic Gatekeeper 1
    passed, errors = PreRenderValidator.validate_batch({
        "topic": topic,
        "level": level,
        "words": words
    })
    assert passed, f"Row 4 failed Gatekeeper 1 validation! Errors: {errors}"


def test_m4_row_4_status_ready_and_qc_notes(gsheet_live):
    """Verify that Row #4 status transitioned to 'Ready' with Auto-QC pass timestamp in Notes."""
    rows = gsheet_live.get_all_values()
    assert len(rows) >= 4
    row_4 = rows[3]
    
    status = row_4[3].strip()
    assert status == "Ready", f"Expected Row 4 status 'Ready', got '{status}'"
    
    notes = row_4[15].strip()
    assert "Auto-QC Passed" in notes, f"Expected 'Auto-QC Passed' in Row 4 Notes, got '{notes}'"


def test_m4_row_4_video_url_and_metadata(gsheet_live):
    """Verify that Row #4 contains valid Google Drive video link and complete social metadata."""
    rows = gsheet_live.get_all_values()
    assert len(rows) >= 4
    row_4 = rows[3]
    
    video_url = row_4[10].strip()
    assert video_url != "", "Row 4 Video URL is empty"
    m = DRIVE_URL_REGEX.match(video_url)
    assert m is not None, f"Row 4 Video URL '{video_url}' does not match Google Drive pattern"
    file_id = m.group(1)
    assert len(file_id) >= 20, f"Drive file ID '{file_id}' looks invalid"
    
    metadata = row_4[9].strip()
    assert "YOUTUBE SHORTS" in metadata, "Missing YouTube Shorts metadata in Col J"
    assert "TIKTOK" in metadata, "Missing TikTok metadata in Col J"
    assert "FACEBOOK REELS" in metadata, "Missing Facebook Reels metadata in Col J"


def test_m4_negative_context_deduplication(gsheet_live):
    """Verify that Row #4 is strictly unique and non-overlapping with Row #2 and Row #3."""
    rows = gsheet_live.get_all_values()
    assert len(rows) >= 4
    
    row_2 = rows[1]
    row_3 = rows[2]
    row_4 = rows[3]
    
    # Topic uniqueness
    assert row_4[1] != row_2[1], "Row 4 duplicated topic from Row 2"
    assert row_4[1] != row_3[1], "Row 4 duplicated topic from Row 3"
    
    # Word uniqueness
    words_2 = [row_2[c].split("|")[0].strip() for c in range(4, 9)]
    words_3 = [row_3[c].split("|")[0].strip() for c in range(4, 9)]
    words_4 = [row_4[c].split("|")[0].strip() for c in range(4, 9)]
    
    for w in words_4:
        assert w not in words_2, f"Word '{w}' duplicated from Row 2"
        assert w not in words_3, f"Word '{w}' duplicated from Row 3"
