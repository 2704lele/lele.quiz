import os
import sys
import json
import re
import yaml
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.enforce_row_height_21px import (
    get_sheets_service,
    SPREADSHEET_ID,
    QUIZ_TABS,
    TARGET_ROW_HEIGHT_PX,
    execute_with_backoff,
)
from scripts.linguistic_qc import (
    ALL_TONE_VOWELS,
    VALID_NEUTRAL_SYLLABLES,
    strip_tone_marks,
    get_expected_tone_position,
)

APPENDED_ROWS = {
    "pinyin": (62, 66),
    "vocabCN": (46, 50),
    "vocabVN": (39, 43),
    "multilevels": (40, 44),
}

REQUIRED_16_DEPENDENCIES = [
    "manim",
    "edge-tts",
    "opencv-python-headless",
    "opencc-python-reimplemented",
    "gspread",
    "google-api-python-client",
    "google-auth",
    "google-auth-oauthlib",
    "pypinyin",
    "requests",
    "rich",
    "scipy",
    "numpy",
    "Pillow",
    "pydub",
    "pyyaml",
]


@pytest.fixture(scope="module")
def sheets_service():
    return get_sheets_service()


@pytest.fixture(scope="module")
def sheets_data(sheets_service):
    data = {}
    for tab in QUIZ_TABS:
        res = execute_with_backoff(
            sheets_service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{tab}!A:P"
            )
        )
        data[tab] = res.get("values", [])
    return data


def test_row_id_parity_all_199_rows(sheets_data):
    """Assert for every data row N >= 2: Column A == f'#{N}'. Exactly 199 rows total."""
    total_data_rows = 0
    mismatches = []

    for tab in QUIZ_TABS:
        rows = sheets_data[tab]
        data_rows = rows[1:] if len(rows) > 1 else []
        total_data_rows += len(data_rows)

        for idx, row in enumerate(data_rows, start=2):
            col_a = row[0].strip() if len(row) > 0 else ""
            expected_id = f"#{idx}"
            if col_a != expected_id:
                mismatches.append((tab, idx, col_a, expected_id))

    assert len(mismatches) == 0, f"Found {len(mismatches)} Column A row-ID mismatches: {mismatches}"
    assert total_data_rows == 199, f"Expected 199 data rows across 4 tabs, found {total_data_rows}"


def test_row_height_21px_all_403_rows(sheets_service):
    """Assert for 100% of rows: pixelSize == 21 across all 403 allocated rows."""
    ranges = [f"{title}!A:A" for title in QUIZ_TABS]
    fields = "sheets(properties(title,sheetId,gridProperties/rowCount),data(rowMetadata(pixelSize)))"

    get_req = sheets_service.spreadsheets().get(
        spreadsheetId=SPREADSHEET_ID,
        ranges=ranges,
        fields=fields
    )
    meta_res = execute_with_backoff(get_req)

    total_allocated_rows = 0
    deviations = []

    for s in meta_res.get("sheets", []):
        props = s.get("properties", {})
        title = props.get("title")
        if title in QUIZ_TABS:
            row_count = props.get("gridProperties", {}).get("rowCount", 0)
            total_allocated_rows += row_count

            data_list = s.get("data", [])
            rows_meta = data_list[0].get("rowMetadata", []) if data_list else []
            for r_idx, r_meta in enumerate(rows_meta):
                ps = r_meta.get("pixelSize")
                if ps != TARGET_ROW_HEIGHT_PX:
                    deviations.append((title, r_idx, ps))

    assert len(deviations) == 0, f"Found {len(deviations)} rows deviating from {TARGET_ROW_HEIGHT_PX}px: {deviations}"
    assert total_allocated_rows == 403, f"Expected 403 allocated rows across 4 tabs, got {total_allocated_rows}"


def test_newly_appended_20_rows_status_and_ids(sheets_data):
    """Assert for all 20 newly appended rows: status is 'Pending', and Column A ID matches physical row index."""
    total_appended = 0
    for tab, (start_idx, end_idx) in APPENDED_ROWS.items():
        rows = sheets_data[tab]
        for r_idx in range(start_idx, end_idx + 1):
            row = rows[r_idx - 1]
            col_a = row[0].strip() if len(row) > 0 else ""
            col_d = row[3].strip() if len(row) > 3 else ""

            assert col_a == f"#{r_idx}", f"Tab '{tab}' Row {r_idx} Column A '{col_a}' != '#{r_idx}'"
            assert col_d == "Pending", f"Tab '{tab}' Row {r_idx} Column D '{col_d}' != 'Pending'"
            total_appended += 1

    assert total_appended == 20, f"Expected exactly 20 appended rows, verified {total_appended}"


