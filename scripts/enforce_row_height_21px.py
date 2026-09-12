#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enforces the strict 21px Row Height Invariant across all 4 quiz tabs
in the central Google Spreadsheet (pinyin, vocabCN, vocabVN, multilevels).
Equipped with self-healing randomized exponential backoff and quota-efficient batch querying.
"""

import os
import sys
import time
import random
import logging
from typing import List, Dict, Any, Optional, Callable
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

try:
    import gspread.exceptions
    GSPREAD_API_ERROR = gspread.exceptions.APIError
except ImportError:
    GSPREAD_API_ERROR = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [RowHeightEnforcer] %(message)s"
)
logger = logging.getLogger("RowHeightEnforcer")

SPREADSHEET_ID = "1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0"
SA_PATH = os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/google_sa/service_account.json")
QUIZ_TABS = ["pinyin", "vocabCN", "vocabVN", "multilevels"]
TARGET_ROW_HEIGHT_PX = 21


def get_sheets_service():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    env_json = os.getenv("GCP_SERVICE_ACCOUNT_KEY") or os.getenv("GCP_SERVICE_ACCOUNT_JSON") or os.getenv("SERVICE_ACCOUNT_JSON")
    if env_json and env_json.strip().startswith("{"):
        try:
            import json
            info = json.loads(env_json)
            creds = Credentials.from_service_account_info(info, scopes=scopes)
            return build("sheets", "v4", credentials=creds)
        except Exception:
            pass

    search_paths = [
        SA_PATH,
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pinyinquiz", "configs", "service_account.json"),
        os.path.expanduser("~/.config/gspread/service_account.json"),
    ]
    for p in search_paths:
        if p and os.path.exists(p) and os.path.getsize(p) > 10:
            creds = Credentials.from_service_account_file(p, scopes=scopes)
            return build("sheets", "v4", credentials=creds)

    raise FileNotFoundError(f"Service account not found at {SA_PATH}")


def execute_with_backoff(
    request_or_callable: Any,
    max_retries: int = 5,
    initial_delay: float = 2.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
) -> Any:
    """
    Executes a Google API request (or arbitrary callable) with exponential backoff and randomized jitter.
    Specifically catches and retries:
    - HTTP 429 (Rate Limit Exceeded / Quota Exceeded)
    - HTTP 500, 502, 503, 504 (Transient Server Errors)
    - Transient socket/network errors (ConnectionError, TimeoutError, OSError)
    """
    delay = initial_delay
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            if hasattr(request_or_callable, "execute"):
                try:
                    return request_or_callable.execute(num_retries=2)
                except TypeError:
                    return request_or_callable.execute()
            elif callable(request_or_callable):
                return request_or_callable()
            else:
                raise TypeError(f"Expected callable or googleapiclient HttpRequest, got {type(request_or_callable)}")
        except HttpError as err:
            last_err = err
            status_code = getattr(err.resp, "status", None) or getattr(err, "status_code", None)
            is_retryable = status_code in (429, 500, 502, 503, 504) or "Quota exceeded" in str(err) or "RATE_LIMIT_EXCEEDED" in str(err)
            if not is_retryable or attempt >= max_retries:
                logger.error(f"Google Sheets API call failed on attempt {attempt}/{max_retries}: {err}")
                raise

            sleep_time = min(delay, max_delay)
            if jitter:
                sleep_time *= (0.8 + 0.4 * random.random())
            logger.warning(
                f"[RateLimit/Transient] HTTP {status_code}. Retrying in {sleep_time:.2f}s "
                f"(attempt {attempt}/{max_retries})... Error: {err}"
            )
            time.sleep(sleep_time)
            delay *= backoff_factor
        except Exception as e:
            if GSPREAD_API_ERROR and isinstance(e, GSPREAD_API_ERROR):
                last_err = e
                resp = getattr(e, "response", None)
                status_code = getattr(resp, "status_code", None) if resp else None
                is_retryable = status_code in (429, 500, 502, 503, 504) or "RESOURCE_EXHAUSTED" in str(e) or "Quota exceeded" in str(e)
                if not is_retryable or attempt >= max_retries:
                    raise
                sleep_time = min(delay, max_delay)
                if jitter:
                    sleep_time *= (0.8 + 0.4 * random.random())
                logger.warning(
                    f"[RateLimit/Transient] GSpread Status {status_code}. Retrying in {sleep_time:.2f}s "
                    f"(attempt {attempt}/{max_retries})... Error: {e}"
                )
                time.sleep(sleep_time)
                delay *= backoff_factor
            elif isinstance(e, (ConnectionError, TimeoutError, OSError)):
                last_err = e
                if attempt >= max_retries:
                    logger.error(f"Network call failed on attempt {attempt}/{max_retries}: {e}")
                    raise
                sleep_time = min(delay, max_delay)
                if jitter:
                    sleep_time *= (0.8 + 0.4 * random.random())
                logger.warning(
                    f"[NetworkTransient] Retrying in {sleep_time:.2f}s (attempt {attempt}/{max_retries})... Error: {e}"
                )
                time.sleep(sleep_time)
                delay *= backoff_factor
            else:
                raise

    if last_err:
        raise last_err


def audit_and_enforce_row_height(
    target_height: int = TARGET_ROW_HEIGHT_PX,
    spreadsheet_id: str = SPREADSHEET_ID,
    service: Optional[Any] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Audits row heights across all quiz tabs in a single batch query and enforces target height.
    Consolidates metadata retrieval for all 4 quiz tabs into 1 single GET request to minimize quota usage.
    """
    if service is None:
        service = get_sheets_service()

    # 1. Fetch metadata for all 4 quiz tabs in a SINGLE batch query to minimize quota usage
    ranges = [f"{title}!A:A" for title in QUIZ_TABS]
    fields = "sheets(properties(title,sheetId,gridProperties/rowCount),data(rowMetadata(pixelSize)))"

    get_req = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        ranges=ranges,
        fields=fields
    )
    meta_res = execute_with_backoff(get_req)

    sheets = meta_res.get("sheets", [])
    results = {}
    requests = []

    for s in sheets:
        props = s.get("properties", {})
        title = props.get("title")
        if title in QUIZ_TABS:
            sheet_id = props.get("sheetId")
            row_count = props.get("gridProperties", {}).get("rowCount", 0)

            data_list = s.get("data", [])
            rows_meta = data_list[0].get("rowMetadata", []) if data_list else []

            non_target_count = sum(1 for r in rows_meta if r.get("pixelSize") != target_height)

            results[title] = {
                "sheet_id": sheet_id,
                "total_rows": row_count,
                "non_target_rows": non_target_count,
                "all_target": (non_target_count == 0)
            }

            if non_target_count > 0 or force:
                requests.append({
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": 0,
                            "endIndex": row_count
                        },
                        "properties": {
                            "pixelSize": target_height
                        },
                        "fields": "pixelSize"
                    }
                })

    if requests:
        logger.info(f"Applying {target_height}px row height enforcement across {len(requests)} quiz tabs...")
        body = {"requests": requests}
        batch_req = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body)
        execute_with_backoff(batch_req)
        logger.info(f"✓ {target_height}px row height invariant successfully enforced on all tabs!")

    return results


