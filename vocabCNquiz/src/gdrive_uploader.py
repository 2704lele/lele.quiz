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
        oauth_candidates = [
            os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/google_oauth/user_oauth2.json"),
            os.path.join(config.base_dir, "configs", "oauth_credentials.json"),
            os.path.join(config.base_dir, "..", "configs", "oauth_credentials.json"),
        ]

        env_oauth = os.getenv("GOOGLE_USER_OAUTH2_JSON") or os.getenv("GOOGLE_OAUTH_JSON")
        if env_oauth and env_oauth.strip().startswith("{"):
            try:
                data = json.loads(env_oauth)
                user_creds = UserCredentials(
                    token=data.get("token") or data.get("access_token"),
                    refresh_token=data.get("refresh_token"),
                    token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
                    client_id=data.get("client_id"),
                    client_secret=data.get("client_secret")
                )
                user_creds.refresh(Request())
                self.service = build("drive", "v3", credentials=user_creds)
                logger.info("Google OAuth 2.0 User Authentication Successful from env!")
                return
            except Exception as e:
                logger.warning(f"OAuth from env failed: {e}")

        for oauth_file in oauth_candidates:
            if oauth_file and os.path.exists(oauth_file) and os.path.getsize(oauth_file) > 10:
                try:
                    with open(oauth_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    user_creds = UserCredentials(
                        token=data.get("token") or data.get("access_token"),
                        refresh_token=data.get("refresh_token"),
                        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
                        client_id=data.get("client_id"),
                        client_secret=data.get("client_secret")
                    )
                    user_creds.refresh(Request())
                    self.service = build("drive", "v3", credentials=user_creds)
                    logger.info(f"Google OAuth 2.0 User Authentication Successful from {oauth_file}!")
                    return
                except Exception as e:
                    logger.warning(f"OAuth attempt with {oauth_file} failed: {e}")

        client_id = os.getenv("GDRIVE_CLIENT_ID")
        client_secret = os.getenv("GDRIVE_CLIENT_SECRET")
        refresh_token = os.getenv("GDRIVE_REFRESH_TOKEN")

        if client_id and client_secret and refresh_token:
            try:
                user_creds = UserCredentials(
                    token=None,
                    refresh_token=refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=client_id,
                    client_secret=client_secret
                )
                user_creds.refresh(Request())
                self.service = build("drive", "v3", credentials=user_creds)
                logger.info("Google OAuth 2.0 User Authentication Successful from env vars!")
                return
            except Exception as oe:
                logger.warning(f"Failed to authenticate via OAuth env vars: {oe}")

        # 2. Priority 2: Service Account Credentials (Fallback)
        scopes = [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.file"
        ]

        env_json = os.getenv("GCP_SERVICE_ACCOUNT_KEY") or os.getenv("GCP_SERVICE_ACCOUNT_JSON") or os.getenv("SERVICE_ACCOUNT_JSON")
        if env_json and env_json.strip().startswith("{"):
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
                try:
                    sa_creds = ServiceAccountCredentials.from_service_account_file(path, scopes=scopes)
                    self.service = build("drive", "v3", credentials=sa_creds)
                    logger.info(f"Authenticated via Service Account file: {path}")
                    return
                except Exception as e:
                    logger.warning(f"Service Account file {path} failed: {e}")

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

            web_link = f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk"
            logger.info(f"Uploaded '{filename}' to GDrive folder {self.folder_id} -> {web_link}")
            return web_link
        except Exception as e:
            logger.error(f"CRITICAL: Failed to upload file to Google Drive: {e}")
            raise RuntimeError(f"Google Drive upload failed: {e}") from e
