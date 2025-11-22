"""Markdown and text file ingestion with YAML frontmatter."""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

import frontmatter
from pydantic import ValidationError

from mtm.models import Note


def parse_md_txt(file_path: str | Path) -> Note:
    """Parse markdown or text file with YAML frontmatter.

    Args:
        file_path: Path to .md or .txt file

    Returns:
        Note object with parsed content and metadata

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file cannot be parsed
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Read file with frontmatter parsing
    with open(file_path, "r", encoding="utf-8") as f:
        post = frontmatter.load(f)

    # Extract metadata
    metadata = post.metadata or {}
    content = post.content or ""

    # Normalize metadata fields
    date = _parse_date(metadata.get("date") or metadata.get("created") or metadata.get("created_at"))
    if not date:
        # Try to extract from filename or use file modification time
        date = _extract_date_from_filename(file_path) or datetime.fromtimestamp(file_path.stat().st_mtime)

    meeting_title = (
        metadata.get("meeting")
        or metadata.get("title")
        or metadata.get("meeting_title")
        or file_path.stem
    )

    attendees = _normalize_list(metadata.get("attendees") or metadata.get("participants") or [])
    project = metadata.get("project") or metadata.get("project_name") or "default"
    roles = _normalize_list(metadata.get("roles") or metadata.get("role") or [])
    tags = _normalize_list(metadata.get("tags") or metadata.get("tag") or [])

    # Create Note object
    note = Note(
        id=uuid4(),
        project=project,
        roles=roles,
        date=date,
        source_file=str(file_path),
        content=content.strip(),
        title=meeting_title,
        metadata={
            "attendees": ",".join(attendees) if attendees else "",
            "tags": ",".join(tags) if tags else "",
            "meeting": meeting_title,
            **{k: str(v) for k, v in metadata.items() if k not in ["date", "meeting", "title", "attendees", "project", "roles", "tags"]},
        },
    )

    return note


def _parse_date(date_value: str | datetime | None) -> Optional[datetime]:
    """Parse date from various formats.

    Args:
        date_value: Date string or datetime object

    Returns:
        Parsed datetime or None
    """
    if date_value is None:
        return None

    if isinstance(date_value, datetime):
        return date_value

    if isinstance(date_value, str):
        # Try common date formats
        date_formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%B %d, %Y",
            "%d %B %Y",
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_value, fmt)
            except ValueError:
                continue

        # Try ISO format
        try:
            return datetime.fromisoformat(date_value.replace("Z", "+00:00"))
        except ValueError:
            pass

    return None


def _extract_date_from_filename(file_path: Path) -> Optional[datetime]:
    """Try to extract date from filename patterns like YYYY-MM-DD.

    Args:
        file_path: Path to file

    Returns:
        Parsed datetime or None
    """
    filename = file_path.stem

    # Pattern: YYYY-MM-DD or YYYYMMDD
    date_patterns = [
        r"(\d{4}-\d{2}-\d{2})",  # 2024-01-15
        r"(\d{4}\d{2}\d{2})",  # 20240115
        r"(\d{2}-\d{2}-\d{4})",  # 01-15-2024
    ]

    for pattern in date_patterns:
        match = re.search(pattern, filename)
        if match:
            date_str = match.group(1)
            return _parse_date(date_str)

    return None


def _normalize_list(value: str | list | None) -> list[str]:
    """Normalize value to list of strings.

    Args:
        value: String, list, or None

    Returns:
        List of strings
    """
    if value is None:
        return []

    if isinstance(value, str):
        # Split by comma, semicolon, or newline
        return [item.strip() for item in re.split(r"[,;\n]", value) if item.strip()]

    if isinstance(value, list):
        return [str(item).strip() for item in value if item]

    return []

