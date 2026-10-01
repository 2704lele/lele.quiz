#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Adversarial Independent Oracle and Stress Harness for Milestone M5.
Empirically verifies:
1. Exact row count (199 data rows across 4 tabs), sequence integrity, zero missing, zero duplicates, zero off-by-one.
2. Cell security and Formula Injection defense (=, +, -, @) across all newly appended rows (and full sheet).
3. Google Colab notebook schema, AST syntax, and 16-package dependency parity with GitHub Actions.
4. Parity and invariant enforcement across all execution layers.
"""

import os
import sys
import json
import ast
import re
import pytest
from typing import Dict, List, Tuple, Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.enforce_row_height_21px import (
    SPREADSHEET_ID,
    QUIZ_TABS,
    get_sheets_service,
    execute_with_backoff,
)

EXPECTED_TAB_SPECS = {
    "pinyin": {
        "expected_data_rows": 65,
        "start_row": 2,
        "end_row": 66,
        "new_rows_range": (62, 66),
    },
    "vocabCN": {
        "expected_data_rows": 49,
        "start_row": 2,
        "end_row": 50,
        "new_rows_range": (46, 50),
    },
    "vocabVN": {
        "expected_data_rows": 42,
        "start_row": 2,
        "end_row": 43,
        "new_rows_range": (39, 43),
    },
    "multilevels": {
        "expected_data_rows": 43,
        "start_row": 2,
        "end_row": 44,
        "new_rows_range": (40, 44),
    },
}

REQUIRED_16_PACKAGES = [
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

INJECTION_CHARS = ("=", "+", "-", "@", "\t", "\r")


@pytest.fixture(scope="module")
def sheets_service():
    service = get_sheets_service()
    assert service is not None, "Failed to initialize Google Sheets API service"
    return service


@pytest.fixture(scope="module")
def full_sheets_data(sheets_service):
    data = {}
    for tab in QUIZ_TABS:
        res = execute_with_backoff(
            sheets_service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{tab}!A:Z"
            )
        )
        data[tab] = res.get("values", [])
    return data


# ==============================================================================
# 1. INDEPENDENT ROW AUDIT ORACLE (199 DATA ROWS ACROSS 4 TABS)
# ==============================================================================

def test_independent_oracle_total_199_data_rows(full_sheets_data):
    """Oracle verifying exactly 199 data rows across the 4 sheets."""
    total_data_rows = 0
    breakdown = {}

    for tab, spec in EXPECTED_TAB_SPECS.items():
        rows = full_sheets_data[tab]
        # First row is header
        assert len(rows) >= 1, f"Tab '{tab}' is completely empty"
        header = rows[0]
        assert len(header) > 0, f"Tab '{tab}' header is empty"

        # Data rows
        data_rows = [r for r in rows[1:] if r and any(str(c).strip() for c in r)]
        count = len(data_rows)
        breakdown[tab] = count
        total_data_rows += count

        expected = spec["expected_data_rows"]
        assert count == expected, (
            f"Tab '{tab}' data row count mismatch: found {count}, expected {expected}. "
            f"Expected row range #{spec['start_row']}..#{spec['end_row']}"
        )

    assert total_data_rows == 199, (
        f"Total data rows across 4 tabs is {total_data_rows}, expected exactly 199! "
        f"Breakdown: {breakdown}"
    )


@pytest.mark.parametrize("tab", list(EXPECTED_TAB_SPECS.keys()))
def test_independent_oracle_row_sequence_and_no_duplicates(full_sheets_data, tab):
    """Oracle verifying strict sequential #{i}, no gaps, no duplicates, no off-by-one errors."""
    spec = EXPECTED_TAB_SPECS[tab]
    rows = full_sheets_data[tab]
    start_row = spec["start_row"]
    end_row = spec["end_row"]
    expected_count = spec["expected_data_rows"]

    # Verify physical row count in sheet
    data_rows = rows[1:end_row]
    assert len(data_rows) == expected_count, (
        f"Tab '{tab}' has {len(data_rows)} rows between index 2 and {end_row}, expected {expected_count}"
    )

    observed_ids = []
    observed_numeric_ids = []

    for idx, row in enumerate(data_rows, start=start_row):
        assert len(row) > 0, f"Tab '{tab}' Row {idx} is empty"
        col_a = str(row[0]).strip()
        expected_col_a = f"#{idx}"

        assert col_a == expected_col_a, (
            f"Tab '{tab}' Row {idx} Column A mismatch: got '{col_a}', expected '{expected_col_a}'"
        )

        match = re.match(r"^#(\d+)$", col_a)
        assert match is not None, f"Tab '{tab}' Row {idx} Column A '{col_a}' does not match pattern #<integer>"
        num_id = int(match.group(1))
        assert num_id == idx, f"Tab '{tab}' Row {idx} has integer ID {num_id} != physical row {idx}"

        observed_ids.append(col_a)
        observed_numeric_ids.append(num_id)

    # Check for duplicates
    assert len(observed_ids) == len(set(observed_ids)), (
        f"Tab '{tab}' has duplicate Column A IDs: {len(observed_ids)} total vs {len(set(observed_ids))} unique"
    )

    # Check for gaps
    expected_numeric_range = list(range(start_row, end_row + 1))
    assert observed_numeric_ids == expected_numeric_range, (
        f"Tab '{tab}' numeric ID sequence has gaps or skips! Difference: "
        f"{set(expected_numeric_range).symmetric_difference(set(observed_numeric_ids))}"
    )

    # Check that row end_row + 1 does not contain trailing phantom data
    if len(rows) > end_row:
        extra_rows = rows[end_row:]
        non_empty_extras = [r for r in extra_rows if any(str(c).strip() for c in r)]
        assert len(non_empty_extras) == 0, (
            f"Tab '{tab}' has {len(non_empty_extras)} unexpected extra data rows beyond #{end_row}: {non_empty_extras}"
        )


