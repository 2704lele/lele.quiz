#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audits and reconciles 1:1 Row-ID Parity across Google Sheets tabs for Lê Lê Học Tiếng Trung Quiz v2.0.
Ensures physical row k in Google Sheets has exactly '#k' in Column A.
Safely repairs gaps, skips, duplicates, and out-of-order IDs via Google Sheets API v4 batchUpdate.
Equipped with exponential backoff, jitter, and quota-efficient batch queries.
"""

import os
import sys
import argparse
import logging
from typing import Dict, Any, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.enforce_row_height_21px import (
    SPREADSHEET_ID,
    QUIZ_TABS,
    get_sheets_service,
    execute_with_backoff,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [RowIdReconciler] %(message)s"
)
logger = logging.getLogger("RowIdReconciler")

TAB_NAME_MAP = {
    "all": "all",
    "pinyin": "pinyin",
    "pinyinquiz": "pinyin",
    "vocabcn": "vocabCN",
    "vocabcnquiz": "vocabCN",
    "vocabvn": "vocabVN",
    "vocabvnquiz": "vocabVN",
    "multilevels": "multilevels",
    "multilevelsquiz": "multilevels",
    "ml": "multilevels",
}


def normalize_tab_name(tab: str) -> str:
    """Normalizes case-insensitive input or pipeline alias to canonical tab name."""
    clean = (tab or "").strip().lower()
    if clean in TAB_NAME_MAP:
        return TAB_NAME_MAP[clean]
    for canon in QUIZ_TABS:
        if canon.lower() == clean:
            return canon
    return tab.strip()


def reconcile_tab_row_ids(
    service: Optional[Any] = None,
    spreadsheet_id: str = SPREADSHEET_ID,
    tab: str = "all",
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Ensures row k has '#k' for all data rows (Row 2 onwards) in the given tab.
    Adheres strictly to PROJECT.md interface contract:
    reconcile_tab_row_ids(service, spreadsheet_id: str, tab: str, dry_run: bool = False) -> Dict[str, Any]

    If tab == 'all', reconciles all 4 quiz tabs and aggregates the results.
    """
    canon_tab = normalize_tab_name(tab)

    if canon_tab == "all":
        return reconcile_all_tabs(service=service, spreadsheet_id=spreadsheet_id, dry_run=dry_run)

    if service is None:
        service = get_sheets_service()

    range_name = f"{canon_tab}!A1:P"
    get_req = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    )
    res = execute_with_backoff(get_req)
    vals = res.get("values", [])

    updates = []
    mismatches = 0
    mismatch_details = []

    for idx, r in enumerate(vals[1:], start=2):
        # Ignore empty trailing rows
        if not any(str(c).strip() for c in r):
            continue

        raw_val = str(r[0]).strip() if len(r) > 0 else ""
        clean_id = raw_val.replace("#", "").strip()
        expected_id = f"#{idx}"

        # Match check: must start with '#' and clean number must match physical row index
        is_match = (
            raw_val.startswith("#")
            and clean_id.isdigit()
            and int(clean_id) == idx
            and raw_val == expected_id
        )

        if not is_match:
            mismatches += 1
            mismatch_details.append({
                "row": idx,
                "current_id": raw_val,
                "expected_id": expected_id
            })
            updates.append({
                "range": f"{canon_tab}!A{idx}",
                "values": [[expected_id]]
            })

    applied = False
    if updates and not dry_run:
        logger.info(f"Applying {len(updates)} row ID corrections on tab '{canon_tab}'...")
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": updates
        }
        batch_req = service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        )
        execute_with_backoff(batch_req)
        applied = True
        logger.info(f"✓ Tab '{canon_tab}': {len(updates)} row IDs successfully repaired to 1:1 parity!")

    return {
        "tab": canon_tab,
        "total_rows": max(0, len(vals) - 1),
        "mismatches": mismatches,
        "applied": applied,
        "dry_run": dry_run,
        "details": mismatch_details
    }


