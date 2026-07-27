"""Configuration module for the Student Enrolment Agent."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # Google API credentials
    GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/credentials.json")
    TOKEN_PATH = os.getenv("TOKEN_PATH", "credentials/token.json")

    # Gmail settings
    GMAIL_SEARCH_QUERY = os.getenv("GMAIL_SEARCH_QUERY", "subject:enrolment has:attachment")

    # Course settings
    MAX_STUDENTS_PER_COURSE = int(os.getenv("MAX_STUDENTS_PER_COURSE", "5"))
    COURSES = [
        course.strip()
        for course in os.getenv("COURSES", "Engineering,Design,Sports,IT Systems,Tourism").split(",")
    ]

    # Output settings
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

    # Supported file extensions for enrolment documents
    SUPPORTED_EXTENSIONS = [".xlsx", ".xls", ".csv"]

    @classmethod
    def display(cls):
        """Print current configuration for debugging."""
        print("=" * 50)
        print("Student Enrolment Agent Configuration")
        print("=" * 50)
        print(f"  Credentials Path: {cls.GOOGLE_CREDENTIALS_PATH}")
        print(f"  Token Path:       {cls.TOKEN_PATH}")
        print(f"  Gmail Query:      {cls.GMAIL_SEARCH_QUERY}")
        print(f"  Max per Course:   {cls.MAX_STUDENTS_PER_COURSE}")
        print(f"  Courses:          {cls.COURSES}")
        print(f"  Output Dir:       {cls.OUTPUT_DIR}")
        print("=" * 50)
