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

TARGET_FOLDER_ID = "1f2mFUgpz_pYn3y9HqeHyOG9DzPMVH9QY"

class GDriveUploader:
    def __init__(self, folder_id: Optional[str] = None):
        self.folder_id = folder_id or os.getenv("GDRIVE_TARGET_FOLDER") or os.getenv("GDRIVE_FOLDER_ID") or TARGET_FOLDER_ID
        self.service = None
        self._authenticate()

    def _authenticate(self):
        # 1. Priority 1: User OAuth 2.0 (Refresh Token) - Direct User Quota
        client_id = os.getenv("GDRIVE_CLIENT_ID")
        client_secret = os.getenv("GDRIVE_CLIENT_SECRET")
        refresh_token = os.getenv("GDRIVE_REFRESH_TOKEN")

        # Also check oauth_credentials.json file if present locally
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
                logger.info("Authenticating via Google OAuth 2.0 User Credentials (aleron.dt@gmail.com)...")
                user_creds = UserCredentials(
                    token=None,
                    refresh_token=refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=client_id,
                    client_secret=client_secret
                )
                user_creds.refresh(Request())
                self.service = build("drive", "v3", credentials=user_creds)
                logger.info(" Google OAuth 2.0 User Authentication Successful!")
                return
            except Exception as oe:
                logger.error(f"Failed to authenticate via OAuth 2.0: {oe}. Falling back to Service Account...")

        # 2. Priority 2: Service Account Credentials (Fallback)
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

        raise FileNotFoundError("No valid Google credentials (OAuth 2.0 or Service Account) found!")

    def upload_file(self, file_path: str, custom_filename: Optional[str] = None, mimetype: Optional[str] = None) -> Optional[str]:
        """
        Uploads a video or image thumbnail file to Google Drive folder and returns the direct web view link.
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found for upload: {file_path}")
            return None

        filename = custom_filename or os.path.basename(file_path)
        logger.info(f"Uploading '{filename}' to Google Drive folder [{self.folder_id}]...")

        if not mimetype:
            if filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
                mimetype = "image/jpeg"
            elif filename.lower().endswith(".png"):
                mimetype = "image/png"
            elif filename.lower().endswith(".mp4"):
                mimetype = "video/mp4"
            else:
                mimetype = "application/octet-stream"

        file_metadata = {
            "name": filename,
            "parents": [self.folder_id]
        }
        media = MediaFileUpload(file_path, mimetype=mimetype, resumable=True)

        try:
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, name, webViewLink, webContentLink",
                supportsAllDrives=True
            ).execute()

            file_id = file.get("id")
            web_link = file.get("webViewLink")
            logger.info(f" Upload successful! File ID: {file_id}")
            logger.info(f" Direct File Link: {web_link}")

            try:
                self.service.permissions().create(
                    fileId=file_id,
                    body={"type": "anyone", "role": "reader"},
                    supportsAllDrives=True
                ).execute()
            except Exception as pe:
                logger.warning(f"Could not set public permission: {pe}")

            direct_view_link = f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk"
            logger.info(f" Direct File View Link: {direct_view_link}")
            return direct_view_link
        except Exception as e:
            logger.error(f"Failed to upload to Google Drive: {e}")
            return f"https://drive.google.com/drive/folders/{self.folder_id}"

if __name__ == "__main__":
    uploader = GDriveUploader()
    test_video = "/media/vpsg16gb/Workspace/lelehoctiengtrung_pinyin/output/videos/tiktok_pinyin_hsk_master_1080p.mp4"
    if os.path.exists(test_video):
        link = uploader.upload_file(test_video, "#1.HSK 1 • Đồ Ăn & Thức Uống.mp4")
        print("Upload Result:", link)