def reconcile_all_tabs(
    service: Optional[Any] = None,
    spreadsheet_id: str = SPREADSHEET_ID,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Reconciles row ID parity across all 4 quiz tabs.
    Returns aggregated summary dict with tab breakdown.
    """
    if service is None:
        service = get_sheets_service()

    tab_results = {}
    total_rows = 0
    total_mismatches = 0
    any_applied = False

    for tab in QUIZ_TABS:
        res = reconcile_tab_row_ids(
            service=service,
            spreadsheet_id=spreadsheet_id,
            tab=tab,
            dry_run=dry_run
        )
        tab_results[tab] = res
        total_rows += res.get("total_rows", 0)
        total_mismatches += res.get("mismatches", 0)
        if res.get("applied", False):
            any_applied = True

    return {
        "tab": "all",
        "total_rows": total_rows,
        "mismatches": total_mismatches,
        "applied": any_applied,
        "dry_run": dry_run,
        "tabs": tab_results
    }


def print_reconcile_report(result: Dict[str, Any]):
    """Prints a clear, structured reconciliation report."""
    print("\n" + "=" * 65)
    mode_str = "DRY-RUN (AUDIT ONLY)" if result.get("dry_run") else "APPLIED (MODIFIED)"
    print(f"  GOOGLE SHEETS 1:1 ROW-ID PARITY REPORT [{mode_str}]")
    print("=" * 65)

    if result.get("tab") == "all":
        tabs_dict = result.get("tabs", {})
        for tab_name, info in tabs_dict.items():
            mismatches = info.get("mismatches", 0)
            total = info.get("total_rows", 0)
            status = "PASSED (100% Parity)" if mismatches == 0 else f"MISMATCHES: {mismatches} rows"
            if info.get("applied"):
                status = f"REPAIRED: {mismatches} rows fixed"
            print(f"  • Tab: {tab_name:<14} | Total Rows: {total:<5} | Status: {status}")
            if mismatches > 0 and info.get("details"):
                for d in info["details"][:5]:
                    print(f"      - Row {d['row']}: current '{d['current_id']}' -> expected '{d['expected_id']}'")
                if len(info["details"]) > 5:
                    print(f"      ... and {len(info['details']) - 5} more mismatched rows")
        print("=" * 65)
        print(f"Summary: Total {result.get('total_rows', 0)} rows audited across 4 tabs. "
              f"Mismatches: {result.get('mismatches', 0)}.")
    else:
        tab_name = result.get("tab")
        mismatches = result.get("mismatches", 0)
        total = result.get("total_rows", 0)
        status = "PASSED (100% Parity)" if mismatches == 0 else f"MISMATCHES: {mismatches} rows"
        if result.get("applied"):
            status = f"REPAIRED: {mismatches} rows fixed"
        print(f"  • Tab: {tab_name:<14} | Total Rows: {total:<5} | Status: {status}")
        if mismatches > 0 and result.get("details"):
            for d in result["details"][:10]:
                print(f"      - Row {d['row']}: current '{d['current_id']}' -> expected '{d['expected_id']}'")
            if len(result["details"]) > 10:
                print(f"      ... and {len(result['details']) - 10} more mismatched rows")
        print("=" * 65)

    if result.get("dry_run") and result.get("mismatches", 0) > 0:
        print("NOTE: Running in DRY-RUN mode. No changes were written to Google Sheets.")
        print("      Run with '--apply' to repair mismatched row IDs.")
    print("=" * 65 + "\n")


__all__ = [
    "reconcile_tab_row_ids",
    "reconcile_all_tabs",
    "normalize_tab_name",
    "SPREADSHEET_ID",
    "QUIZ_TABS"
]


def main():
    parser = argparse.ArgumentParser(
        description="Audit and reconcile 1:1 Row-ID parity across Google Sheets tabs."
    )
    parser.add_argument(
        "--tab",
        default="all",
        help="Target worksheet: 'all', 'pinyin', 'vocabCN', 'vocabVN', or 'multilevels' (default: 'all')"
    )
    parser.add_argument(
        "--spreadsheet-id",
        default=SPREADSHEET_ID,
        help=f"Central Google Spreadsheet ID (default: {SPREADSHEET_ID})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Audit only; do not write changes to Google Sheets (default if --apply omitted)"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Execute batchUpdate to repair mismatched row IDs"
    )

    args = parser.parse_args()

    # If --apply is explicitly specified, dry_run is False; otherwise dry_run is True
    dry_run = not args.apply

    logger.info(f"Starting Row-ID Reconciliation (Tab: {args.tab}, Mode: {'DRY-RUN' if dry_run else 'APPLY'})...")
    service = get_sheets_service()
    res = reconcile_tab_row_ids(
        service=service,
        spreadsheet_id=args.spreadsheet_id,
        tab=args.tab,
        dry_run=dry_run
    )
    print_reconcile_report(res)


if __name__ == "__main__":
    main()
