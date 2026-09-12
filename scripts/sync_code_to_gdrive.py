#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sync Quiz Codebase to Google Drive (scripts/sync_code_to_gdrive.py).
Packages the clean, sanitized codebase across all 4 quiz tabs (pinyin, vocabCN, vocabVN, multilevels)
and synchronizes it directly to the designated Google Drive Codebase folder:
Folder: 1C-n3Un-D6Teu4LapgIWWeVZ6l7toH8lm (00.codebases)
"""

import os
import sys
import shutil
import zipfile
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from google.oauth2.service_account import Credentials as SACreds
from google.oauth2.credentials import Credentials as UserCreds
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [CodeSync] %(message)s")
logger = logging.getLogger("CodeSync")

BASE_DIR = Path(__file__).resolve().parent.parent
MAP_FILE = BASE_DIR / "gdrive_folder_map.json"
SA_PATH = Path(os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/google_sa/service_account.json"))
USER_OAUTH_PATH = Path(os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/google_oauth/user_oauth2.json"))

DEFAULT_CODE_FOLDER_ID = "1C-n3Un-D6Teu4LapgIWWeVZ6l7toH8lm"

EXCLUDE_DIRS = {
    ".git", ".venv", "venv", ".agents", "output", "__pycache__", ".pytest_cache",
    ".idea", ".vscode", "artifacts"
}

EXCLUDE_EXTENSIONS = {
    ".pyc", ".pyo", ".log", ".pid", ".tmp", ".gz", ".zip", ".tar"
}

EXCLUDE_FILES = {
    "service_account.json", "user_oauth2.json", "token.json", "colab_batch.pid",
    "colab_batch_execution.log"
}


def get_vietnam_now_str() -> str:
    tz_vn = timezone(timedelta(hours=7))
    return datetime.now(tz_vn).strftime("%Y%m%d_%H%M%S")


def get_code_folder_id() -> str:
    if MAP_FILE.exists():
        try:
            with open(MAP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "code_sync_folder_id" in data and data["code_sync_folder_id"]:
                    return data["code_sync_folder_id"]
        except Exception:
            pass
    return DEFAULT_CODE_FOLDER_ID


def get_gdrive_service():
    scopes = ["https://www.googleapis.com/auth/drive"]

    if USER_OAUTH_PATH.exists():
        try:
            with open(USER_OAUTH_PATH, "r", encoding="utf-8") as f:
                d = json.load(f)
            creds = UserCreds(
                token=None,
                refresh_token=d.get("refresh_token"),
                token_uri=d.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=d.get("client_id"),
                client_secret=d.get("client_secret"),
                scopes=scopes
            )
            creds.refresh(Request())
            logger.info("✓ Authenticated via Google OAuth 2.0 User Credentials.")
            return build("drive", "v3", credentials=creds)
        except Exception as e:
            logger.warning(f"OAuth auth warning: {e}. Falling back to Service Account...")

    if SA_PATH.exists():
        creds = SACreds.from_service_account_file(str(SA_PATH), scopes=scopes)
        logger.info("✓ Authenticated via Service Account.")
        return build("drive", "v3", credentials=creds)

    raise FileNotFoundError("No valid Google credentials found for code sync!")


def build_clean_zip(output_zip: Path) -> int:
    """Creates a clean, sanitized zip archive of the quiz codebase."""
    logger.info(f"📦 Packaging clean codebase from {BASE_DIR}...")
    file_count = 0

    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(BASE_DIR):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in EXCLUDE_EXTENSIONS or file in EXCLUDE_FILES:
                    continue

                full_path = Path(root) / file
                rel_path = full_path.relative_to(BASE_DIR)
                parts = rel_path.parts
                if any(p in EXCLUDE_DIRS for p in parts):
                    continue

                zf.write(full_path, arcname=str(rel_path))
                file_count += 1

    size_mb = output_zip.stat().st_size / (1024 * 1024)
    logger.info(f"✓ Packaged {file_count} files into {output_zip.name} ({size_mb:.2f} MB)")
    return file_count


def upload_to_drive(service, file_path: Path, folder_id: str, remote_name: str) -> str:
    """Uploads a file to Google Drive and returns the file ID."""
    logger.info(f"🚀 Uploading {remote_name} to Google Drive folder [{folder_id}]...")
    media = MediaFileUpload(str(file_path), mimetype="application/zip", resumable=True)

    query = f"'{folder_id}' in parents and name = '{remote_name}' and trashed = false"
    res = service.files().list(q=query, fields="files(id, name)", supportsAllDrives=True).execute()
    existing = res.get("files", [])

    if existing:
        file_id = existing[0]["id"]
        logger.info(f"  Existing file found ({file_id}), updating in-place...")
        updated = service.files().update(
            fileId=file_id,
            media_body=media,
            fields="id, name, webViewLink",
            supportsAllDrives=True
        ).execute()
        return updated.get("id")
    else:
        meta = {
            "name": remote_name,
            "parents": [folder_id]
        }
        created = service.files().create(
            body=meta,
            media_body=media,
            fields="id, name, webViewLink",
            supportsAllDrives=True
        ).execute()
        return created.get("id")


def sync_code_to_gdrive() -> bool:
    target_folder_id = get_code_folder_id()
    logger.info(f"=== Starting Codebase Sync to Google Drive [{target_folder_id}] ===")

    service = get_gdrive_service()

    timestamp = get_vietnam_now_str()
    tmp_dir = Path("/tmp")
    latest_zip = tmp_dir / "quiz_codebase_latest.zip"
    versioned_zip = tmp_dir / f"quiz_codebase_{timestamp}.zip"

    try:
        build_clean_zip(latest_zip)
        shutil.copy2(latest_zip, versioned_zip)

        latest_id = upload_to_drive(service, latest_zip, target_folder_id, "quiz_codebase_latest.zip")
        version_id = upload_to_drive(service, versioned_zip, target_folder_id, f"quiz_codebase_{timestamp}.zip")

        logger.info("🎉 Codebase Sync Complete!")
        logger.info(f"  • Latest: https://drive.google.com/file/d/{latest_id}/view")
        logger.info(f"  • Version: https://drive.google.com/file/d/{version_id}/view")
        return True
    except Exception as e:
        logger.error(f"❌ Code sync failed: {e}")
        return False
    finally:
        for p in [latest_zip, versioned_zip]:
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass


if __name__ == "__main__":
    ok = sync_code_to_gdrive()
    sys.exit(0 if ok else 1)