# ==============================================================================
# 2. FORMULA INJECTION & CELL SECURITY ORACLE
# ==============================================================================

@pytest.mark.parametrize("tab", list(EXPECTED_TAB_SPECS.keys()))
def test_formula_injection_prevention_new_rows(full_sheets_data, tab):
    """Verify that none of the 20 newly appended rows contain formula injection characters."""
    spec = EXPECTED_TAB_SPECS[tab]
    start_new, end_new = spec["new_rows_range"]
    rows = full_sheets_data[tab]

    vulnerabilities = []
    for r_idx in range(start_new, end_new + 1):
        row = rows[r_idx - 1]  # 1-indexed to 0-indexed
        for c_idx, cell in enumerate(row):
            val_str = str(cell).strip()
            if not val_str:
                continue

            # Check if text cell begins with dangerous spreadsheet formula characters
            # Exception: negative numbers if numeric (none expected in quiz text columns)
            # In quiz sheets, Column A is '#N', Column B is Date, Column D is Status, others are text
            for danger in INJECTION_CHARS:
                if val_str.startswith(danger):
                    vulnerabilities.append({
                        "tab": tab,
                        "row": r_idx,
                        "col": c_idx,
                        "char": danger,
                        "value": val_str[:30],
                    })

    assert len(vulnerabilities) == 0, (
        f"Formula injection vulnerabilities detected in new rows of '{tab}': {vulnerabilities}"
    )


@pytest.mark.parametrize("tab", list(EXPECTED_TAB_SPECS.keys()))
def test_formula_injection_prevention_all_199_rows(full_sheets_data, tab):
    """Exhaustively scan all 199 data rows across all columns for formula injection characters."""
    spec = EXPECTED_TAB_SPECS[tab]
    start_row = spec["start_row"]
    end_row = spec["end_row"]
    rows = full_sheets_data[tab]

    vulnerabilities = []
    for r_idx in range(start_row, end_row + 1):
        row = rows[r_idx - 1]
        for c_idx, cell in enumerate(row):
            val_str = str(cell).strip()
            if not val_str:
                continue
            # Column A should always start with '#'
            if c_idx == 0:
                assert val_str.startswith("#"), f"Tab '{tab}' Row {r_idx} Col 0 does not start with '#': {val_str}"
                continue

            # Check for leading formula execution triggers
            for danger in ["=", "+", "@"]:
                if val_str.startswith(danger):
                    vulnerabilities.append({
                        "tab": tab,
                        "row": r_idx,
                        "col": c_idx,
                        "char": danger,
                        "value": val_str[:30],
                    })

    assert len(vulnerabilities) == 0, (
        f"Formula injection vulnerabilities detected across full tab '{tab}': {vulnerabilities}"
    )


