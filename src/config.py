"""Configuration module for the Student Enrolment Agent.

Designed to work cross-platform (Windows/Git Bash/macOS/Linux).
Uses absolute paths resolved from the project root to avoid path issues.
"""

import os
import sys
from pathlib import Path

# Resolve project root directory (where main.py lives)
# This works regardless of where the script is run from
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=str(env_path))
        print(f"[Config] Loaded .env from: {env_path}")
    else:
        print(f"[Config] No .env file found at {env_path} (using defaults)")
except ImportError:
    print("[Config] python-dotenv not installed, using defaults/environment variables only")


class Config:
    """Application configuration loaded from environment variables.

    All file paths are resolved relative to the project root directory,
    ensuring they work correctly on Windows (Git Bash, CMD, PowerShell) and Unix.
    """

    # Project root (absolute path)
    ROOT_DIR = PROJECT_ROOT

    # Google API credentials - resolved as absolute paths
    GOOGLE_CREDENTIALS_PATH = str(
        PROJECT_ROOT / os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/credentials.json")
    )
    TOKEN_PATH = str(
        PROJECT_ROOT / os.getenv("TOKEN_PATH", "credentials/token.json")
    )

    # Gmail settings
    GMAIL_SEARCH_QUERY = os.getenv("GMAIL_SEARCH_QUERY", "subject:enrolment has:attachment")

    # Google Drive settings
    DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "")
    DRIVE_SEARCH_QUERY = os.getenv("DRIVE_SEARCH_QUERY", "enrolment")
    DRIVE_OUTPUT_FOLDER_ID = os.getenv("DRIVE_OUTPUT_FOLDER_ID", "")

    # Course settings
    MAX_STUDENTS_PER_COURSE = int(os.getenv("MAX_STUDENTS_PER_COURSE", "5"))
    COURSES = [
        course.strip()
        for course in os.getenv("COURSES", "Engineering,Design,Sports,IT Systems,Tourism").split(",")
    ]

    # Output settings - resolved as absolute path
    OUTPUT_DIR = str(PROJECT_ROOT / os.getenv("OUTPUT_DIR", "output"))

    # Supported file extensions for enrolment documents
    SUPPORTED_EXTENSIONS = [".xlsx", ".xls", ".csv"]

    @classmethod
    def display(cls):
        """Print current configuration for debugging."""
        print("=" * 60)
        print("  Student Enrolment Agent - Configuration")
        print("=" * 60)
        print(f"  Project Root:     {cls.ROOT_DIR}")
        print(f"  Credentials Path: {cls.GOOGLE_CREDENTIALS_PATH}")
        print(f"  Token Path:       {cls.TOKEN_PATH}")
        print(f"  Gmail Query:      {cls.GMAIL_SEARCH_QUERY}")
        print(f"  Drive Folder ID:  {cls.DRIVE_FOLDER_ID or '(not set)'}")
        print(f"  Drive Output:     {cls.DRIVE_OUTPUT_FOLDER_ID or '(not set - saves locally only)'}")
        print(f"  Drive Search:     {cls.DRIVE_SEARCH_QUERY}")
        print(f"  Max per Course:   {cls.MAX_STUDENTS_PER_COURSE}")
        print(f"  Courses:          {cls.COURSES}")
        print(f"  Output Dir:       {cls.OUTPUT_DIR}")
        print(f"  Platform:         {sys.platform}")
        print("=" * 60)

    @classmethod
    def check_credentials(cls) -> bool:
        """Check if credentials file exists and provide helpful guidance if not.

        Returns:
            True if credentials exist, False otherwise.
        """
        cred_path = Path(cls.GOOGLE_CREDENTIALS_PATH)

        if cred_path.exists():
            print(f"[Config] Credentials found at: {cred_path}")
            return True

        print("\n" + "!" * 60)
        print("  CREDENTIALS NOT FOUND")
        print("!" * 60)
        print(f"\n  Expected location: {cred_path}")
        print(f"\n  To fix this:")
        print(f"  1. Place your credentials.json file in:")
        print(f"     {cred_path.parent}{os.sep}")
        print(f"\n  On Git Bash (Windows), run:")
        print(f"     mkdir -p credentials")
        print(f"     cp ~/Downloads/credentials.json credentials/credentials.json")
        print(f"\n  On CMD/PowerShell (Windows), run:")
        print(f"     mkdir credentials")
        print(f"     copy %USERPROFILE%\\Downloads\\credentials.json credentials\\credentials.json")
        print(f"\n  Then run this script again.")
        print("!" * 60)
        return False
