#!/usr/bin/env python3
"""
Student Enrolment Agent - Main Orchestrator

This agent connects to Gmail, retrieves student enrolment spreadsheets,
processes the documents, and allocates students to courses based on their
ranked preferences (max 5 students per course).

Works on: Windows (Git Bash, CMD, PowerShell), macOS, Linux

Usage:
    python main.py                   # Full pipeline: Gmail -> Process -> Allocate -> Output
    python main.py --local FILE      # Process a local file (skip Gmail)
    python main.py --demo            # Run with sample data (no Gmail needed)
    python main.py --setup           # Check setup and credentials
    python main.py --help            # Show help
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

# Ensure the project root is in the Python path (fixes import issues on Windows)
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import Config
from src.gmail_client import GmailClient
from src.spreadsheet_processor import SpreadsheetProcessor
from src.allocation_engine import AllocationEngine
from src.output_generator import OutputGenerator
from src.scheduler import AgentScheduler


def run_setup_check():
    """Check the environment setup and provide guidance.

    Verifies:
        - Python version
        - Required packages installed
        - Credentials file exists
        - Output directory is writable
    """
    print("\n" + "=" * 60)
    print("  STUDENT ENROLMENT AGENT - Setup Check")
    print("=" * 60)

    issues = []

    # Python version
    py_version = sys.version_info
    print(f"\n  [1/5] Python Version: {py_version.major}.{py_version.minor}.{py_version.micro}")
    if py_version < (3, 8):
        issues.append("Python 3.8+ required")
        print("        FAIL - Need Python 3.8 or higher")
    else:
        print("        OK")

    # Required packages
    print(f"\n  [2/5] Required Packages:")
    packages = {
        "google.oauth2": "google-auth-oauthlib",
        "googleapiclient": "google-api-python-client",
        "pandas": "pandas",
        "openpyxl": "openpyxl",
    }
    all_packages_ok = True
    for module, pip_name in packages.items():
        try:
            __import__(module)
            print(f"        {pip_name}: OK")
        except ImportError:
            print(f"        {pip_name}: MISSING")
            issues.append(f"Install: pip install {pip_name}")
            all_packages_ok = False

    if not all_packages_ok:
        print(f"\n        Fix: pip install -r requirements.txt")

    # Credentials
    print(f"\n  [3/5] Google Credentials:")
    cred_path = Path(Config.GOOGLE_CREDENTIALS_PATH)
    if cred_path.exists():
        print(f"        Found at: {cred_path}")
        print("        OK")
    else:
        print(f"        NOT FOUND at: {cred_path}")
        print(f"        Fix: Place credentials.json in the credentials/ folder")
        issues.append("Missing credentials.json")

    # Token (optional - created on first auth)
    print(f"\n  [4/5] Auth Token:")
    token_path = Path(Config.TOKEN_PATH)
    if token_path.exists():
        print(f"        Found at: {token_path}")
        print("        OK (already authenticated)")
    else:
        print("        Not found (will be created on first run)")
        print("        OK")

    # Output directory
    print(f"\n  [5/5] Output Directory:")
    output_dir = Path(Config.OUTPUT_DIR)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"        {output_dir}")
        print("        OK (writable)")
    except PermissionError:
        print(f"        Cannot create: {output_dir}")
        issues.append("Output directory not writable")

    # Summary
    print("\n" + "=" * 60)
    if issues:
        print(f"  ISSUES FOUND ({len(issues)}):")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("  ALL CHECKS PASSED - Ready to run!")
        print(f"\n  Next step: python main.py --demo     (test with sample data)")
        print(f"             python main.py             (run full Gmail pipeline)")
    print("=" * 60 + "\n")

    return len(issues) == 0


def run_full_pipeline(query: str = None, output_format: str = "both"):
    """Run the complete pipeline: Gmail retrieval -> Processing -> Allocation -> Output.

    Args:
        query: Custom Gmail search query. Uses config default if None.
        output_format: Output file format ('xlsx', 'csv', or 'both').
    """
    print("\n" + "=" * 60)
    print("  STUDENT ENROLMENT AGENT")
    print("  Full Pipeline Mode")
    print("=" * 60)
    Config.display()

    # Pre-flight check: ensure credentials exist
    if not Config.check_credentials():
        sys.exit(1)

    # Step 1: Connect to Gmail and retrieve enrolment files
    print("\n[Step 1/4] Connecting to Gmail and retrieving enrolment files...")
    gmail = GmailClient()
    gmail.authenticate()
    file_paths = gmail.retrieve_enrolment_files(query)

    if not file_paths:
        print("\n[!] No enrolment files found. Please check your Gmail search query.")
        print(f"    Current query: '{query or Config.GMAIL_SEARCH_QUERY}'")
        print("    Tip: Ensure emails with spreadsheet attachments exist matching the query.")
        print("\n    To change the search query, edit .env or use --query flag:")
        print('    python main.py --query "from:admin subject:student list"')
        return

    # Step 2: Process spreadsheet files
    print(f"\n[Step 2/4] Processing {len(file_paths)} enrolment spreadsheet(s)...")
    processor = SpreadsheetProcessor()
    students = processor.process_files(file_paths)

    if not students:
        print("\n[!] No student records found in the downloaded files.")
        print("    Tip: Ensure files have columns like 'Name', 'First Choice', etc.")
        return

    # Step 3: Allocate students to courses
    print("\n[Step 3/4] Allocating students to courses...")
    engine = AllocationEngine()
    result = engine.allocate(students)

    # Step 4: Generate output files
    print("\n[Step 4/4] Generating output files...")
    output = OutputGenerator()
    output.generate_placement_file(result, format=output_format)
    output.generate_detailed_report(result)
    output.print_console_summary(result)

    # Cleanup temp files
    _cleanup_temp_files(file_paths)

    print(f"\n[Done] Output files saved to: {Config.OUTPUT_DIR}")
    print("=" * 60)


def run_local_mode(file_paths: list, output_format: str = "both"):
    """Run the pipeline on local file(s), skipping Gmail retrieval.

    Args:
        file_paths: List of local spreadsheet file paths.
        output_format: Output file format ('xlsx', 'csv', or 'both').
    """
    print("\n" + "=" * 60)
    print("  STUDENT ENROLMENT AGENT")
    print("  Local File Mode")
    print("=" * 60)
    Config.display()

    # Validate and resolve file paths (handle Git Bash / Windows path differences)
    valid_paths = []
    for filepath in file_paths:
        resolved = Path(filepath).resolve()
        if resolved.exists():
            valid_paths.append(str(resolved))
        else:
            # Also try relative to project root
            alt_path = PROJECT_ROOT / filepath
            if alt_path.exists():
                valid_paths.append(str(alt_path))
            else:
                print(f"[!] File not found: {filepath}")
                print(f"    Tried: {resolved}")
                print(f"    Also tried: {alt_path}")

    if not valid_paths:
        print("\n[!] No valid files to process.")
        return

    # Step 1: Process spreadsheet files
    print(f"\n[Step 1/3] Processing {len(valid_paths)} enrolment file(s)...")
    processor = SpreadsheetProcessor()
    students = processor.process_files(valid_paths)

    if not students:
        print("\n[!] No student records found in the provided files.")
        print("    Tip: Ensure files have columns like 'Name', 'First Choice', etc.")
        return

    # Step 2: Allocate students to courses
    print("\n[Step 2/3] Allocating students to courses...")
    engine = AllocationEngine()
    result = engine.allocate(students)

    # Step 3: Generate output files
    print("\n[Step 3/3] Generating output files...")
    output = OutputGenerator()
    output.generate_placement_file(result, format=output_format)
    output.generate_detailed_report(result)
    output.print_console_summary(result)

    print(f"\n[Done] Output files saved to: {Config.OUTPUT_DIR}")
    print("=" * 60)


def run_demo():
    """Run a demonstration with sample data to verify the system works.

    No Gmail credentials needed - uses built-in sample data.
    """
    print("\n" + "=" * 60)
    print("  STUDENT ENROLMENT AGENT")
    print("  Demo Mode (no Gmail needed)")
    print("=" * 60)

    import pandas as pd

    # Create sample enrolment data matching the expected format
    sample_data = {
        "Name": [
            "Casey", "Jordan", "Alex", "Taylor", "Morgan",
            "Riley", "Quinn", "Blake", "Drew", "Sage",
            "Harper", "Avery",
        ],
        "First Choice": [
            "Engineering", "Design", "Sports", "IT Systems", "Tourism",
            "Engineering", "Design", "Sports", "IT Systems", "Tourism",
            "Engineering", "Engineering",
        ],
        "Second Choice": [
            "Design", "Sports", "IT Systems", "Tourism", "Engineering",
            "Design", "Sports", "Engineering", "Tourism", "Design",
            "Design", "Sports",
        ],
        "Third Choice": [
            "Sports", "IT Systems", "Tourism", "Engineering", "Design",
            "Sports", "IT Systems", "Tourism", "Engineering", "Sports",
            "Sports", "IT Systems",
        ],
        "Fourth Choice": [
            "IT Systems", "Tourism", "Engineering", "Design", "Sports",
            "IT Systems", "Tourism", "Design", "Sports", "IT Systems",
            "IT Systems", "Tourism",
        ],
        "Fifth Choice": [
            "Tourism", "Engineering", "Design", "Sports", "IT Systems",
            "Tourism", "Engineering", "IT Systems", "Design", "Engineering",
            "Tourism", "Design",
        ],
    }

    # Save to a temp CSV file
    temp_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, prefix="demo_enrolment_"
    )
    df = pd.DataFrame(sample_data)
    df.to_csv(temp_file.name, index=False)
    temp_file.close()

    print(f"\n[Demo] Created sample file with {len(sample_data['Name'])} students")

    # Run local mode with the demo file
    run_local_mode([temp_file.name])

    # Cleanup
    try:
        os.unlink(temp_file.name)
    except OSError:
        pass


def _cleanup_temp_files(file_paths: list):
    """Remove temporary downloaded files.

    Args:
        file_paths: List of temp file paths to clean up.
    """
    temp_dir = tempfile.gettempdir()
    for filepath in file_paths:
        try:
            if os.path.exists(filepath) and temp_dir in str(Path(filepath).resolve()):
                os.unlink(filepath)
        except OSError:
            pass


def run_auto_mode(interval: int = 30, query: str = None, output_format: str = "both"):
    """Run the agent automatically on a repeating schedule.

    Args:
        interval: Minutes between each run.
        query: Custom Gmail search query.
        output_format: Output file format.
    """
    scheduler = AgentScheduler(interval_minutes=interval)
    scheduler.run(
        run_full_pipeline,
        query=query,
        output_format=output_format,
    )


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Student Enrolment Agent - Automatically sort students into courses",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples (works in Git Bash, CMD, PowerShell, or Terminal):

  python main.py --setup                  # Check your setup first
  python main.py --demo                   # Test with sample data (no Gmail)
  python main.py                          # Full pipeline (one-time run)
  python main.py --auto                   # Auto mode: runs every 30 minutes
  python main.py --auto --interval 10     # Auto mode: runs every 10 minutes
  python main.py --local enrolment.xlsx   # Process a local file directly
  python main.py --query "from:admin subject:enrolment"  # Custom Gmail search
  python main.py --format csv             # Output as CSV only
        """,
    )

    parser.add_argument(
        "--setup",
        action="store_true",
        help="Check setup: Python, packages, credentials, and configuration",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run continuously, checking Gmail at regular intervals (default: every 30 min)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        metavar="MINUTES",
        help="Minutes between auto-runs (default: 30). Use with --auto",
    )
    parser.add_argument(
        "--local",
        nargs="+",
        metavar="FILE",
        help="Process local spreadsheet file(s) instead of fetching from Gmail",
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Custom Gmail search query (overrides .env setting)",
    )
    parser.add_argument(
        "--format",
        choices=["xlsx", "csv", "both"],
        default="both",
        help="Output file format (default: both xlsx and csv)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run a demo with sample data (no Gmail credentials needed)",
    )

    args = parser.parse_args()

    if args.setup:
        run_setup_check()
    elif args.demo:
        run_demo()
    elif args.auto:
        run_auto_mode(
            interval=args.interval,
            query=args.query,
            output_format=args.format,
        )
    elif args.local:
        run_local_mode(args.local, output_format=args.format)
    else:
        run_full_pipeline(query=args.query, output_format=args.format)


if __name__ == "__main__":
    main()
