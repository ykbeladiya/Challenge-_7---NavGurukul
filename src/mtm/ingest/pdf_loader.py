"""PDF file ingestion using pdfminer.six (text only)."""

from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams

from mtm.models import Note


def parse_pdf(file_path: str | Path) -> Note:
    """Parse PDF file and extract text content.

    Args:
        file_path: Path to .pdf file

    Returns:
        Note object with parsed content and metadata

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file cannot be parsed
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Extract text from PDF
    try:
        # Use layout parameters for better text extraction
        laparams = LAParams(
            line_margin=0.5,
            word_margin=0.1,
            char_margin=2.0,
            boxes_flow=0.5,
        )

        content = extract_text(str(file_path), laparams=laparams)
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {e}") from e

    if not content or not content.strip():
        raise ValueError(f"PDF appears to be empty or contains no extractable text: {file_path}")

    # Extract metadata
    date = datetime.fromtimestamp(file_path.stat().st_mtime)

    # Try to extract title and metadata from content
    meeting_title = _extract_title_from_content(content) or file_path.stem
    extracted_metadata = _extract_metadata_from_content(content)

    # Normalize metadata
    project = extracted_metadata.get("project") or "default"
    attendees = _normalize_list(extracted_metadata.get("attendees") or [])
    roles = _normalize_list(extracted_metadata.get("roles") or [])
    tags = _normalize_list(extracted_metadata.get("tags") or [])

    # Try to extract date from content
    content_date = _extract_date_from_content(content)
    if content_date:
        date = content_date

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
            "file_type": "pdf",
        },
    )

    return note


def _extract_title_from_content(content: str) -> Optional[str]:
    """Extract title from PDF content (first non-empty line).

    Args:
        content: PDF text content

    Returns:
        Title string or None
    """
    lines = content.split("\n")
    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        # Look for lines that might be titles
        if line and len(line) < 200 and len(line) > 3:
            # Skip common non-title patterns
            if not any(
                line.lower().startswith(prefix)
                for prefix in ["page", "date:", "time:", "attendance", "agenda"]
            ):
                return line
    return None


def _extract_metadata_from_content(content: str) -> dict[str, str | list[str]]:
    """Extract metadata patterns from PDF content.

    Looks for patterns like:
    - Project: name
    - Attendees: person1, person2
    - Roles: role1, role2
    - Tags: tag1, tag2
    - Date: YYYY-MM-DD

    Args:
        content: PDF text content

    Returns:
        Dictionary of extracted metadata
    """
    import re

    metadata: dict[str, str | list[str]] = {}

    # Pattern matching for key-value pairs
    patterns = {
        "project": r"(?:project|project name|project_name)[:\s]+([^\n]+)",
        "attendees": r"(?:attendees|participants|people|present)[:\s]+([^\n]+)",
        "roles": r"(?:roles|role)[:\s]+([^\n]+)",
        "tags": r"(?:tags|tag)[:\s]+([^\n]+)",
        "date": r"(?:date|meeting date)[:\s]+([^\n]+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, content[:2000], re.IGNORECASE)  # Search first 2000 chars
        if match:
            value = match.group(1).strip()
            if key in ["attendees", "roles", "tags"]:
                metadata[key] = [item.strip() for item in value.split(",") if item.strip()]
            else:
                metadata[key] = value

    return metadata


def _extract_date_from_content(content: str) -> Optional[datetime]:
    """Extract date from PDF content.

    Args:
        content: PDF text content

    Returns:
        Parsed datetime or None
    """
    import re

    # Look for date patterns in first 1000 characters
    date_patterns = [
        r"(?:date|meeting date)[:\s]+(\d{4}-\d{2}-\d{2})",
        r"(?:date|meeting date)[:\s]+(\d{2}/\d{2}/\d{4})",
        r"(\d{4}-\d{2}-\d{2})",  # YYYY-MM-DD
        r"(\d{2}/\d{2}/\d{4})",  # MM/DD/YYYY
    ]

    for pattern in date_patterns:
        match = re.search(pattern, content[:1000], re.IGNORECASE)
        if match:
            date_str = match.group(1)
            return _parse_date(date_str)

    return None


def _parse_date(date_value: str) -> Optional[datetime]:
    """Parse date from string.

    Args:
        date_value: Date string

    Returns:
        Parsed datetime or None
    """
    date_formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%B %d, %Y",
        "%d %B %Y",
    ]

    for fmt in date_formats:
        try:
            return datetime.strptime(date_value, fmt)
        except ValueError:
            continue

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
        return [item.strip() for item in value.split(",") if item.strip()]

    if isinstance(value, list):
        return [str(item).strip() for item in value if item]

    return []