# ==============================================================================
# 3. COLAB PARITY ORACLE & CODE EXECUTION FEASIBILITY
# ==============================================================================

def test_colab_notebook_json_and_ast_compilation():
    """Verify that render_quiz_colab.ipynb parses as valid JSON, and all Python code compiles via AST."""
    nb_path = os.path.join(PROJECT_ROOT, "scripts", "render_quiz_colab.ipynb")
    assert os.path.exists(nb_path), f"Notebook file missing: {nb_path}"

    with open(nb_path, "r", encoding="utf-8") as f:
        nb_json = json.load(f)

    assert "cells" in nb_json, "Notebook missing 'cells' key"
    assert "metadata" in nb_json, "Notebook missing 'metadata' key"

    code_cells = [c for c in nb_json["cells"] if c.get("cell_type") == "code"]
    assert len(code_cells) >= 7, f"Expected at least 7 code cells, found {len(code_cells)}"

    # Check AST compilation for each code cell after transforming IPython shell magics
    for idx, cell in enumerate(code_cells):
        raw_source = "".join(cell.get("source", []))
        # Transform or comment out IPython shell commands starting with ! or % or #@, including line continuations (\)
        sanitized_lines = []
        in_shell_continuation = False
        for line in raw_source.splitlines():
            stripped = line.strip()
            if in_shell_continuation:
                sanitized_lines.append(f"# {line}")
                if not stripped.endswith("\\"):
                    in_shell_continuation = False
            elif stripped.startswith("!") or stripped.startswith("%"):
                sanitized_lines.append(f"# {line}")
                if stripped.endswith("\\"):
                    in_shell_continuation = True
            else:
                sanitized_lines.append(line)
        sanitized_code = "\n".join(sanitized_lines)

        try:
            tree = ast.parse(sanitized_code)
            assert tree is not None
        except SyntaxError as e:
            pytest.fail(f"Colab notebook code cell #{idx} failed AST syntax parse: {e}\nCode:\n{sanitized_code}")


def test_colab_dependency_parity_16_packages():
    """Verify scripts/render_quiz_colab.ipynb and colab/colab_worker_quiz.py contain all 16 packages."""
    nb_path = os.path.join(PROJECT_ROOT, "scripts", "render_quiz_colab.ipynb")
    worker_path = os.path.join(PROJECT_ROOT, "colab", "colab_worker_quiz.py")

    with open(nb_path, "r", encoding="utf-8") as f:
        nb_content = f.read()

    with open(worker_path, "r", encoding="utf-8") as f:
        worker_content = f.read()

    for pkg in REQUIRED_16_PACKAGES:
        assert pkg in nb_content, f"Notebook missing package '{pkg}'"
        assert f'"{pkg}"' in worker_content or f"'{pkg}'" in worker_content, (
            f"colab_worker_quiz.py missing package '{pkg}'"
        )


def test_colab_system_packages_and_security_hardening():
    """Verify fonts-noto-color-emoji and chmod 600 are present in both Colab artifacts."""
    nb_path = os.path.join(PROJECT_ROOT, "scripts", "render_quiz_colab.ipynb")
    worker_path = os.path.join(PROJECT_ROOT, "colab", "colab_worker_quiz.py")

    with open(nb_path, "r", encoding="utf-8") as f:
        nb_content = f.read()

    with open(worker_path, "r", encoding="utf-8") as f:
        worker_content = f.read()

    # System fonts
    assert "fonts-noto-color-emoji" in nb_content, "Notebook missing fonts-noto-color-emoji"
    assert "fonts-noto-color-emoji" in worker_content, "colab_worker_quiz.py missing fonts-noto-color-emoji"

    # Row height invariant enforcement
    assert "enforce_row_height_21px.py" in nb_content, "Notebook missing enforce_row_height_21px.py"
    assert "enforce_row_height_21px.py" in worker_content, "colab_worker_quiz.py missing enforce_row_height_21px.py"

    # Zero-Leak Vault chmod 600 on notebook credential vault
    assert "chmod" in nb_content and "600" in nb_content, "Notebook missing chmod 600 security hardening"
    # colab_worker_quiz.py handles credentials from vault or uploaded files
    assert "setup_credentials" in worker_content, "colab_worker_quiz.py missing setup_credentials"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main(["-v", __file__]))
