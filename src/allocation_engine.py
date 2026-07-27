"""Course allocation engine that assigns students to courses based on preferences."""

from typing import List, Dict, Tuple
from collections import defaultdict

from .config import Config
from .spreadsheet_processor import StudentRecord


class AllocationResult:
    """Holds the results of the course allocation process."""

    def __init__(self):
        # course_name -> list of student names
        self.placements: Dict[str, List[str]] = defaultdict(list)
        # Students who could not be placed in any of their preferred courses
        self.unplaced: List[Tuple[str, List[str]]] = []
        # Detailed log of allocation decisions
        self.allocation_log: List[str] = []

    def add_placement(self, student_name: str, course: str):
        """Record a student placement."""
        self.placements[course].append(student_name)
        self.allocation_log.append(f"  PLACED: {student_name} -> {course}")

    def add_unplaced(self, student_name: str, preferences: List[str]):
        """Record a student who could not be placed."""
        self.unplaced.append((student_name, preferences))
        self.allocation_log.append(
            f"  UNPLACED: {student_name} (preferences were: {', '.join(preferences)})"
        )

    def get_course_count(self, course: str) -> int:
        """Get current number of students in a course."""
        return len(self.placements.get(course, []))

    def is_course_full(self, course: str, max_capacity: int) -> bool:
        """Check if a course has reached its maximum capacity."""
        return self.get_course_count(course) >= max_capacity

    def get_flat_placements(self) -> List[Dict[str, str]]:
        """Get all placements as a flat list of {name, course} dicts.

        Returns results sorted by course name, then by student name within each course.
        """
        results = []
        for course in sorted(self.placements.keys()):
            for student in sorted(self.placements[course]):
                results.append({"name": student, "course": course})
        return results

    def summary(self) -> str:
        """Generate a human-readable summary of the allocation."""
        lines = []
        lines.append("\n" + "=" * 60)
        lines.append("COURSE ALLOCATION SUMMARY")
        lines.append("=" * 60)

        total_placed = 0
        for course in sorted(self.placements.keys()):
            students = self.placements[course]
            count = len(students)
            total_placed += count
            lines.append(f"\n  {course} ({count}/{Config.MAX_STUDENTS_PER_COURSE}):")
            for i, student in enumerate(sorted(students), 1):
                lines.append(f"    {i}. {student}")

        lines.append(f"\n  Total placed: {total_placed}")

        if self.unplaced:
            lines.append(f"\n  UNPLACED STUDENTS ({len(self.unplaced)}):")
            for name, prefs in self.unplaced:
                lines.append(f"    - {name} (wanted: {', '.join(prefs)})")

        lines.append("=" * 60)
        return "\n".join(lines)


class AllocationEngine:
    """Allocates students to courses based on their ranked preferences.

    Algorithm:
        Uses a first-come-first-served approach with preference ordering.
        For each student (processed in order received):
            1. Try their 1st choice - if space available, place them.
            2. If 1st choice full, try 2nd choice, and so on.
            3. If all preferences are full, mark as unplaced.

    This ensures students are given priority based on their preference rank,
    and courses are filled up to the configured maximum capacity.
    """

    def __init__(self, max_per_course: int = None, courses: List[str] = None):
        """
        Args:
            max_per_course: Maximum students per course. Defaults to Config value.
            courses: List of valid course names. Defaults to Config value.
        """
        self.max_per_course = max_per_course or Config.MAX_STUDENTS_PER_COURSE
        self.courses = [c.lower() for c in (courses or Config.COURSES)]
        self.course_display_names = {c.lower(): c for c in (courses or Config.COURSES)}

    def allocate(self, students: List[StudentRecord]) -> AllocationResult:
        """Run the allocation algorithm on a list of student records.

        Args:
            students: List of StudentRecord objects with preferences.

        Returns:
            AllocationResult containing all placements and unplaced students.
        """
        result = AllocationResult()

        print(f"\n[Allocator] Starting allocation for {len(students)} student(s)")
        print(f"[Allocator] Available courses: {list(self.course_display_names.values())}")
        print(f"[Allocator] Max per course: {self.max_per_course}")
        print()

        for student in students:
            placed = False

            for preference in student.preferences:
                # Normalize the preference for matching
                pref_lower = preference.lower().strip()

                # Find the matching course
                matched_course = self._match_course(pref_lower)

                if matched_course is None:
                    result.allocation_log.append(
                        f"  WARNING: '{preference}' is not a recognized course "
                        f"(student: {student.name})"
                    )
                    continue

                # Check if the course has space
                display_name = self.course_display_names[matched_course]
                if not result.is_course_full(display_name, self.max_per_course):
                    result.add_placement(student.name, display_name)
                    placed = True
                    break
                else:
                    result.allocation_log.append(
                        f"  FULL: {display_name} - cannot place {student.name} "
                        f"({result.get_course_count(display_name)}/{self.max_per_course})"
                    )

            if not placed:
                result.add_unplaced(student.name, student.preferences)

        return result

    def _match_course(self, preference: str) -> str:
        """Match a student's preference string to a valid course.

        Uses fuzzy matching to handle minor variations in course names.

        Args:
            preference: Normalized (lowercase) preference string.

        Returns:
            Matched course key (lowercase) or None if no match.
        """
        # Exact match
        if preference in self.courses:
            return preference

        # Partial/contains match
        for course in self.courses:
            if course in preference or preference in course:
                return course

        # Word overlap match (for cases like "it systems" vs "it")
        pref_words = set(preference.split())
        for course in self.courses:
            course_words = set(course.split())
            if pref_words & course_words:  # Any word overlap
                # Require significant overlap
                overlap = len(pref_words & course_words)
                if overlap >= len(course_words) * 0.5:
                    return course

        return None
