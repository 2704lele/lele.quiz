import os
import hashlib
import json
import logging
from typing import Optional
from google.oauth2.credentials import Credentials as UserCredentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
try:
    from multilevelsquiz.src.config import config
except ImportError:
    from src.config import config

logger = logging.getLogger("GDriveUploader")

TARGET_FOLDER_ID = "17xOkiW-XOWRDK2CCwNEl_rlf1rGKqKXm"

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
        vault_oauth_file = os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/google_oauth/user_oauth2.json")
        for fpath in [oauth_file, vault_oauth_file]:
            if not (client_id and client_secret and refresh_token) and os.path.exists(fpath):
                try:
                    with open(fpath, "r") as f:
                        oauth_data = json.load(f)
                        client_id = client_id or oauth_data.get("client_id")
                        client_secret = client_secret or oauth_data.get("client_secret")
                        refresh_token = refresh_token or oauth_data.get("refresh_token")
                except Exception as e:
                    logger.warning(f"Could not read {fpath}: {e}")

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
                logger.info("Authenticated via GCP_SERVICE_ACCOUNT_JSON env.")
                return
            except Exception as e:
                logger.warning(f"Failed to load SA from env: {e}")

        for path in config.creds_paths:
            if path and os.path.exists(path) and os.path.getsize(path) > 10:
                try:
                    sa_creds = ServiceAccountCredentials.from_service_account_file(path, scopes=scopes)
                    self.service = build("drive", "v3", credentials=sa_creds)
                    logger.info(f"Authenticated via SA file: {path}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to authenticate with SA file {path}: {e}")

        raise RuntimeError("Could not authenticate to Google Drive with any method!")

    def upload_file(self, local_path: str, filename: Optional[str] = None, subfolder_name: Optional[str] = None) -> str:
        """
        Uploads local file to Google Drive and returns direct playable URL:
        https://drive.google.com/file/d/{FILE_ID}/view?usp=drivesdk
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")

        file_name = filename or os.path.basename(local_path)
        target_folder = self.folder_id

        if subfolder_name:
            target_folder = self.get_or_create_subfolder(subfolder_name, parent_id=self.folder_id)

        file_metadata = {
            "name": file_name,
            "parents": [target_folder]
        }

        media = MediaFileUpload(local_path, resumable=True)
        logger.info(f"Uploading {file_name} to Google Drive folder '{target_folder}'...")

        try:
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, webViewLink, webContentLink",
                supportsAllDrives=True
            ).execute()

            file_id = file.get("id")
            logger.info(f"File uploaded successfully! File ID: {file_id}")

            try:
                self.service.permissions().create(
                    fileId=file_id,
                    body={"role": "reader", "type": "anyone"},
                    fields="id",
                    supportsAllDrives=True
                ).execute()
            except Exception as pe:
                logger.warning(f"Could not set public permission: {pe}")

            direct_link = f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk"
            return direct_link
        except Exception as e:
            logger.error(f"CRITICAL: Failed to upload file to Google Drive: {e}")
            raise RuntimeError(f"Google Drive upload failed: {e}") from e

    def get_or_create_subfolder(self, folder_name: str, parent_id: str) -> str:
        try:
            query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and '{parent_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            items = results.get('files', [])

            if items:
                return items[0]['id']

            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id',
                supportsAllDrives=True
            ).execute()
            return folder.get('id', parent_id)
        except Exception as fe:
            logger.warning(f"Could not get or create subfolder '{folder_name}': {fe}. Using parent folder.")
            return parent_id
