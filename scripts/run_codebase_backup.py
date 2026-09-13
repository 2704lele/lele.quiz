#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LeLe Quiz Codebase & Colab Backup Engine (scripts/run_codebase_backup.py).
Packages clean codebase and Colab modules into ZIP archives and uploads them to Google Drive:
- 00.codebases (1C-n3Un-D6Teu4LapgIWWeVZ6l7toH8lm)
- Backups (1QHYaOfvE8yoShR4UcM0o3zd0uOh7rhaK)
"""

import os
import sys
import json
import shutil
import zipfile
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from google.oauth2.credentials import Credentials as UserCreds
from google.oauth2.service_account import Credentials as SACreds
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [BackupEngine] %(message)s")
logger = logging.getLogger("BackupEngine")

QUIZ_ROOT = Path(__file__).resolve().parent.parent
MAP_FILE = QUIZ_ROOT / "gdrive_folder_map.json"
USER_OAUTH_PATH = Path(os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/google_oauth/user_oauth2.json"))
SA_PATH = Path(os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/google_sa/service_account.json"))

DEFAULT_CODE_FOLDER_ID = "1C-n3Un-D6Teu4LapgIWWeVZ6l7toH8lm"
DEFAULT_BACKUP_FOLDER_ID = "1QHYaOfvE8yoShR4UcM0o3zd0uOh7rhaK"

EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".idea", ".vscode", "output", "dist", "build", ".agents"
}

EXCLUDE_EXTS = {
    ".pyc", ".pyo", ".log", ".pid", ".tmp"
}

EXCLUDE_FILES = {
    "service_account.json", "user_oauth2.json", "token.json", ".env"
}


def get_vietnam_timestamp() -> str:
    tz_vn = timezone(timedelta(hours=7))
    return datetime.now(tz_vn).strftime("%Y%m%d_%H%M%S")


def get_folder_ids() -> tuple[str, str]:
    code_id = DEFAULT_CODE_FOLDER_ID
    backup_id = DEFAULT_BACKUP_FOLDER_ID

    if MAP_FILE.exists():
        try:
            with open(MAP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                code_id = data.get("code_sync_folder_id") or data.get("target_folder_id") or code_id
                backup_id = data.get("backup_folder_id") or data.get("_backup_folder_id") or backup_id
        except Exception as e:
            logger.warning(f"Could not parse gdrive_folder_map.json: {e}")

    return code_id, backup_id


def get_gdrive_service():
    scopes = ["https://www.googleapis.com/auth/drive"]

    # 1. User OAuth 2.0
    env_oauth = os.getenv("GOOGLE_USER_OAUTH2_JSON") or os.getenv("GOOGLE_OAUTH_JSON")
    if env_oauth and env_oauth.strip().startswith("{"):
        try:
            d = json.loads(env_oauth)
            creds = UserCreds(
                token=d.get("access_token") or d.get("token"),
                refresh_token=d.get("refresh_token"),
                token_uri=d.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=d.get("client_id"),
                client_secret=d.get("client_secret"),
                scopes=scopes
            )
            creds.refresh(Request())
            logger.info("✓ Authenticated via Google OAuth 2.0 (Env)")
            return build("drive", "v3", credentials=creds)
        except Exception as e:
            logger.warning(f"OAuth env authentication failed: {e}")

    if USER_OAUTH_PATH.exists():
        try:
            with open(USER_OAUTH_PATH, "r", encoding="utf-8") as f:
                d = json.load(f)
            creds = UserCreds(
                token=d.get("access_token") or d.get("token"),
                refresh_token=d.get("refresh_token"),
                token_uri=d.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=d.get("client_id"),
                client_secret=d.get("client_secret"),
                scopes=scopes
            )
            creds.refresh(Request())
            logger.info(f"✓ Authenticated via Google OAuth 2.0 ({USER_OAUTH_PATH})")
            return build("drive", "v3", credentials=creds)
        except Exception as e:
            logger.warning(f"OAuth file authentication failed: {e}")

    # 2. GCP Service Account
    env_sa = os.getenv("GCP_SERVICE_ACCOUNT_KEY") or os.getenv("GCP_SERVICE_ACCOUNT_JSON") or os.getenv("SERVICE_ACCOUNT_JSON")
    if env_sa and env_sa.strip().startswith("{"):
        try:
            info = json.loads(env_sa)
            creds = SACreds.from_service_account_info(info, scopes=scopes)
            logger.info("✓ Authenticated via Service Account (Env)")
            return build("drive", "v3", credentials=creds)
        except Exception as e:
            logger.warning(f"SA env authentication failed: {e}")

    if SA_PATH.exists():
        try:
            creds = SACreds.from_service_account_file(str(SA_PATH), scopes=scopes)
            logger.info(f"✓ Authenticated via Service Account ({SA_PATH})")
            return build("drive", "v3", credentials=creds)
        except Exception as e:
            logger.warning(f"SA file authentication failed: {e}")

    raise RuntimeError("No valid Google credentials found for Google Drive backup!")


def create_clean_codebase_zip(output_zip: Path) -> int:
    logger.info(f"📦 Packaging clean codebase from {QUIZ_ROOT}...")
    file_count = 0

    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(QUIZ_ROOT):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            for file in files:
                ext = Path(file).suffix.lower()
                if ext in EXCLUDE_EXTS or file in EXCLUDE_FILES:
                    continue

                full_path = Path(root) / file
                rel_path = full_path.relative_to(QUIZ_ROOT)

                if any(p in EXCLUDE_DIRS for p in rel_path.parts):
                    continue

                zf.write(full_path, arcname=str(rel_path))
                file_count += 1

    size_mb = output_zip.stat().st_size / (1024 * 1024)
    logger.info(f"✓ Codebase zip created: {output_zip.name} ({file_count} files, {size_mb:.2f} MB)")
    return file_count


def create_colab_backup_zip(output_zip: Path) -> int:
    logger.info("📦 Packaging Colab modules and scripts...")
    file_count = 0

    colab_dir = QUIZ_ROOT / "colab"
    scripts_dir = QUIZ_ROOT / "scripts"

    colab_files = []
    if colab_dir.exists():
        for root, _, files in os.walk(colab_dir):
            for f in files:
                colab_files.append(Path(root) / f)

    if scripts_dir.exists():
        for f in scripts_dir.glob("colab*.py"):
            colab_files.append(f)

    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for full_path in colab_files:
            rel_path = full_path.relative_to(QUIZ_ROOT)
            zf.write(full_path, arcname=str(rel_path))
            file_count += 1

    size_kb = output_zip.stat().st_size / 1024
    logger.info(f"✓ Colab backup zip created: {output_zip.name} ({file_count} files, {size_kb:.2f} KB)")
    return file_count


def upload_to_gdrive(service, file_path: Path, folder_id: str, remote_name: str) -> str:
    logger.info(f"🚀 Syncing {remote_name} -> Drive folder [{folder_id}]...")
    media = MediaFileUpload(str(file_path), mimetype="application/zip", resumable=True)

    query = f"'{folder_id}' in parents and name = '{remote_name}' and trashed = false"
    res = service.files().list(q=query, fields="files(id, name)", supportsAllDrives=True).execute()
    existing = res.get("files", [])

    if existing:
        file_id = existing[0]["id"]
        updated = service.files().update(
            fileId=file_id,
            media_body=media,
            fields="id, name, webViewLink",
            supportsAllDrives=True
        ).execute()
        logger.info(f"  ✓ In-place update complete: {remote_name} (ID: {file_id})")
        return updated.get("id", file_id)
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
        file_id = created.get("id")
        logger.info(f"  ✓ Upload complete: {remote_name} (ID: {file_id})")
        return file_id


def run_codebase_backup() -> bool:
    code_folder_id, backup_folder_id = get_folder_ids()
    timestamp = get_vietnam_timestamp()

    logger.info("==================================================")
    logger.info("  🚀 STARTING CODEBASE & COLAB BACKUP TO GDRIVE   ")
    logger.info(f"  • Codebase Target: 00.codebases [{code_folder_id}]")
    logger.info(f"  • Backup Target:   Backups [{backup_folder_id}]")
    logger.info(f"  • Timestamp:       {timestamp} (GMT+7)")
    logger.info("==================================================")

    service = get_gdrive_service()

    tmp_dir = Path("/tmp")
    codebase_latest = tmp_dir / "quiz_codebase_latest.zip"
    codebase_versioned = tmp_dir / f"quiz_codebase_{timestamp}.zip"
    colab_latest = tmp_dir / "colab_steps_all_backup.zip"
    colab_versioned = tmp_dir / f"colab_backup_{timestamp}.zip"

    try:
        # 1. Package codebase
        create_clean_codebase_zip(codebase_latest)
        shutil.copy2(codebase_latest, codebase_versioned)

        # 2. Package colab
        create_colab_backup_zip(colab_latest)
        shutil.copy2(colab_latest, colab_versioned)

        # 3. Upload codebase to 00.codebases
        latest_code_id = upload_to_gdrive(service, codebase_latest, code_folder_id, "quiz_codebase_latest.zip")
        ver_code_id = upload_to_gdrive(service, codebase_versioned, code_folder_id, f"quiz_codebase_{timestamp}.zip")

        # 4. Upload colab to 00.codebases
        latest_colab_id = upload_to_gdrive(service, colab_latest, code_folder_id, "colab_steps_all_backup.zip")
        ver_colab_id = upload_to_gdrive(service, colab_versioned, code_folder_id, f"colab_backup_{timestamp}.zip")

        # 5. Backup versioned codebase copy to Backups folder
        snapshot_code_id = upload_to_gdrive(service, codebase_versioned, backup_folder_id, f"quiz_codebase_{timestamp}.zip")

        logger.info("==================================================")
        logger.info("  🎉 BACKUP & SYNC COMPLETED SUCCESSFULLY!        ")
        logger.info(f"  • 00.codebases / quiz_codebase_latest.zip: https://drive.google.com/file/d/{latest_code_id}/view")
        logger.info(f"  • 00.codebases / quiz_codebase_{timestamp}.zip: https://drive.google.com/file/d/{ver_code_id}/view")
        logger.info(f"  • 00.codebases / colab_steps_all_backup.zip: https://drive.google.com/file/d/{latest_colab_id}/view")
        logger.info(f"  • Backups / quiz_codebase_{timestamp}.zip: https://drive.google.com/file/d/{snapshot_code_id}/view")
        logger.info("==================================================")
        return True
    except Exception as e:
        logger.error(f"❌ Backup failed with error: {e}", exc_info=True)
        return False
    finally:
        for p in [codebase_latest, codebase_versioned, colab_latest, colab_versioned]:
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass


if __name__ == "__main__":
    ok = run_codebase_backup()
    sys.exit(0 if ok else 1)