def test_linguistic_qc_spaced_pinyin_and_tones(sheets_data):
    """
    Stress-test linguistic QC on all 20 newly appended rows (100 words):
    - Verify spaced pinyin (e.g. 'mǐ fàn'). Ensure no unspaced compounds like 'mǐfàn' exist.
    - Verify tone mark positioning conforms to GB/T 16159-2012.
    - Verify Tier 5 in multilevels has Hanzi length >= 3 (4-character Chengyu).
    """
    chinese_regex = re.compile(r"[\u4e00-\u9fff]")
    total_words_tested = 0

    for tab, (start_idx, end_idx) in APPENDED_ROWS.items():
        rows = sheets_data[tab]
        for r_idx in range(start_idx, end_idx + 1):
            row = rows[r_idx - 1]

            # Columns E through I (indexes 4 through 8)
            for col_idx in range(4, 9):
                val = row[col_idx] if len(row) > col_idx else ""
                assert val, f"Tab '{tab}' Row {r_idx} Col {col_idx} is empty"

                parts = [p.strip() for p in val.split("|")]
                if tab == "vocabVN":
                    if len(parts) >= 3 and chinese_regex.search(parts[2]) and not chinese_regex.search(parts[0]):
                        hanzi = parts[2]
                        pinyin = parts[1]
                    else:
                        hanzi = parts[0]
                        pinyin = parts[1] if len(parts) > 1 else ""
                else:
                    hanzi = parts[0]
                    pinyin = parts[1] if len(parts) > 1 else ""

                total_words_tested += 1
                hz_chars = [c for c in hanzi if "\u4e00" <= c <= "\u9fff"]
                py_syls = pinyin.split()

                # 1. Spaced Pinyin: Compound words must not be unspaced (e.g., 'mǐfàn' is forbidden)
                is_erhua = hanzi.endswith("儿") and len(py_syls) == len(hz_chars) - 1 and py_syls[-1].endswith("r")
                if len(hz_chars) > 1 and not is_erhua:
                    assert len(py_syls) > 1, f"Unspaced compound found in {tab} Row {r_idx}: Hanzi='{hanzi}', Pinyin='{pinyin}'"
                    assert len(py_syls) == len(hz_chars), (
                        f"Syllable count mismatch in {tab} Row {r_idx}: Hanzi='{hanzi}' ({len(hz_chars)}) vs Pinyin='{pinyin}' ({len(py_syls)})"
                    )

                # 2. Tone mark placement per GB/T 16159-2012
                for syl in py_syls:
                    syl_clean = re.sub(r"[^a-zA-Zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü]", "", syl)
                    tone_chars = [c for c in syl_clean if c in ALL_TONE_VOWELS]
                    assert len(tone_chars) <= 1, f"Multiple tone vowels in syllable '{syl}' (Tab {tab} Row {r_idx})"
                    if len(tone_chars) == 1:
                        tone_pos = syl_clean.index(tone_chars[0])
                        plain = strip_tone_marks(syl_clean).lower()
                        expected_pos = get_expected_tone_position(plain)
                        assert tone_pos == expected_pos, (
                            f"Tone mark misplaced in '{syl}' (pos {tone_pos}, expected {expected_pos} in '{plain}')"
                        )
                    else:
                        plain = strip_tone_marks(syl_clean).lower()
                        assert plain in VALID_NEUTRAL_SYLLABLES or plain.endswith("r"), (
                            f"Invalid toneless syllable '{syl}' not in neutral tone dictionary"
                        )

                # 3. Multilevels Tier 5 length >= 3
                if tab == "multilevels" and col_idx == 8:
                    assert len(hz_chars) >= 3, (
                        f"Multilevels Tier 5 word '{hanzi}' in Row {r_idx} must have >= 3 characters (Chengyu)"
                    )

    assert total_words_tested == 100, f"Expected 100 words tested across 20 rows, got {total_words_tested}"


def test_colab_notebook_structure_and_dependencies():
    """Verify scripts/render_quiz_colab.ipynb is valid JSON, nbformat v4, and has all 16 required dependencies."""
    colab_path = os.path.join(PROJECT_ROOT, "scripts", "render_quiz_colab.ipynb")
    assert os.path.exists(colab_path), f"Colab notebook missing: {colab_path}"

    with open(colab_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    assert nb.get("nbformat") == 4, f"Expected nbformat 4, got {nb.get('nbformat')}"
    assert len(nb.get("cells", [])) > 0, "Colab notebook has no cells"

    all_code = "\n".join(
        "".join(c.get("source", []))
        for c in nb.get("cells", [])
        if c.get("cell_type") == "code"
    )

    for pkg in REQUIRED_16_DEPENDENCIES:
        assert pkg.lower() in all_code.lower(), f"Colab notebook missing required dependency: {pkg}"


def test_workflow_02_dependency_parity():
    """Verify workflow 02 contains all 16 required dependencies in pip install."""
    wf_path = os.path.join(PROJECT_ROOT, ".github", "workflows", "02_quiz_video_rendering_and_qc.yml")
    assert os.path.exists(wf_path), f"Workflow 02 missing: {wf_path}"

    with open(wf_path, "r", encoding="utf-8") as f:
        content = f.read()

    for pkg in REQUIRED_16_DEPENDENCIES:
        assert pkg.lower() in content.lower(), f"Workflow 02 missing required dependency: {pkg}"
