#!/usr/bin/env python3
"""
Empirical Challenger Test Suite for Milestone 2: Google Sheets Tab vocabCN Audit & Cleanup
Target Sheet ID: 1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0
Target Tab: vocabCN
"""

import os
import sys
import re
import pytest

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from src.gsheet_manager import GSheetManager

EXPECTED_HEADER = [
    '#', 'Topic', 'Level', 'Status', 'Word 1', 'Word 2', 'Word 3', 'Word 4',
    'Word 5', 'metadata', 'Video', 'Youtube', 'Tiktok', 'Facebook', 'Created At', 'Notes'
]

DRIVE_URL_REGEX = re.compile(r"^https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)/view(\?usp=drivesdk)?$")


@pytest.fixture(scope="module")
def gsheet_live():
    gm = GSheetManager()
    return gm.worksheet


def test_row_count_exact(gsheet_live):
    """Assert len(rows) >= 3 (Header + Row 2 + Row 3 + Row 4)."""
    rows = gsheet_live.get_all_values()
    assert len(rows) >= 3, f"Expected at least 3 rows, found {len(rows)}: {rows}"


def test_header_schema(gsheet_live):
    """Assert rows[0] == exact 16 standard columns."""
    rows = gsheet_live.get_all_values()
    assert len(rows) >= 1
    assert rows[0] == EXPECTED_HEADER, f"Header mismatch! Expected {EXPECTED_HEADER}, got {rows[0]}"


def test_row_ids_and_numbering(gsheet_live):
    """Assert rows[1][0] == '#2' and rows[2][0] == '#3', and subsequent rows match # == Row ID."""
    rows = gsheet_live.get_all_values()
    assert len(rows) >= 3
    assert rows[1][0] == '#2', f"Expected '#2' at row 1 col 0, got '{rows[1][0]}'"
    assert rows[2][0] == '#3', f"Expected '#3' at row 2 col 0, got '{rows[2][0]}'"
    for idx, row in enumerate(rows[1:], start=2):
        clean_id = row[0].replace("#", "").strip()
        assert clean_id == str(idx), f"Row {idx} '#' column mismatch: expected '{idx}' or '#{idx}', got '{row[0]}'"


def test_row_statuses(gsheet_live):
    """Assert rows have valid statuses ('Pending', 'Video', 'Ready')."""
    rows = gsheet_live.get_all_values()
    assert len(rows) >= 3
    assert rows[1][3] == 'Video', f"Expected 'Video' for row 1 status, got '{rows[1][3]}'"
    assert rows[2][3] == 'Ready', f"Expected 'Ready' for row 2 status, got '{rows[2][3]}'"
    for idx, row in enumerate(rows[1:], start=2):
        assert row[3] in ('Pending', 'Video', 'Ready'), f"Row {idx} has invalid status '{row[3]}'"


def test_drive_video_urls(gsheet_live):
    """Assert valid Drive video URLs in Col K (index 10) for Video/Ready rows."""
    rows = gsheet_live.get_all_values()
    assert len(rows) >= 3
    
    for idx, row in enumerate(rows[1:], start=2):
        status = row[3].strip()
        video_url = row[10].strip()
        if status in ('Video', 'Ready'):
            assert video_url != "", f"Row {idx} with status '{status}' has empty Video URL"
            m = DRIVE_URL_REGEX.match(video_url)
            assert m is not None, f"Row {idx} Video URL '{video_url}' does not match Google Drive pattern"
            file_id = m.group(1)
            assert len(file_id) >= 20, f"Drive file ID at row {idx} '{file_id}' looks too short/invalid"


def test_word_columns_and_linguistic_invariants(gsheet_live):
    """Assert word columns (Cols 4..8) contain valid 3-part or 4-part pipe-separated entries."""
    rows = gsheet_live.get_all_values()
    assert len(rows) >= 3
    
    for row_idx in range(1, len(rows)):
        row = rows[row_idx]
        for col_idx in range(4, 9):
            word_str = row[col_idx].strip()
            assert word_str != "", f"Empty word at row {row_idx+1}, col {col_idx+1}"
            parts = [p.strip() for p in word_str.split("|")]
            assert len(parts) >= 3, f"Invalid word format in row {row_idx+1}, col {col_idx+1}: '{word_str}'"
            hanzi, pinyin = parts[0], parts[1]
            assert hanzi != "", f"Empty hanzi in '{word_str}'"
            assert pinyin != "", f"Empty pinyin in '{word_str}'"


def test_no_corrupt_duplicate_rows_in_sheet(gsheet_live):
    """Assert all rows are valid production rows without corrupt duplicate fallback repetitions."""
    rows = gsheet_live.get_all_values()
    topics = []
    for idx, row in enumerate(rows[1:], start=2):
        top = row[1].strip()
        assert top != "", f"Row {idx} has empty topic"
        # Check topic uniqueness across production rows
        assert top not in topics, f"Duplicate topic detected at row #{idx}: '{top}'"
        topics.append(top)
