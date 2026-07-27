"""Gmail integration module for retrieving enrolment documents.

Works cross-platform (Windows Git Bash, CMD, PowerShell, macOS, Linux).
"""

import os
import base64
import tempfile
from pathlib import Path
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .config import Config


# Gmail API scopes - read-only access to messages
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailClient:
    """Handles Gmail API authentication and email retrieval."""

    def __init__(self):
        self.service = None
        self.credentials = None

    def authenticate(self) -> None:
        """Authenticate with Gmail API using OAuth2.

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
                print("[Gmail] Found existing token.")
            except Exception as e:
                print(f"[Gmail] Token file invalid, will re-authenticate: {e}")
                creds = None

        # If no valid credentials, initiate auth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("[Gmail] Refreshing expired token...")
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"[Gmail] Token refresh failed: {e}")
                    print("[Gmail] Will re-authenticate from scratch...")
                    creds = None

            if not creds or not creds.valid:
                # Need fresh authentication
                if not cred_path.exists():
                    # Use the config check which gives platform-specific guidance
                    Config.check_credentials()
                    raise FileNotFoundError(
                        f"Credentials file not found at: {cred_path}"
                    )

                print("[Gmail] Starting OAuth2 authentication flow...")
                print("[Gmail] A browser window will open - please sign in with your Google account.")
                print("[Gmail] (If the browser doesn't open automatically, check the URL in the terminal)")
                print()

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(cred_path), SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for future use
            token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(str(token_path), "w") as token_file:
                token_file.write(creds.to_json())
            print(f"[Gmail] Token saved to: {token_path}")

        self.credentials = creds
        self.service = build("gmail", "v1", credentials=creds)
        print("[Gmail] Successfully authenticated.")

    def search_emails(self, query: Optional[str] = None) -> List[dict]:
        """Search Gmail for emails matching the query.

        Args:
            query: Gmail search query string. Uses config default if not provided.

        Returns:
            List of message metadata dicts with 'id' and 'threadId'.
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        search_query = query or Config.GMAIL_SEARCH_QUERY
        print(f"[Gmail] Searching emails with query: '{search_query}'")

        messages = []
        page_token = None

        while True:
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=search_query, pageToken=page_token)
                .execute()
            )

            if "messages" in results:
                messages.extend(results["messages"])

            page_token = results.get("nextPageToken")
            if not page_token:
                break

        print(f"[Gmail] Found {len(messages)} email(s) matching query.")
        return messages

    def get_email_details(self, message_id: str) -> dict:
        """Get full email details including headers and parts.

        Args:
            message_id: Gmail message ID.

        Returns:
            Full message resource dict.
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        message = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        return message

    def get_attachments(self, message_id: str) -> List[dict]:
        """Extract attachment metadata from a message.

        Handles nested MIME parts (multipart messages).

        Args:
            message_id: Gmail message ID.

        Returns:
            List of dicts with 'filename', 'attachment_id', 'mime_type', and 'size'.
        """
        message = self.get_email_details(message_id)
        attachments = []

        def _extract_parts(parts):
            """Recursively extract attachments from message parts."""
            for part in parts:
                filename = part.get("filename", "")
                if filename and part.get("body", {}).get("attachmentId"):
                    attachment_info = {
                        "filename": filename,
                        "attachment_id": part["body"]["attachmentId"],
                        "mime_type": part.get("mimeType", ""),
                        "size": part["body"].get("size", 0),
                    }
                    attachments.append(attachment_info)
                # Check nested parts (multipart messages)
                if "parts" in part:
                    _extract_parts(part["parts"])

        parts = message.get("payload", {}).get("parts", [])
        _extract_parts(parts)

        return attachments

    def download_attachment(self, message_id: str, attachment_id: str, filename: str) -> str:
        """Download an attachment and save it to a temporary file.

        Args:
            message_id: Gmail message ID.
            attachment_id: Attachment ID within the message.
            filename: Original filename for the attachment.

        Returns:
            Path to the downloaded temporary file.
        """
        if not self.service:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        # Fetch the attachment data
        attachment = (
            self.service.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=attachment_id)
            .execute()
        )

        # Decode the base64url-encoded data
        file_data = base64.urlsafe_b64decode(attachment["data"])

        # Save to a temp file preserving the original extension
        _, ext = os.path.splitext(filename)
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, suffix=ext, prefix="enrolment_"
        )
        temp_file.write(file_data)
        temp_file.close()

        print(f"[Gmail] Downloaded: {filename} ({len(file_data)} bytes)")
        return temp_file.name

    def retrieve_enrolment_files(self, query: Optional[str] = None) -> List[str]:
        """High-level method: search emails and download all spreadsheet attachments.

        Args:
            query: Optional custom search query.

        Returns:
            List of file paths to downloaded enrolment spreadsheets.
        """
        downloaded_files = []
        messages = self.search_emails(query)

        if not messages:
            return downloaded_files

        for msg in messages:
            message_id = msg["id"]
            attachments = self.get_attachments(message_id)

            for att in attachments:
                filename = att["filename"]
                _, ext = os.path.splitext(filename.lower())

                if ext in Config.SUPPORTED_EXTENSIONS:
                    file_path = self.download_attachment(
                        message_id, att["attachment_id"], filename
                    )
                    downloaded_files.append(file_path)
                else:
                    print(f"[Gmail] Skipping non-spreadsheet: {filename}")

        print(f"\n[Gmail] Total enrolment files downloaded: {len(downloaded_files)}")
        return downloaded_files
