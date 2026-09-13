import os
import time
import json
import logging
from typing import List, Dict, Any, Optional
import gspread
from google.oauth2.service_account import Credentials
from src.config import config

logger = logging.getLogger("GSheetManager")

STANDARD_COLUMNS = [
    "#",
    "Topic",
    "Level",
    "Status",
    "Word 1",
    "Word 2",
    "Word 3",
    "Word 4",
    "Word 5",
    "metadata",
    "Video",
    "Youtube",
    "Tiktok",
    "Facebook",
    "Created At",
    "Notes"
]

class GSheetManager:
    def __init__(self, credentials_path: str = None, spreadsheet_id: str = None, tab_name: str = None):
        self.spreadsheet_id = spreadsheet_id or config.spreadsheet_id
        self.tab_name = tab_name or config.sheet_tab_name
        self.credentials_path = credentials_path
        self.client = None
        self.spreadsheet = None
        self.worksheet = None
        self._authenticate()

    def _get_credentials(self) -> Credentials:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        env_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON") or os.getenv("SERVICE_ACCOUNT_JSON")
        if env_json and env_json.strip():
            try:
                info = json.loads(env_json)
                logger.info("Loaded credentials directly from GCP_SERVICE_ACCOUNT_JSON environment variable.")
                return Credentials.from_service_account_info(info, scopes=scopes)
            except Exception as e:
                logger.warning(f"Failed to parse credentials from env JSON: {e}")

        search_paths = [self.credentials_path] if self.credentials_path else []
        search_paths.extend(config.creds_paths)

        for path in search_paths:
            if path and os.path.exists(path) and os.path.getsize(path) > 10:
                logger.info(f"Loaded credentials from file: {path}")
                return Credentials.from_service_account_file(path, scopes=scopes)

        raise FileNotFoundError(f"No valid Google service account credentials found! Checked: {search_paths}")

    def _authenticate(self):
        credentials = self._get_credentials()
        self.client = gspread.authorize(credentials)

        max_retries = 6
        for attempt in range(1, max_retries + 1):
            try:
                self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
                break
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"Failed to open spreadsheet after {max_retries} attempts: {e}")
                    raise
                wait_time = 12 if ("429" in str(e) or "Quota exceeded" in str(e)) else (attempt * 2)
                logger.warning(f"Attempt {attempt} to open spreadsheet failed ({e}). Retrying in {wait_time}s...")
                time.sleep(wait_time)

        for attempt in range(1, max_retries + 1):
            try:
                self.worksheet = self.spreadsheet.worksheet(self.tab_name)
                break
            except gspread.exceptions.WorksheetNotFound:
                logger.info(f"Worksheet '{self.tab_name}' not found. Creating it...")
                self.worksheet = self.spreadsheet.add_worksheet(title=self.tab_name, rows=100, cols=20)
                self.init_header()
                break
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"Failed to get worksheet '{self.tab_name}' after {max_retries} attempts: {e}")
                    raise
                wait_time = 12 if ("429" in str(e) or "Quota exceeded" in str(e)) else (attempt * 2)
                logger.warning(f"Attempt {attempt} to get worksheet failed ({e}). Retrying in {wait_time}s...")
                time.sleep(wait_time)

    def init_header(self):
        """Set up standard column headers in row 1."""
        self.worksheet.update("A1:P1", [STANDARD_COLUMNS])
        logger.info(f"Initialized headers on tab '{self.tab_name}'")

    def get_all_rows(self) -> List[Dict[str, Any]]:
        """Fetch all rows as dictionaries with retry and quota backoff."""
        max_retries = 6
        for attempt in range(1, max_retries + 1):
            try:
                records = self.worksheet.get_all_records()
                results = []
                for idx, r in enumerate(records, start=2):
                    r["_row_number"] = idx
                    results.append(r)
                return results
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"Failed to fetch sheet records after {max_retries} attempts: {e}")
                    return []
                wait_time = 12 if ("429" in str(e) or "Quota exceeded" in str(e)) else (1.5 * attempt)
                logger.warning(f"Attempt {attempt} to fetch sheet records failed ({e}). Retrying in {wait_time}s...")
                time.sleep(wait_time)
        return []

    def get_pending_batches(self) -> List[Dict[str, Any]]:
        """Return all rows with Status == 'Pending'."""
        rows = self.get_all_rows()
        return [r for r in rows if str(r.get("Status", "")).strip().lower() == "pending"]

    def get_row_by_id(self, batch_id: Any) -> Optional[Dict[str, Any]]:
        """Get specific batch row by # ID (Strict 1:1 Row Mapping)."""
        clean_id = str(batch_id).replace("#", "").strip()
        rows = self.get_all_rows()
        for r in rows:
            r_id = str(r.get("#", "")).replace("#", "").strip()
            if r_id == clean_id:
                return r
        return None

    def get_batches_by_status(self, target_status: str = "Video") -> List[Dict[str, Any]]:
        """Retrieve rows matching a specific Status (case-insensitive) formatted for QC and processing."""
        rows = self.get_all_rows()
        target_lower = target_status.strip().lower()
        matching_batches = []

        for r in rows:
            status = str(r.get("Status", "")).strip().lower()
            if status == target_lower:
                words = []
                for w_idx in range(1, 6):
                    w_key = f"Word {w_idx}"
                    w_val = str(r.get(w_key, "")).strip()
                    if w_val:
                        w = self.parse_word_entry(w_val)
                        if w.get("hanzi"):
                            words.append(w)

                row_idx = r.get("_row_number", 2)
                matching_batches.append({
                    "row_index": row_idx,
                    "id": str(r.get("#", str(row_idx))).replace("#", "").strip(),
                    "topic": r.get("Topic", "Từ Vựng Cơ Bản"),
                    "level": r.get("Level", "HSK 1"),
                    "words": words,
                    "video_url": r.get("Video", ""),
                    "metadata": r.get("metadata", ""),
                    "notes": r.get("Notes", ""),
                    "raw_data": r
                })

        return matching_batches

    def get_batch_by_id(self, target_id: Any) -> Optional[Dict[str, Any]]:
        """Retrieve a specific row by ID (# column or row index) formatted for QC."""
        clean_target = str(target_id).replace("#", "").strip()
        rows = self.get_all_rows()
        for r in rows:
            r_id = str(r.get("#", "")).replace("#", "").strip()
            if r_id == clean_target or str(r.get("_row_number", "")) == clean_target:
                words = []
                for w_idx in range(1, 6):
                    w_key = f"Word {w_idx}"
                    w_val = str(r.get(w_key, "")).strip()
                    if w_val:
                        w = self.parse_word_entry(w_val)
                        if w.get("hanzi"):
                            words.append(w)

                row_idx = r.get("_row_number", 2)
                return {
                    "row_index": row_idx,
                    "id": str(r.get("#", str(row_idx))).replace("#", "").strip(),
                    "topic": r.get("Topic", "Từ Vựng Cơ Bản"),
                    "level": r.get("Level", "HSK 1"),
                    "words": words,
                    "video_url": r.get("Video", ""),
                    "metadata": r.get("metadata", ""),
                    "notes": r.get("Notes", ""),
                    "raw_data": r
                }
        return None

    def update_batch_status(self, row_number: int, status: str, video_link: str = None, notes: str = None):
        """Update batch status, video link and notes at exact row number."""
        updates = [{"range": f"D{row_number}", "values": [[status]]}]
        if video_link is not None:
            updates.append({"range": f"K{row_number}", "values": [[video_link]]})
        if notes is not None:
            updates.append({"range": f"P{row_number}", "values": [[notes]]})
        self.worksheet.batch_update(updates)
        logger.info(f"Updated row {row_number} -> Status: '{status}'")

    def append_or_insert_batch(self, batch_data: Dict[str, Any], target_row: int = None) -> int:
        """
        Insert or backfill batch strictly matching Row == # rule.
        """
        if target_row is None:
            all_vals = self.worksheet.get_all_values()
            target_row = len(all_vals) + 1

        if target_row > self.worksheet.row_count:
            self.worksheet.add_rows(max(50, target_row - self.worksheet.row_count + 10))

        batch_id_str = f"#{target_row}"
        row_values = [
            batch_id_str,
            batch_data.get("topic", ""),
            batch_data.get("level", "HSK 1"),
            batch_data.get("status", "Pending"),
            batch_data.get("word_1", ""),
            batch_data.get("word_2", ""),
            batch_data.get("word_3", ""),
            batch_data.get("word_4", ""),
            batch_data.get("word_5", ""),
            json.dumps(batch_data.get("metadata", {}), ensure_ascii=False) if isinstance(batch_data.get("metadata"), dict) else str(batch_data.get("metadata", "")),
            batch_data.get("video", ""),
            batch_data.get("youtube", ""),
            batch_data.get("tiktok", ""),
            batch_data.get("facebook", ""),
            batch_data.get("created_at", time.strftime("%Y-%m-%d %H:%M:%S")),
            batch_data.get("notes", "")
        ]

        self.worksheet.update(f"A{target_row}:P{target_row}", [row_values])
        logger.info(f"Wrote batch #{target_row} at row {target_row}")
        return target_row

    def parse_word_entry(self, word_raw: str) -> Dict[str, str]:
        """Parse 'hanzi | pinyin | hidden_pinyin | meaning' format."""
        if not word_raw:
            return {"hanzi": "", "pinyin": "", "hidden_pinyin": "", "meaning": ""}
        parts = [p.strip() for p in word_raw.split("|")]
        hanzi = parts[0] if len(parts) > 0 else ""
        pinyin = parts[1] if len(parts) > 1 else ""
        if len(parts) >= 4:
            hidden_pinyin = parts[2]
            meaning = parts[3]
        elif len(parts) == 3:
            hidden_pinyin = ""
            meaning = parts[2]
        else:
            hidden_pinyin = ""
            meaning = hanzi

        # Ensure pinyin has 1:1 syllables matching hanzi count
        if hanzi and pinyin and len(pinyin.split()) != len(hanzi):
            try:
                from src.pinyin_utils import hanzi_to_full_pinyin
                pinyin = hanzi_to_full_pinyin(hanzi)
            except Exception:
                pass

        return {
            "hanzi": hanzi,
            "pinyin": pinyin,
            "hidden_pinyin": hidden_pinyin,
            "meaning": meaning
        }
