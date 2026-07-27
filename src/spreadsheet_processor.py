"""Spreadsheet processing module for parsing enrolment documents."""

import os
from typing import List, Dict, Optional

import pandas as pd

from .config import Config


class StudentRecord:
    """Represents a single student's enrolment record with course preferences."""

    def __init__(self, name: str, preferences: List[str]):
        """
        Args:
            name: Student's full name.
            preferences: Ordered list of course preferences (1st choice first).
        """
        self.name = name.strip()
        self.preferences = [p.strip() for p in preferences if p and str(p).strip()]

    def __repr__(self):
        return f"StudentRecord(name='{self.name}', preferences={self.preferences})"

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "preferences": self.preferences,
        }


class SpreadsheetProcessor:
    """Handles reading and parsing of enrolment spreadsheet files."""

    # Expected column name patterns for auto-detection
    NAME_COLUMNS = ["name", "student name", "student", "full name"]
    CHOICE_COLUMNS = [
        "first choice", "second choice", "third choice",
        "fourth choice", "fifth choice",
        "1st choice", "2nd choice", "3rd choice",
        "4th choice", "5th choice",
        "choice 1", "choice 2", "choice 3",
        "choice 4", "choice 5",
    ]

    def process_file(self, file_path: str) -> List[StudentRecord]:
        """Process a single spreadsheet file and extract student records.

        Args:
            file_path: Path to the spreadsheet file (.xlsx, .xls, or .csv).

        Returns:
            List of StudentRecord objects.

        Raises:
            ValueError: If file format is unsupported or data cannot be parsed.
        """
        _, ext = os.path.splitext(file_path.lower())

        if ext == ".csv":
            df = pd.read_csv(file_path)
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_path, engine="openpyxl")
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        print(f"[Processor] Loaded file: {file_path}")
        print(f"[Processor] Columns found: {list(df.columns)}")
        print(f"[Processor] Rows: {len(df)}")

        return self._parse_dataframe(df)

    def process_files(self, file_paths: List[str]) -> List[StudentRecord]:
        """Process multiple spreadsheet files and combine results.

        Args:
            file_paths: List of paths to spreadsheet files.

        Returns:
            Combined list of all StudentRecord objects from all files.
        """
        all_records = []

        for file_path in file_paths:
            try:
                records = self.process_file(file_path)
                all_records.extend(records)
                print(f"[Processor] Extracted {len(records)} student(s) from {os.path.basename(file_path)}")
            except Exception as e:
                print(f"[Processor] ERROR processing {file_path}: {e}")

        print(f"[Processor] Total students extracted: {len(all_records)}")
        return all_records

    def _parse_dataframe(self, df: pd.DataFrame) -> List[StudentRecord]:
        """Parse a pandas DataFrame into StudentRecord objects.

        Attempts to auto-detect column mappings based on common naming patterns.

        Args:
            df: Input DataFrame from a spreadsheet.

        Returns:
            List of StudentRecord objects.
        """
        # Normalize column names for matching
        df.columns = [str(col).strip() for col in df.columns]
        col_lower_map = {col.lower(): col for col in df.columns}

        # Find the name column
        name_col = self._find_column(col_lower_map, self.NAME_COLUMNS)
        if not name_col:
            raise ValueError(
                f"Could not find a 'Name' column. "
                f"Available columns: {list(df.columns)}. "
                f"Expected one of: {self.NAME_COLUMNS}"
            )

        # Find choice/preference columns
        choice_cols = self._find_choice_columns(df.columns)
        if not choice_cols:
            raise ValueError(
                f"Could not find course choice columns. "
                f"Available columns: {list(df.columns)}. "
                f"Expected columns containing 'choice' in their name."
            )

        print(f"[Processor] Name column: '{name_col}'")
        print(f"[Processor] Choice columns: {choice_cols}")

        # Extract records
        records = []
        for _, row in df.iterrows():
            name = str(row[name_col]).strip()

            # Skip empty or NaN names
            if not name or name.lower() == "nan":
                continue

            # Extract preferences in order
            preferences = []
            for col in choice_cols:
                value = str(row[col]).strip()
                if value and value.lower() != "nan":
                    preferences.append(value)

            if preferences:
                records.append(StudentRecord(name=name, preferences=preferences))

        return records

    def _find_column(self, col_lower_map: Dict[str, str], candidates: List[str]) -> Optional[str]:
        """Find a column by matching against candidate names.

        Args:
            col_lower_map: Mapping of lowercase column names to original names.
            candidates: List of candidate column name patterns (lowercase).

        Returns:
            Original column name if found, None otherwise.
        """
        for candidate in candidates:
            if candidate in col_lower_map:
                return col_lower_map[candidate]
        return None

    def _find_choice_columns(self, columns: List[str]) -> List[str]:
        """Find and order course choice columns.

        Looks for columns containing 'choice' in their name and orders them
        by any numeric indicator (first, second, 1st, 2nd, etc.)

        Args:
            columns: List of DataFrame column names.

        Returns:
            Ordered list of choice column names.
        """
        # Define ordering keywords
        order_keywords = [
            (["first", "1st", "1"], 1),
            (["second", "2nd", "2"], 2),
            (["third", "3rd", "3"], 3),
            (["fourth", "4th", "4"], 4),
            (["fifth", "5th", "5"], 5),
            (["sixth", "6th", "6"], 6),
        ]

        choice_cols = []
        for col in columns:
            if "choice" in col.lower():
                # Determine order
                order = 99  # default for unrecognized
                col_lower = col.lower()
                for keywords, rank in order_keywords:
                    if any(kw in col_lower for kw in keywords):
                        order = rank
                        break
                choice_cols.append((order, col))

        # Sort by order and return column names
        choice_cols.sort(key=lambda x: x[0])
        return [col for _, col in choice_cols]
