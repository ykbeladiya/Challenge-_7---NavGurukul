"""Structured logging utilities with Rich and JSONL output."""

import json
from datetime import datetime
from pathlib import Path
from time import time
from typing import Any, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from mtm.config import get_config


class StructuredLogger:
    """Structured logger with Rich console output and JSONL file logging."""

    def __init__(self, command_name: str, log_to_file: bool = True):
        """Initialize logger.

        Args:
            command_name: Name of the command being executed
            log_to_file: Whether to write JSONL logs to file
        """
        self.command_name = command_name
        self.console = Console()
        self.start_time = time()
        self.log_entries: list[dict[str, Any]] = []
        self.counts: dict[str, int] = {}
        self.skipped_files: list[dict[str, str]] = []
        self.errors: list[dict[str, str]] = []
        self.log_to_file = log_to_file
        self._writing_log = False  # Guard to prevent recursive logging

        # Create log entry for command start
        self.log("command_start", {"command": command_name})

    def log(self, event_type: str, data: dict[str, Any]) -> None:
        """Log an event.

        Args:
            event_type: Type of event (e.g., "command_start", "file_processed", "error")
            data: Event data dictionary
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "command": self.command_name,
            "event_type": event_type,
            **data,
        }
        self.log_entries.append(entry)

        # Write to JSONL file if enabled
        if self.log_to_file:
            self._write_jsonl_entry(entry)

    def increment_count(self, key: str, amount: int = 1) -> None:
        """Increment a counter.

        Args:
            key: Counter key
            amount: Amount to increment
        """
        self.counts[key] = self.counts.get(key, 0) + amount

    def add_skipped_file(self, file_path: str, reason: str) -> None:
        """Add a skipped file to the report.

        Args:
            file_path: Path to skipped file
            reason: Reason for skipping
        """
        self.skipped_files.append({"file": file_path, "reason": reason})
        self.log("file_skipped", {"file": file_path, "reason": reason})

    def add_error(self, error_type: str, message: str, hint: Optional[str] = None) -> None:
        """Add an error to the report.

        Args:
            error_type: Type of error
            message: Error message
            hint: Actionable hint for resolving the error
        """
        error_data = {"type": error_type, "message": message}
        if hint:
            error_data["hint"] = hint
        self.errors.append(error_data)
        self.log("error", error_data)

    def _write_jsonl_entry(self, entry: dict[str, Any]) -> None:
        """Write a single entry to JSONL log file.

        Args:
            entry: Log entry dictionary
        """
        # Guard against recursive calls
        if self._writing_log:
            return
        self._writing_log = True
        
        try:
            config = get_config()
            logs_dir = Path(config.output_dir) / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)

            # Use date-based filename
            date_str = datetime.now().strftime("%Y%m%d")
            log_file = logs_dir / f"{date_str}.jsonl"

            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        finally:
            self._writing_log = False

    def finish(self, success: bool = True) -> None:
        """Finish logging and display summary.

        Args:
            success: Whether the command completed successfully
        """
        elapsed_time = time() - self.start_time

        # Log command completion
        self.log(
            "command_end",
            {
                "success": success,
                "elapsed_seconds": round(elapsed_time, 2),
                "counts": self.counts,
                "errors_count": len(self.errors),
                "skipped_files_count": len(self.skipped_files),
            },
        )

        # Display summary
        self._display_summary(success, elapsed_time)

    def _display_summary(self, success: bool, elapsed_time: float) -> None:
        """Display summary table with timing, counts, and errors.

        Args:
            success: Whether command succeeded
            elapsed_time: Elapsed time in seconds
        """
        table = Table(title=f"Command Summary: {self.command_name}", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")

        # Timing
        table.add_row("Elapsed Time", f"{elapsed_time:.2f}s")

        # Counts
        if self.counts:
            for key, value in sorted(self.counts.items()):
                table.add_row(key.replace("_", " ").title(), str(value))

        # Errors
        if self.errors:
            table.add_row("Errors", f"[red]{len(self.errors)}[/red]")
        else:
            table.add_row("Errors", "[green]0[/green]")

        # Skipped files
        if self.skipped_files:
            table.add_row("Skipped Files", f"[yellow]{len(self.skipped_files)}[/yellow]")
        else:
            table.add_row("Skipped Files", "[green]0[/green]")

        self.console.print()
        self.console.print(table)

        # Display skipped files if any
        if self.skipped_files:
            self.console.print()
            self.console.print("[yellow]Skipped Files:[/yellow]")
            for skipped in self.skipped_files[:10]:  # Show first 10
                self.console.print(f"  [dim]{Path(skipped['file']).name}[/dim]: {skipped['reason']}")
            if len(self.skipped_files) > 10:
                self.console.print(f"  ... and {len(self.skipped_files) - 10} more")

        # Display errors with hints if any
        if self.errors:
            self.console.print()
            self.console.print("[red]Errors:[/red]")
            for error in self.errors:
                self.console.print(f"  [red]{error['type']}:[/red] {error['message']}")
                if error.get("hint"):
                    self.console.print(f"    [yellow]Hint:[/yellow] {error['hint']}")

    def get_exit_code(self) -> int:
        """Get exit code based on errors.

        Returns:
            0 if no errors, 1 if errors exist
        """
        return 0 if not self.errors else 1

    def get_actionable_hints(self) -> list[str]:
        """Get actionable hints for resolving errors.

        Returns:
            List of actionable hints
        """
        hints = []
        for error in self.errors:
            if error.get("hint"):
                hints.append(error["hint"])
        return hints


def create_logger(command_name: str, log_to_file: bool = True) -> StructuredLogger:
    """Create a structured logger instance.

    Args:
        command_name: Name of the command
        log_to_file: Whether to write JSONL logs

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(command_name, log_to_file=log_to_file)

