"""Google Drive integration module for retrieving enrolment documents directly.

Works cross-platform (Windows Git Bash, CMD, PowerShell, macOS, Linux).
"""

import io
import os
import tempfile
from pathlib import Path
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

from .config import Config


# Google Drive API scopes - read and write access to files
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.readonly",
]


class DriveClient:
    """Handles Google Drive API authentication and file retrieval."""

    # MIME types for spreadsheets
    SPREADSHEET_MIME_TYPES = [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
        "application/vnd.ms-excel",  # .xls
        "text/csv",  # .csv
        "application/vnd.google-apps.spreadsheet",  # Google Sheets
    ]

    # Export format for Google Sheets (download as .xlsx)
    GOOGLE_SHEETS_EXPORT_TYPE = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    def __init__(self):
        self.service = None
        self.credentials = None

    def authenticate(self) -> None:
        """Authenticate with Google Drive API using OAuth2.

        Uses stored token if available, otherwise initiates OAuth2 flow.
        On first run, opens a browser for Google account authorization.
        """
        creds = None
        token_path = Path(Config.TOKEN_PATH)
        cred_path = Path(Config.GOOGLE_CREDENTIALS_PATH)

        # Check for existing token
        if token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
                print("[Drive] Found existing token.")
            except Exception as e:
                print(f"[Drive] Token file invalid, will re-authenticate: {e}")
                creds = None

        # If no valid credentials, initiate auth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("[Drive] Refreshing expired token...")
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"[Drive] Token refresh failed: {e}")
                    print("[Drive] Will re-authenticate from scratch...")
                    creds = None

            if not creds or not creds.valid:
                if not cred_path.exists():
                    Config.check_credentials()
                    raise FileNotFoundError(
                        f"Credentials file not found at: {cred_path}"
                    )

                print("[Drive] Starting OAuth2 authentication flow...")
                print("[Drive] A browser window will open - please sign in.")
                print()

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(cred_path), SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for future use
            token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(str(token_path), "w") as token_file:
                token_file.write(creds.to_json())
            print(f"[Drive] Token saved to: {token_path}")

        self.credentials = creds
        self.service = build("drive", "v3", credentials=creds)
        print("[Drive] Successfully authenticated.")

    def list_files_in_folder(self, folder_id: str) -> List[dict]:
        """List all spreadsheet files in a Google Drive folder.

        Args:
            folder_id: The Google Drive folder ID.
                       (from the URL: https://drive.google.com/drive/folders/FOLDER_ID)

        Returns:
            List of file metadata dicts with 'id', 'name', 'mimeType'.
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        print(f"[Drive] Searching for spreadsheets in folder: {folder_id}")

        # Build query for spreadsheet files in the folder
        mime_conditions = " or ".join(
            [f"mimeType='{mt}'" for mt in self.SPREADSHEET_MIME_TYPES]
        )
        query = f"'{folder_id}' in parents and ({mime_conditions}) and trashed=false"

        files = []
        page_token = None

        while True:
            results = (
                self.service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                    pageToken=page_token,
                )
                .execute()
            )

            files.extend(results.get("files", []))
            page_token = results.get("nextPageToken")
            if not page_token:
                break

        print(f"[Drive] Found {len(files)} spreadsheet(s) in folder.")
        for f in files:
            print(f"[Drive]   - {f['name']} ({f['mimeType']})")

        return files

    def search_files(self, search_query: str = "enrolment") -> List[dict]:
        """Search Google Drive for spreadsheet files matching a query.

        Args:
            search_query: Text to search for in file names. Default: "enrolment".

        Returns:
            List of file metadata dicts.
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        print(f"[Drive] Searching Drive for files containing: '{search_query}'")

        # Build query
        mime_conditions = " or ".join(
            [f"mimeType='{mt}'" for mt in self.SPREADSHEET_MIME_TYPES]
        )
        query = f"name contains '{search_query}' and ({mime_conditions}) and trashed=false"

        files = []
        page_token = None

        while True:
            results = (
                self.service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                    pageToken=page_token,
                )
                .execute()
            )

            files.extend(results.get("files", []))
            page_token = results.get("nextPageToken")
            if not page_token:
                break

        print(f"[Drive] Found {len(files)} matching file(s).")
        for f in files:
            print(f"[Drive]   - {f['name']} (modified: {f.get('modifiedTime', 'unknown')})")

        return files

    def download_file(self, file_id: str, file_name: str, mime_type: str) -> str:
        """Download a file from Google Drive to a temporary local file.

        Handles both regular files (.xlsx, .csv) and Google Sheets
        (exports as .xlsx).

        Args:
            file_id: Google Drive file ID.
            file_name: Original file name.
            mime_type: MIME type of the file.

        Returns:
            Path to the downloaded temporary file.
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        # Determine if this is a Google Sheets file (needs export) or regular file
        if mime_type == "application/vnd.google-apps.spreadsheet":
            # Export Google Sheets as .xlsx
            request = self.service.files().export_media(
                fileId=file_id, mimeType=self.GOOGLE_SHEETS_EXPORT_TYPE
            )
            ext = ".xlsx"
        else:
            # Download regular file directly
            request = self.service.files().get_media(fileId=file_id)
            _, ext = os.path.splitext(file_name)
            if not ext:
                ext = ".xlsx"

        # Download to temp file
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, suffix=ext, prefix="enrolment_drive_"
        )

        downloader = MediaIoBaseDownload(temp_file, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"[Drive] Downloading {file_name}: {int(status.progress() * 100)}%")

        temp_file.close()
        print(f"[Drive] Downloaded: {file_name} -> {temp_file.name}")
        return temp_file.name

    def retrieve_enrolment_files(
        self, folder_id: Optional[str] = None, search_query: Optional[str] = None
    ) -> List[str]:
        """High-level method: find and download enrolment spreadsheets from Drive.

        Can work in two modes:
            1. Folder mode: Download all spreadsheets from a specific folder
            2. Search mode: Search Drive for files matching a query

        Args:
            folder_id: Google Drive folder ID. If provided, lists files in folder.
            search_query: Search term for file names. Used if folder_id is None.

        Returns:
            List of file paths to downloaded enrolment spreadsheets.
        """
        if folder_id:
            files = self.list_files_in_folder(folder_id)
        else:
            query = search_query or Config.DRIVE_SEARCH_QUERY
            files = self.search_files(query)

        if not files:
            return []

        downloaded_files = []
        for file_info in files:
            try:
                file_path = self.download_file(
                    file_info["id"], file_info["name"], file_info["mimeType"]
                )
                downloaded_files.append(file_path)
            except Exception as e:
                print(f"[Drive] ERROR downloading {file_info['name']}: {e}")

        print(f"\n[Drive] Total files downloaded: {len(downloaded_files)}")
        return downloaded_files

    def upload_file(self, local_path: str, folder_id: Optional[str] = None,
                    convert_to_sheets: bool = False) -> dict:
        """Upload a local file to Google Drive.

        Args:
            local_path: Path to the local file to upload.
            folder_id: Google Drive folder ID to upload into.
                       If None, uploads to root of Drive.
            convert_to_sheets: If True, converts .xlsx/.csv to Google Sheets format.

        Returns:
            Dict with 'id', 'name', and 'webViewLink' of the uploaded file.
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        file_name = os.path.basename(local_path)
        _, ext = os.path.splitext(file_name.lower())

        # Determine MIME type
        mime_types = {
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".csv": "text/csv",
        }
        mime_type = mime_types.get(ext, "application/octet-stream")

        # File metadata
        file_metadata = {"name": file_name}

        if folder_id:
            file_metadata["parents"] = [folder_id]

        if convert_to_sheets:
            file_metadata["mimeType"] = "application/vnd.google-apps.spreadsheet"

        # Upload
        media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)

        file = (
            self.service.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id, name, webViewLink",
            )
            .execute()
        )

        link = file.get("webViewLink", f"https://drive.google.com/file/d/{file['id']}")
        print(f"[Drive] Uploaded: {file_name}")
        print(f"[Drive]   Link: {link}")

        return file

    def upload_output_files(self, file_paths: List[str], folder_id: Optional[str] = None,
                            convert_to_sheets: bool = True) -> List[dict]:
        """Upload multiple output files to Google Drive.

        Args:
            file_paths: List of local file paths to upload.
            folder_id: Google Drive folder ID to upload into.
                       Uses DRIVE_OUTPUT_FOLDER_ID from config if not specified.
            convert_to_sheets: If True, converts spreadsheets to Google Sheets.

        Returns:
            List of uploaded file metadata dicts.
        """
        upload_folder = folder_id or Config.DRIVE_OUTPUT_FOLDER_ID

        if upload_folder:
            print(f"[Drive] Uploading {len(file_paths)} file(s) to folder: {upload_folder}")
        else:
            print(f"[Drive] Uploading {len(file_paths)} file(s) to Drive root")

        uploaded = []
        for path in file_paths:
            if not os.path.exists(path):
                print(f"[Drive] Skipping (not found): {path}")
                continue
            try:
                result = self.upload_file(
                    path,
                    folder_id=upload_folder,
                    convert_to_sheets=convert_to_sheets,
                )
                uploaded.append(result)
            except Exception as e:
                print(f"[Drive] ERROR uploading {path}: {e}")

        print(f"\n[Drive] Successfully uploaded: {len(uploaded)} file(s)")
        return uploaded
