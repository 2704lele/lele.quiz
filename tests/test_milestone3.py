import os
import sys
import re
import json
import time
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import gspread
from google.oauth2.service_account import Credentials as SACredentials
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build

CANONICAL_FOLDERS = {
    "pinyin": "1f2mFUgpz_pYn3y9HqeHyOG9DzPMVH9QY",
    "vocabCN": "1eI7I4jQqGBjD7MC_NXJ4zwFANxrcZM1E",
    "vocabVN": "1VPqs9h4LLmmmXWKDGWoAz1fUCylVLK2H",
    "multilevels": "17xOkiW-XOWRDK2CCwNEl_rlf1rGKqKXm"
}

TARGET_ROWS = {
    "pinyin": list(range(55, 61)),       # 6 rows: #54-#59
    "vocabCN": list(range(41, 46)),      # 5 rows: #40-#44
    "vocabVN": list(range(34, 39)),      # 5 rows: #33-#37
    "multilevels": list(range(35, 40))   # 5 rows: #34-#38
}

SPREADSHEET_ID = "1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0"


@pytest.fixture(scope="module")
def gsheet_data():
    """Fetch all 4 tabs once with retry backoff and cache in memory."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    sa_path = os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/google_sa/service_account.json")
    creds = SACredentials.from_service_account_file(sa_path, scopes=scope)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SPREADSHEET_ID)

    data = {}
    for tab in CANONICAL_FOLDERS.keys():
        for attempt in range(1, 5):
            try:
                ws = sh.worksheet(tab)
                data[tab] = ws.get_all_records()
                break
            except Exception as e:
                if attempt == 4:
                    raise
                time.sleep(3 * attempt)
    return data


@pytest.fixture(scope="module")
def gdrive_service():
    user_oauth_path = os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/google_oauth/user_oauth2.json")
    with open(user_oauth_path) as f:
        odata = json.load(f)
    u_creds = UserCredentials(
        token=None,
        refresh_token=odata["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=odata["client_id"],
        client_secret=odata["client_secret"]
    )
    return build("drive", "v3", credentials=u_creds)


def test_all_tabs_have_zero_pending(gsheet_data):
    """Verify that there are exactly 0 pending rows across all 4 quiz tabs."""
    total_pending = 0
    pending_details = []

    for tab_name, rows in gsheet_data.items():
        for idx, r in enumerate(rows, start=2):
            st = str(r.get("Status", "")).strip().lower()
            if st == "pending":
                total_pending += 1
                pending_details.append(f"{tab_name} row {idx} (#{r.get('#')})")

    assert total_pending == 0, f"Found {total_pending} pending row(s): {', '.join(pending_details)}"


@pytest.mark.parametrize("tab_name", ["pinyin", "vocabCN", "vocabVN", "multilevels"])
def test_milestone3_rows_status_ready_and_qc(gsheet_data, tab_name):
    """Verify each target row in milestone 3 is marked 'Ready' with QC pass note in Column P."""
    all_rows = gsheet_data[tab_name]

    for r_idx in TARGET_ROWS[tab_name]:
        row_dict = all_rows[r_idx - 2]
        status = row_dict.get("Status", "").strip()
        notes = row_dict.get("Notes", "").strip()
        batch_id = row_dict.get("#", f"row_{r_idx}")

        assert status == "Ready", f"[{tab_name}] Row {r_idx} ({batch_id}) has status '{status}', expected 'Ready'"
        assert "Auto-QC" in notes or "QC" in notes, f"[{tab_name}] Row {r_idx} ({batch_id}) missing QC pass note: '{notes}'"


@pytest.mark.parametrize("tab_name", ["pinyin", "vocabCN", "vocabVN", "multilevels"])
def test_milestone3_rows_gdrive_urls_and_canonical_folder(gsheet_data, gdrive_service, tab_name):
    """Verify each target row in milestone 3 has a valid direct GDrive link in the canonical folder."""
    all_rows = gsheet_data[tab_name]
    expected_folder = CANONICAL_FOLDERS[tab_name]

    for r_idx in TARGET_ROWS[tab_name]:
        row_dict = all_rows[r_idx - 2]
        video_url = row_dict.get("Video", "").strip()
        batch_id = row_dict.get("#", f"row_{r_idx}")

        match = re.match(r"^https:\/\/drive\.google\.com\/file\/d\/([a-zA-Z0-9_-]+)\/view\?usp=drivesdk$", video_url)
        assert match is not None, f"[{tab_name}] Row {r_idx} ({batch_id}) video URL does not match canonical format: '{video_url}'"

        file_id = match.group(1)
        file_meta = gdrive_service.files().get(
            fileId=file_id,
            fields="id, name, size, mimeType, parents, trashed",
            supportsAllDrives=True
        ).execute()

        assert not file_meta.get("trashed", False), f"[{tab_name}] File {file_id} is in trash"
        assert int(file_meta.get("size", 0)) > 500 * 1024, f"[{tab_name}] File {file_id} too small ({file_meta.get('size')} bytes)"
        assert expected_folder in file_meta.get("parents", []), f"[{tab_name}] File {file_id} parent '{file_meta.get('parents')}' does not contain canonical folder '{expected_folder}'"


def test_milestone4_21px_row_height_invariant():
    """Verify 100% of rows across all 4 tabs have strictly 21px row height."""
    from scripts.enforce_row_height_21px import audit_and_enforce_row_height, TARGET_ROW_HEIGHT_PX
    res = audit_and_enforce_row_height(TARGET_ROW_HEIGHT_PX)
    for tab, info in res.items():
        assert info["all_target"] is True, f"Tab {tab} did not meet 21px invariant: {info}"
