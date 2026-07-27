"""
Student Enrolment Agent - Main Orchestrator

This agent connects to Gmail, retrieves student enrolment spreadsheets,
processes the documents, and allocates students to courses based on their
ranked preferences (max 5 students per course).

Usage:
    python main.py                   # Full pipeline: Gmail -> Process -> Allocate -> Output
    python main.py --local FILE      # Process a local file (skip Gmail)
    python main.py --help            # Show help
"""

import argparse
import os
import sys
import tempfile

from src.config import Config
from src.gmail_client import GmailClient
from src.spreadsheet_processor import SpreadsheetProcessor
from src.allocation_engine import AllocationEngine
from src.output_generator import OutputGenerator


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

    # Step 1: Connect to Gmail and retrieve enrolment files
    print("\n[Step 1/4] Connecting to Gmail and retrieving enrolment files...")
    gmail = GmailClient()
    gmail.authenticate()
    file_paths = gmail.retrieve_enrolment_files(query)

    if not file_paths:
        print("\n[!] No enrolment files found. Please check your Gmail search query.")
        print(f"    Current query: '{query or Config.GMAIL_SEARCH_QUERY}'")
        print("    Tip: Ensure emails with spreadsheet attachments exist matching the query.")
        return

    # Step 2: Process spreadsheet files
    print("\n[Step 2/4] Processing enrolment spreadsheets...")
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

    print(f"\n[Done] Output files saved to: {Config.OUTPUT_DIR}/")
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

    # Validate file paths
    valid_paths = []
    for path in file_paths:
        if not os.path.exists(path):
            print(f"[!] File not found: {path}")
        else:
            valid_paths.append(path)

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

    print(f"\n[Done] Output files saved to: {Config.OUTPUT_DIR}/")
    print("=" * 60)


def run_demo():
    """Run a demonstration with sample data to verify the system works."""
    print("\n" + "=" * 60)
    print("  STUDENT ENROLMENT AGENT")
    print("  Demo Mode (sample data)")
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
    print(f"[Demo] File: {temp_file.name}")

    # Run local mode with the demo file
    run_local_mode([temp_file.name])

    # Cleanup
    os.unlink(temp_file.name)


def _cleanup_temp_files(file_paths: list):
    """Remove temporary downloaded files.

    Args:
        file_paths: List of temp file paths to clean up.
    """
    for path in file_paths:
        try:
            if os.path.exists(path) and tempfile.gettempdir() in path:
                os.unlink(path)
        except OSError:
            pass


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Student Enrolment Agent - Automatically sort students into courses",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Full pipeline (Gmail -> Allocate -> Output)
  python main.py --local enrolment.xlsx   # Process a local file
  python main.py --local file1.csv file2.xlsx  # Process multiple files
  python main.py --demo                   # Run with sample data
  python main.py --query "from:admin subject:enrolment"  # Custom Gmail search
  python main.py --format csv             # Output as CSV only
        """,
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
        help="Output file format (default: both)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run a demonstration with sample data",
    )

    args = parser.parse_args()

    if args.demo:
        run_demo()
    elif args.local:
        run_local_mode(args.local, output_format=args.format)
    else:
        run_full_pipeline(query=args.query, output_format=args.format)


if __name__ == "__main__":
    main()
