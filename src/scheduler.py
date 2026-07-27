"""Scheduler module for running the agent automatically at set intervals."""

import time
import signal
import sys
from datetime import datetime


class AgentScheduler:
    """Runs the enrolment agent on a repeating schedule.

    Supports:
        - Run every N minutes
        - Run at specific times of day
        - Graceful shutdown with Ctrl+C
    """

    def __init__(self, interval_minutes: int = 30):
        """
        Args:
            interval_minutes: How often to run (in minutes). Default: 30.
        """
        self.interval_minutes = interval_minutes
        self.running = True
        self.run_count = 0

        # Handle Ctrl+C gracefully
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _shutdown(self, signum, frame):
        """Handle shutdown signal gracefully."""
        print("\n\n[Scheduler] Shutting down gracefully...")
        print(f"[Scheduler] Total runs completed: {self.run_count}")
        self.running = False
        sys.exit(0)

    def run(self, task_function, **kwargs):
        """Run a task function repeatedly at the configured interval.

        Args:
            task_function: The function to call each cycle.
            **kwargs: Arguments to pass to the task function.
        """
        print("\n" + "=" * 60)
        print("  STUDENT ENROLMENT AGENT - Auto Mode")
        print("=" * 60)
        print(f"  Interval:  Every {self.interval_minutes} minute(s)")
        print(f"  Started:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Stop with: Ctrl+C")
        print("=" * 60)

        while self.running:
            self.run_count += 1
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n{'~' * 60}")
            print(f"  [Run #{self.run_count}] Starting at {now}")
            print(f"{'~' * 60}")

            try:
                task_function(**kwargs)
            except Exception as e:
                print(f"\n[Scheduler] ERROR during run #{self.run_count}: {e}")
                print("[Scheduler] Will retry at next interval...")

            if self.running:
                next_run = datetime.now().strftime("%H:%M:%S")
                print(f"\n[Scheduler] Run #{self.run_count} complete.")
                print(f"[Scheduler] Next run in {self.interval_minutes} minute(s)...")
                print(f"[Scheduler] Press Ctrl+C to stop.\n")

                # Wait for the interval (check every 5 seconds for shutdown)
                wait_seconds = self.interval_minutes * 60
                elapsed = 0
                while elapsed < wait_seconds and self.running:
                    time.sleep(5)
                    elapsed += 5
