import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.enforce_row_height_21px import get_sheets_service, SPREADSHEET_ID, QUIZ_TABS, execute_with_backoff
from scripts.linguistic_qc import PinyinLinguisticValidator, MultilevelsEscalationValidator

APPENDED_ROWS = {
    "pinyin": (62, 66),
    "vocabCN": (46, 50),
    "vocabVN": (39, 43),
    "multilevels": (40, 44),
}


@pytest.fixture(scope="module")
def sheets_service():
    return get_sheets_service()


@pytest.fixture(scope="module")
def sheets_data(sheets_service):
    data = {}
    for tab in QUIZ_TABS:
        res = execute_with_backoff(
            sheets_service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"{tab}!A:P")
        )
        data[tab] = res.get("values", [])
    return data


def test_batch_ideation_5_pending_per_tab(sheets_data):
    """Verify that each of the 4 tabs has at least 5 rows in active pipeline lifecycle."""
    valid_statuses = {"Pending", "Ready", "Video", "Published"}
    for tab, rows in sheets_data.items():
        active_rows = [r for r in rows[1:] if len(r) > 3 and r[3].strip() in valid_statuses]
        assert len(active_rows) >= 5, f"Tab '{tab}' has {len(active_rows)} active rows, expected >= 5"


@pytest.mark.parametrize("tab", QUIZ_TABS)
def test_appended_rows_sequential_ids_and_status(sheets_data, tab):
    """Verify that the 5 newly appended rows have Column A == '#{RowIndex}' and valid pipeline Status."""
    valid_statuses = {"Pending", "Ready", "Video", "Published"}
    start_idx, end_idx = APPENDED_ROWS[tab]
    rows = sheets_data[tab]
    assert len(rows) >= end_idx, f"Tab '{tab}' has {len(rows)} rows, expected at least {end_idx}"

    for r_idx in range(start_idx, end_idx + 1):
        row = rows[r_idx - 1]
        col_a = row[0].strip() if len(row) > 0 else ""
        col_d = row[3].strip() if len(row) > 3 else ""
        expected_id = f"#{r_idx}"
        assert col_a == expected_id, f"Tab '{tab}' Row {r_idx} Column A is '{col_a}', expected '{expected_id}'"
        assert col_d in valid_statuses, f"Tab '{tab}' Row {r_idx} Status is '{col_d}', expected one of {valid_statuses}"


@pytest.mark.parametrize("tab", QUIZ_TABS)
def test_appended_rows_gatekeeper1_spaced_pinyin(sheets_data, tab):
    """Verify that all words in the newly appended rows pass Gatekeeper 1 spaced pinyin validation."""
    start_idx, end_idx = APPENDED_ROWS[tab]
    rows = sheets_data[tab]

    for r_idx in range(start_idx, end_idx + 1):
        row = rows[r_idx - 1]
        for col_idx in range(4, min(9, len(row))):
            val = row[col_idx]
            parts = [p.strip() for p in val.split("|")]
            if tab in ["pinyin", "vocabCN"]:
                hz, py = parts[0], parts[1]
            elif tab == "vocabVN":
                hz, py = parts[2], parts[1]
            elif tab == "multilevels":
                hz, py = parts[0], parts[1]

            # Verify spaced pinyin
            if len(hz) > 1:
                assert " " in py, f"Tab '{tab}' Row {r_idx} word '{hz}' pinyin '{py}' missing spacing between syllables"

            valid, errs = PinyinLinguisticValidator.validate_pinyin(hz, py)
            assert valid, f"Tab '{tab}' Row {r_idx} pinyin validation failed for '{hz}' '{py}': {errs}"


@pytest.mark.parametrize("tab", QUIZ_TABS)
def test_appended_rows_metadata_and_injection_free(sheets_data, tab):
    """Verify that Column J has 3 platforms and no cells start with '='."""
    start_idx, end_idx = APPENDED_ROWS[tab]
    rows = sheets_data[tab]

    for r_idx in range(start_idx, end_idx + 1):
        row = rows[r_idx - 1]
        assert len(row) >= 10, f"Tab '{tab}' Row {r_idx} has fewer than 10 columns"
        meta = row[9]
        assert "YOUTUBE SHORTS" in meta, f"Tab '{tab}' Row {r_idx} Column J missing YOUTUBE SHORTS"
        assert "TIKTOK" in meta, f"Tab '{tab}' Row {r_idx} Column J missing TIKTOK"
        assert "FACEBOOK REELS" in meta, f"Tab '{tab}' Row {r_idx} Column J missing FACEBOOK REELS"

        for col_idx, cell in enumerate(row):
            assert not str(cell).startswith("="), f"Tab '{tab}' Row {r_idx} Col {col_idx} has formula injection: {cell}"


def test_multilevels_tier5_idiom_requirement(sheets_data):
    """Verify that multilevels appended rows have 4-character idioms/advanced phrases at Tier 5."""
    start_idx, end_idx = APPENDED_ROWS["multilevels"]
    rows = sheets_data["multilevels"]

    for r_idx in range(start_idx, end_idx + 1):
        row = rows[r_idx - 1]
        tier5_cell = row[8]  # Column I (Word 5 / Tier 5)
        hz = tier5_cell.split("|")[0].strip()
        assert len(hz) >= 3, f"Multilevels Row {r_idx} Tier 5 Hanzi '{hz}' has length {len(hz)} (< 3 chars required)"