class RowHeightEnforcer:
    """Class wrapper adhering to PROJECT.md and scripts/append_5_ideas_all_tabs.py interface."""
    def __init__(self, target_height: int = TARGET_ROW_HEIGHT_PX, spreadsheet_id: str = SPREADSHEET_ID):
        self.target_height = target_height
        self.spreadsheet_id = spreadsheet_id
        self.service = None

    def enforce_all(self, force: bool = False) -> Dict[str, Any]:
        return audit_and_enforce_row_height(
            target_height=self.target_height,
            spreadsheet_id=self.spreadsheet_id,
            service=self.service,
            force=force
        )

    def audit(self) -> Dict[str, Any]:
        return audit_and_enforce_row_height(
            target_height=self.target_height,
            spreadsheet_id=self.spreadsheet_id,
            service=self.service,
            force=False
        )


def enforce_all_tabs_21px(
    service: Optional[Any] = None, spreadsheet_id: str = SPREADSHEET_ID
) -> Dict[str, Any]:
    """
    Enforces 21px row height on all rows across all 4 quiz tabs.
    Adheres to PROJECT.md interface contract.
    """
    return audit_and_enforce_row_height(
        target_height=TARGET_ROW_HEIGHT_PX,
        spreadsheet_id=spreadsheet_id,
        service=service,
        force=True
    )


__all__ = [
    "RowHeightEnforcer",
    "audit_and_enforce_row_height",
    "enforce_all_tabs_21px",
    "execute_with_backoff",
    "SPREADSHEET_ID",
    "TARGET_ROW_HEIGHT_PX",
    "QUIZ_TABS",
    "get_sheets_service"
]


def main():
    logger.info("=== Checking and Enforcing 21px Row Height Invariant ===")
    res = audit_and_enforce_row_height(TARGET_ROW_HEIGHT_PX)
    print("\n" + "=" * 60)
    print("  GOOGLE SHEETS ROW HEIGHT INVARIANT REPORT (TARGET: 21px)")
    print("=" * 60)
    total_rows = sum(info["total_rows"] for info in res.values())
    total_target = sum(info["total_rows"] - info["non_target_rows"] for info in res.values())
    for tab, info in res.items():
        status = "PASSED (100% 21px)" if info["all_target"] else "ENFORCED TO 21px"
        print(f"  • Tab: {tab:<14} | Total Rows: {info['total_rows']:<5} | Status: {status}")
    print("=" * 60)
    print(f"Summary: {total_target}/{total_rows} rows 21px invariant verified.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
