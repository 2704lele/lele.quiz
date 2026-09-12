#!/usr/bin/env python3
"""
E2E Production Test Suite for Batches #5, #6, #7, #8, #9 on Google Sheets tab vocabCN.
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
def live_rows():
    gm = GSheetManager()
    rows = gm.get_all_rows()
    return rows


def test_rows_5_to_9_existence_and_ids(live_rows):
    """Verify that Rows #5..#9 exist with matching row numbers and IDs."""
    row_map = {int(r.get("_row_number")): r for r in live_rows if r.get("_row_number")}
    for row_id in range(5, 10):
        assert row_id in row_map, f"Missing Row #{row_id} in Google Sheets tab vocabCN"
        r = row_map[row_id]
        assert r.get("#") == f"#{row_id}", f"Row #{row_id} '#' column mismatch: got '{r.get('#')}'"


def test_rows_5_to_9_statuses_and_qc_notes(live_rows):
    """Verify that Rows #5..#9 have valid production statuses and proper notes."""
    row_map = {int(r.get("_row_number")): r for r in live_rows if r.get("_row_number")}
    for row_id in range(5, 10):
        r = row_map[row_id]
        status = r.get("Status", "").strip()
        assert status in ["Pending", "Rendering", "Video", "Ready"], f"Row #{row_id} Status is '{status}', invalid status"
        if status == "Ready":
            notes = r.get("Notes", "").strip()
            assert "Auto-QC Passed" in notes, f"Row #{row_id} Notes missing Auto-QC timestamp: got '{notes}'"


def test_rows_5_to_9_video_urls_and_social_metadata(live_rows):
    """Verify that Rows #5..#9 have valid metadata structure and direct playable Google Drive links if rendered."""
    row_map = {int(r.get("_row_number")): r for r in live_rows if r.get("_row_number")}
    for row_id in range(5, 10):
        r = row_map[row_id]
        status = r.get("Status", "").strip()
        video_url = r.get("Video", "").strip()
        if status == "Ready" or video_url:
            assert video_url != "", f"Row #{row_id} Video URL is empty for status '{status}'"
            m = DRIVE_URL_REGEX.match(video_url)
            assert m is not None, f"Row #{row_id} Video URL '{video_url}' does not match Google Drive pattern"
            file_id = m.group(1)
            assert len(file_id) >= 20, f"Row #{row_id} Drive file ID '{file_id}' is too short"

        meta = r.get("metadata", "").strip()
        if meta:
            assert "YOUTUBE SHORTS" in meta or "TIKTOK" in meta or "{" in meta, f"Row #{row_id} metadata invalid format"


def test_rows_5_to_9_linguistic_invariants(live_rows):
    """Verify that Rows #5..#9 pass all Gatekeeper 1 linguistic and topic validation rules."""
    row_map = {int(r.get("_row_number")): r for r in live_rows if r.get("_row_number")}
    for row_id in range(5, 10):
        r = row_map[row_id]
        topic = r.get("Topic", "").strip()
        level = r.get("Level", "").strip()

        words = []
        for col_name in ["Word 1", "Word 2", "Word 3", "Word 4", "Word 5"]:
            cell_val = r.get(col_name, "").strip()
            assert cell_val != "", f"Row #{row_id} {col_name} is empty"
            parts = [p.strip() for p in cell_val.split("|")]
            assert len(parts) >= 3, f"Row #{row_id} {col_name} '{cell_val}' does not have at least 3 pipe-separated parts"
            hanzi, pinyin, meaning = parts[0], parts[1], parts[-1]
            words.append({"hanzi": hanzi, "pinyin": pinyin, "meaning": meaning})

        assert len(words) == 5, f"Row #{row_id} expected exactly 5 words, got {len(words)}"

        is_valid, errors = PreRenderValidator.validate_batch({
            "id": str(row_id),
            "topic": topic,
            "level": level,
            "words": words
        })
        assert is_valid, f"Row #{row_id} failed Gatekeeper 1 validation! Errors: {errors}"


def test_rows_2_to_9_global_deduplication(live_rows):
    """Verify zero duplicate topics and minimal word overlap across all Rows #2..#9."""
    topics = []
    word_sets = []

    for r in live_rows:
        row_id = int(r.get("_row_number", 0))
        if row_id < 2 or row_id > 9:
            continue
        topic = r.get("Topic", "").strip()
        assert topic not in topics, f"Duplicate topic '{topic}' found across sheet rows"
        topics.append(topic)

        row_words = []
        for col in ["Word 1", "Word 2", "Word 3", "Word 4", "Word 5"]:
            h = r.get(col, "").split("|")[0].strip()
            if h:
                row_words.append(h)
        word_sets.append((row_id, topic, set(row_words)))

    for i in range(len(word_sets)):
        for j in range(i + 1, len(word_sets)):
            id_a, topic_a, set_a = word_sets[i]
            id_b, topic_b, set_b = word_sets[j]
            overlap = set_a.intersection(set_b)
            assert len(overlap) <= 1, f"Illegal word overlap > 1 between Row #{id_a} ('{topic_a}') and Row #{id_b} ('{topic_b}'): {overlap}"
