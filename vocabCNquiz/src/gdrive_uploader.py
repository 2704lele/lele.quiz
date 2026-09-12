import os
import json
import logging
from typing import Optional
from google.oauth2.credentials import Credentials as UserCredentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from src.config import config

logger = logging.getLogger("GDriveUploader")

TARGET_FOLDER_ID = "1eI7I4jQqGBjD7MC_NXJ4zwFANxrcZM1E"

class GDriveUploader:
    def __init__(self, folder_id: Optional[str] = None):
        self.folder_id = folder_id or os.getenv("GDRIVE_TARGET_FOLDER") or os.getenv("GDRIVE_FOLDER_ID") or TARGET_FOLDER_ID
        self.service = None
        self._authenticate()

    def _authenticate(self):
        client_id = os.getenv("GDRIVE_CLIENT_ID")
        client_secret = os.getenv("GDRIVE_CLIENT_SECRET")
        refresh_token = os.getenv("GDRIVE_REFRESH_TOKEN")

        oauth_file = os.path.join(config.base_dir, "configs", "oauth_credentials.json")
        if not (client_id and client_secret and refresh_token) and os.path.exists(oauth_file):
            try:
                with open(oauth_file, "r") as f:
                    oauth_data = json.load(f)
                    client_id = client_id or oauth_data.get("client_id")
                    client_secret = client_secret or oauth_data.get("client_secret")
                    refresh_token = refresh_token or oauth_data.get("refresh_token")
            except Exception as e:
                logger.warning(f"Could not read oauth_credentials.json: {e}")

        if client_id and client_secret and refresh_token:
            try:
                logger.info("Authenticating via Google OAuth 2.0 User Credentials...")
                user_creds = UserCredentials(
                    token=None,
                    refresh_token=refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=client_id,
                    client_secret=client_secret
                )
                user_creds.refresh(Request())
                self.service = build("drive", "v3", credentials=user_creds)
                logger.info("Google OAuth 2.0 User Authentication Successful!")
                return
            except Exception as oe:
                logger.error(f"Failed to authenticate via OAuth 2.0: {oe}. Falling back to Service Account...")

        scopes = [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.file"
        ]

        env_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON") or os.getenv("SERVICE_ACCOUNT_JSON")
        if env_json and env_json.strip():
            try:
                info = json.loads(env_json)
                sa_creds = ServiceAccountCredentials.from_service_account_info(info, scopes=scopes)
                self.service = build("drive", "v3", credentials=sa_creds)
                logger.info("Authenticated via Service Account (env).")
                return
            except Exception as e:
                logger.warning(f"Failed to parse Service Account from env: {e}")

        for path in config.creds_paths:
            if path and os.path.exists(path) and os.path.getsize(path) > 10:
                sa_creds = ServiceAccountCredentials.from_service_account_file(path, scopes=scopes)
                self.service = build("drive", "v3", credentials=sa_creds)
                logger.info(f"Authenticated via Service Account file: {path}")
                return

        raise RuntimeError("Could not authenticate Google Drive client via any credentials!")

    def upload_file(self, local_path: str, remote_filename: Optional[str] = None, mime_type: str = "video/mp4") -> str:
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file does not exist: {local_path}")

        filename = remote_filename or os.path.basename(local_path)
        file_metadata = {
            "name": filename,
            "parents": [self.folder_id]
        }

        import hashlib
        try:
            media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, webViewLink, webContentLink",
                supportsAllDrives=True
            ).execute()

            file_id = file.get("id")

            # Ensure public read permissions for Buffer and Telegram preview
            try:
                self.service.permissions().create(
                    fileId=file_id,
                    body={"role": "reader", "type": "anyone"},
                    fields="id",
                    supportsAllDrives=True
                ).execute()
            except Exception as pe:
                logger.warning(f"Warning setting permission for file {file_id}: {pe}")

            web_link = file.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk"
            logger.info(f"Uploaded '{filename}' to GDrive folder {self.folder_id} -> {web_link}")
            return web_link
        except Exception as e:
            logger.error(f"CRITICAL: Failed to upload file to Google Drive: {e}")
            raise RuntimeError(f"Google Drive upload failed: {e}") from e
