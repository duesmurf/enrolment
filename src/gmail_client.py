"""Gmail integration module for retrieving enrolment documents."""

import os
import base64
import tempfile
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
        """
        creds = None

        # Check for existing token
        if os.path.exists(Config.TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(Config.TOKEN_PATH, SCOPES)

        # If no valid credentials, initiate auth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("[Gmail] Refreshing expired token...")
                creds.refresh(Request())
            else:
                if not os.path.exists(Config.GOOGLE_CREDENTIALS_PATH):
                    raise FileNotFoundError(
                        f"Credentials file not found at: {Config.GOOGLE_CREDENTIALS_PATH}\n"
                        "Please download your OAuth2 credentials from Google Cloud Console "
                        "and place them at the configured path."
                    )
                print("[Gmail] Starting OAuth2 authentication flow...")
                print("[Gmail] A browser window will open for authorization.")
                flow = InstalledAppFlow.from_client_secrets_file(
                    Config.GOOGLE_CREDENTIALS_PATH, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for future use
            os.makedirs(os.path.dirname(Config.TOKEN_PATH), exist_ok=True)
            with open(Config.TOKEN_PATH, "w") as token_file:
                token_file.write(creds.to_json())
            print("[Gmail] Token saved for future sessions.")

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

        Args:
            message_id: Gmail message ID.

        Returns:
            List of dicts with 'filename', 'attachment_id', 'mime_type', and 'size'.
        """
        message = self.get_email_details(message_id)
        attachments = []

        parts = message.get("payload", {}).get("parts", [])
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

        print(f"[Gmail] Downloaded attachment: {filename} -> {temp_file.name}")
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
                    print(f"[Gmail] Skipping non-spreadsheet attachment: {filename}")

        print(f"[Gmail] Total enrolment files downloaded: {len(downloaded_files)}")
        return downloaded_files
