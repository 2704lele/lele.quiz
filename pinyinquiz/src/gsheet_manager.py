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

        # 1. Try env variable JSON content
        env_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON") or os.getenv("SERVICE_ACCOUNT_JSON")
        if env_json and env_json.strip():
            try:
                info = json.loads(env_json)
                logger.info("Loaded credentials directly from GCP_SERVICE_ACCOUNT_JSON environment variable.")
                return Credentials.from_service_account_info(info, scopes=scopes)
            except Exception as e:
                logger.warning(f"Failed to parse credentials from env JSON: {e}")

        # 2. Try credentials path or fallback paths
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
                return self.worksheet.get_all_records()
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"Failed to fetch all rows after {max_retries} attempts: {e}")
                    return []
                wait_time = 12 if ("429" in str(e) or "Quota exceeded" in str(e)) else (attempt * 2)
                logger.warning(f"Attempt {attempt} to fetch all rows failed ({e}). Retrying in {wait_time}s...")
                time.sleep(wait_time)
        return []

    def get_pending_batches(self) -> List[Dict[str, Any]]:
        """Retrieve rows with Status == 'Pending'."""
        for attempt in range(1, 4):
            try:
                rows = self.worksheet.get_all_values()
                break
            except Exception as e:
                if attempt == 3:
                    logger.error(f"Failed to get values: {e}")
                    return []
                time.sleep(attempt * 2)

        if not rows or len(rows) < 2:
            return []

        headers = rows[0]
        pending_batches = []

        for row_idx, row in enumerate(rows[1:], start=2):
            row_dict = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
            status = row_dict.get("Status", "").strip().lower()
            if status == "pending":
                words = []
                for w_idx in range(1, 6):
                    w_key = f"Word {w_idx}"
                    w_val = row_dict.get(w_key, "").strip()
                    if w_val:
                        parts = [p.strip() for p in w_val.split("|")]
                        hanzi = parts[0]
                        pinyin = parts[1] if len(parts) > 1 else ""
                        hidden = parts[2] if len(parts) > 2 else ""
                        meaning = parts[3] if len(parts) > 3 else ""
                        words.append({
                            "hanzi": hanzi,
                            "pinyin": pinyin,
                            "hidden_pinyin": hidden,
                            "meaning": meaning or hanzi
                        })

                pending_batches.append({
                    "row_index": row_idx,
                    "id": row_dict.get("#", str(row_idx)),
                    "topic": row_dict.get("Topic", "HSK 1-2 • TỪ VỰNG CƠ BẢN"),
                    "level": row_dict.get("Level", "HSK 1-2"),
                    "words": words,
                    "metadata": row_dict.get("metadata", ""),
                    "raw_data": row_dict
                })

        return pending_batches

    def get_batches_by_status(self, target_status: str = "Video") -> List[Dict[str, Any]]:
        """Retrieve rows matching a specific Status (case-insensitive)."""
        for attempt in range(1, 4):
            try:
                rows = self.worksheet.get_all_values()
                break
            except Exception as e:
                if attempt == 3:
                    logger.error(f"Failed to get values: {e}")
                    return []
                time.sleep(attempt * 2)

        if not rows or len(rows) < 2:
            return []

        headers = rows[0]
        matching_batches = []
        target_lower = target_status.strip().lower()

        for row_idx, row in enumerate(rows[1:], start=2):
            row_dict = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
            status = row_dict.get("Status", "").strip().lower()
            if status == target_lower:
                words = []
                for w_idx in range(1, 6):
                    w_key = f"Word {w_idx}"
                    w_val = row_dict.get(w_key, "").strip()
                    if w_val:
                        parts = [p.strip() for p in w_val.split("|")]
                        hanzi = parts[0]
                        pinyin = parts[1] if len(parts) > 1 else ""
                        hidden = parts[2] if len(parts) > 2 else ""
                        meaning = parts[3] if len(parts) > 3 else ""
                        words.append({
                            "hanzi": hanzi,
                            "pinyin": pinyin,
                            "hidden_pinyin": hidden,
                            "meaning": meaning or hanzi
                        })

                matching_batches.append({
                    "row_index": row_idx,
                    "id": row_dict.get("#", str(row_idx)),
                    "topic": row_dict.get("Topic", "HSK 1-2 • TỪ VỰNG CƠ BẢN"),
                    "level": row_dict.get("Level", "HSK 1-2"),
                    "words": words,
                    "video_url": row_dict.get("Video", ""),
                    "metadata": row_dict.get("metadata", ""),
                    "notes": row_dict.get("Notes", ""),
                    "raw_data": row_dict
                })

        return matching_batches

    def get_batch_by_id(self, target_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific row by ID (# column or row index)."""
        clean_target = str(target_id).replace("#", "").strip()
        for attempt in range(1, 4):
            try:
                rows = self.worksheet.get_all_values()
                break
            except Exception as e:
                if attempt == 3:
                    logger.error(f"Failed to get values: {e}")
                    return None
                time.sleep(attempt * 2)

        if not rows or len(rows) < 2:
            return None

        headers = rows[0]
        # 1. First priority: match exact '#' column ID
        for row_idx, row in enumerate(rows[1:], start=2):
            row_dict = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
            row_id = str(row_dict.get("#", "")).replace("#", "").strip()
            if row_id == clean_target:
                words = []
                for w_idx in range(1, 6):
                    w_key = f"Word {w_idx}"
                    w_val = row_dict.get(w_key, "").strip()
                    if w_val:
                        parts = [p.strip() for p in w_val.split("|")]
                        hanzi = parts[0]
                        pinyin = parts[1] if len(parts) > 1 else ""
                        hidden = parts[2] if len(parts) > 2 else ""
                        meaning = parts[3] if len(parts) > 3 else ""
                        words.append({
                            "hanzi": hanzi,
                            "pinyin": pinyin,
                            "hidden_pinyin": hidden,
                            "meaning": meaning or hanzi
                        })

                return {
                    "row_index": row_idx,
                    "id": row_dict.get("#", str(row_idx)),
                    "topic": row_dict.get("Topic", "HSK 1-2 • TỪ VỰNG CƠ BẢN"),
                    "level": row_dict.get("Level", "HSK 1-2"),
                    "words": words,
                    "video_url": row_dict.get("Video", ""),
                    "metadata": row_dict.get("metadata", ""),
                    "notes": row_dict.get("Notes", ""),
                    "raw_data": row_dict
                }

        # 2. Second priority fallback: match physical row index
        for row_idx, row in enumerate(rows[1:], start=2):
            if str(row_idx) == clean_target:
                row_dict = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
                words = []
                for w_idx in range(1, 6):
                    w_key = f"Word {w_idx}"
                    w_val = row_dict.get(w_key, "").strip()
                    if w_val:
                        parts = [p.strip() for p in w_val.split("|")]
                        hanzi = parts[0]
                        pinyin = parts[1] if len(parts) > 1 else ""
                        hidden = parts[2] if len(parts) > 2 else ""
                        meaning = parts[3] if len(parts) > 3 else ""
                        words.append({
                            "hanzi": hanzi,
                            "pinyin": pinyin,
                            "hidden_pinyin": hidden,
                            "meaning": meaning or hanzi
                        })

                return {
                    "row_index": row_idx,
                    "id": row_dict.get("#", str(row_idx)),
                    "topic": row_dict.get("Topic", "HSK 1-2 • TỪ VỰNG CƠ BẢN"),
                    "level": row_dict.get("Level", "HSK 1-2"),
                    "words": words,
                    "video_url": row_dict.get("Video", ""),
                    "metadata": row_dict.get("metadata", ""),
                    "notes": row_dict.get("Notes", ""),
                    "raw_data": row_dict
                }
        return None

    def update_batch_status(self, row_index: int, status: str, video_link: str = "", metadata_link: str = ""):
        """Update batch status, video GDrive link and metadata GDrive link."""
        try:
            # Col 4: Status
            self.worksheet.update_cell(row_index, 4, status)
            # Col 10: metadata
            if metadata_link:
                self.worksheet.update_cell(row_index, 10, metadata_link)
            # Col 11: Video (Google Drive Link)
            if video_link:
                self.worksheet.update_cell(row_index, 11, video_link)
            logger.info(f"Updated row {row_index} status -> {status}")
        except Exception as e:
            logger.error(f"Failed to update row {row_index}: {e}")

    def update_social_status(self, row_index: int, platform: str, url_or_status: str):
        """Update social posting status / URL (youtube: 12, tiktok: 13, facebook: 14)."""
        col_map = {
            "youtube": 12,
            "tiktok": 13,
            "facebook": 14
        }
        col = col_map.get(platform.lower())
        if col:
            try:
                self.worksheet.update_cell(row_index, col, url_or_status)
                logger.info(f"Updated row {row_index} {platform} -> {url_or_status}")
            except Exception as e:
                logger.error(f"Failed to update {platform} for row {row_index}: {e}")

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
        return {
            "hanzi": hanzi,
            "pinyin": pinyin,
            "hidden_pinyin": hidden_pinyin,
            "meaning": meaning
        }

if __name__ == "__main__":
    manager = GSheetManager()
    batches = manager.get_pending_batches()
    print(f"Found {len(batches)} pending batches.")
