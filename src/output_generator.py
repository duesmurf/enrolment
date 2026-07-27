"""Output generation module for creating placement summary files."""

import os
from datetime import datetime
from typing import Optional

import pandas as pd

from .config import Config
from .allocation_engine import AllocationResult


class OutputGenerator:
    """Generates placement summary files in various formats.

    Output matches the summary placement format:
        S/N | Name | Course
    """

    def __init__(self, output_dir: Optional[str] = None):
        """
        Args:
            output_dir: Directory to save output files. Defaults to Config value.
        """
        self.output_dir = output_dir or Config.OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_placement_file(
        self, result: AllocationResult, filename: Optional[str] = None, format: str = "xlsx"
    ) -> str:
        """Generate a placement summary spreadsheet.

        Creates a file with columns: S/N, Name, Course
        matching the expected output format.

        Args:
            result: AllocationResult from the allocation engine.
            filename: Custom filename (without extension). Auto-generated if not provided.
            format: Output format - 'xlsx', 'csv', or 'both'. Defaults to 'xlsx'.

        Returns:
            Path to the generated file.
        """
        # Get flat placement list
        placements = result.get_flat_placements()

        # Build the DataFrame matching the expected format
        data = []
        for i, placement in enumerate(placements, 1):
            data.append({
                "S/N": i,
                "Name": placement["name"],
                "Course": placement["course"],
            })

        df = pd.DataFrame(data, columns=["S/N", "Name", "Course"])

        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"placement_summary_{timestamp}"

        # Save in requested format(s)
        output_paths = []

        if format in ("xlsx", "both"):
            xlsx_path = os.path.join(self.output_dir, f"{filename}.xlsx")
            df.to_excel(xlsx_path, index=False, engine="openpyxl")
            output_paths.append(xlsx_path)
            print(f"[Output] Generated Excel file: {xlsx_path}")

        if format in ("csv", "both"):
            csv_path = os.path.join(self.output_dir, f"{filename}.csv")
            df.to_csv(csv_path, index=False)
            output_paths.append(csv_path)
            print(f"[Output] Generated CSV file: {csv_path}")

        return output_paths[0] if len(output_paths) == 1 else output_paths

    def generate_detailed_report(
        self, result: AllocationResult, filename: Optional[str] = None
    ) -> str:
        """Generate a detailed allocation report with per-course sheets.

        Creates an Excel workbook with:
            - 'Summary' sheet: S/N, Name, Course (all placements)
            - One sheet per course: S/N, Name
            - 'Unplaced' sheet: students who couldn't be placed

        Args:
            result: AllocationResult from the allocation engine.
            filename: Custom filename (without extension).

        Returns:
            Path to the generated Excel file.
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"detailed_report_{timestamp}"

        output_path = os.path.join(self.output_dir, f"{filename}.xlsx")

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            # Summary sheet
            placements = result.get_flat_placements()
            summary_data = []
            for i, p in enumerate(placements, 1):
                summary_data.append({"S/N": i, "Name": p["name"], "Course": p["course"]})

            summary_df = pd.DataFrame(summary_data, columns=["S/N", "Name", "Course"])
            summary_df.to_excel(writer, sheet_name="Summary", index=False)

            # Per-course sheets
            for course in sorted(result.placements.keys()):
                students = sorted(result.placements[course])
                course_data = []
                for i, student in enumerate(students, 1):
                    course_data.append({"S/N": i, "Name": student})

                course_df = pd.DataFrame(course_data, columns=["S/N", "Name"])
                # Truncate sheet name to Excel's 31-char limit
                sheet_name = course[:31]
                course_df.to_excel(writer, sheet_name=sheet_name, index=False)

            # Unplaced students sheet
            if result.unplaced:
                unplaced_data = []
                for i, (name, prefs) in enumerate(result.unplaced, 1):
                    unplaced_data.append({
                        "S/N": i,
                        "Name": name,
                        "Preferences": ", ".join(prefs),
                    })

                unplaced_df = pd.DataFrame(
                    unplaced_data, columns=["S/N", "Name", "Preferences"]
                )
                unplaced_df.to_excel(writer, sheet_name="Unplaced", index=False)

        print(f"[Output] Generated detailed report: {output_path}")
        return output_path

    def print_console_summary(self, result: AllocationResult) -> None:
        """Print a formatted summary to the console.

        Args:
            result: AllocationResult from the allocation engine.
        """
        print(result.summary())

        # Also print the allocation log for transparency
        if result.allocation_log:
            print("\n  Allocation Details:")
            for entry in result.allocation_log:
                print(f"    {entry}")
