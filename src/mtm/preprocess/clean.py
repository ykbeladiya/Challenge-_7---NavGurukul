"""Text cleaning and preprocessing for meeting notes."""

import builtins
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

import nltk
from unidecode import unidecode

from mtm.config import get_config
from mtm.models import Note, Segment
from mtm.storage.db import get_db


def download_nltk_data() -> None:
    """Download required NLTK data if not already present."""
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        try:
            nltk.download("punkt_tab", quiet=True)
        except Exception:
            # Fallback to old punkt if punkt_tab fails
            try:
                nltk.data.find("tokenizers/punkt")
            except LookupError:
                nltk.download("punkt", quiet=True)


def normalize_unicode(text: str) -> str:
    """Normalize Unicode characters to ASCII.

    Args:
        text: Input text

    Returns:
        Normalized text
    """
    return unidecode(text)


def strip_boilerplate(text: str) -> str:
    """Remove common boilerplate text patterns.

    Args:
        text: Input text

    Returns:
        Text with boilerplate removed
    """
    # Common meeting note boilerplate patterns
    boilerplate_patterns = [
        r"^Meeting Notes.*?\n",
        r"^Minutes.*?\n",
        r"^Agenda.*?\n",
        r"^Attendees?:.*?\n",
        r"^Date:.*?\n",
        r"^Time:.*?\n",
        r"^Location:.*?\n",
        r"^---+\s*\n",  # Horizontal rules
        r"^\*\*\*+\s*\n",  # Asterisk separators
        r"^Page \d+.*?\n",  # Page numbers
        r"^Confidential.*?\n",  # Confidentiality notices
        r"^This document.*?\n",  # Document disclaimers
    ]

    cleaned = text
    for pattern in boilerplate_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.MULTILINE | re.IGNORECASE)

    # Remove excessive whitespace
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)  # Max 2 newlines
    cleaned = re.sub(r"[ \t]+", " ", cleaned)  # Multiple spaces to single

    return cleaned.strip()


def redact_text(text: str, config: Optional[Any] = None) -> str:
    """Redact sensitive information based on config rules.

    Args:
        text: Input text
        config: Config object (optional, will load if not provided)

    Returns:
        Text with redactions applied
    """
    if config is None:
        config = get_config()

    redacted = text

    # Redact emails
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    redacted = re.sub(email_pattern, "[EMAIL]", redacted)

    # Redact phone numbers (various formats)
    phone_patterns = [
        r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # 123-456-7890
        r"\b\(\d{3}\)\s?\d{3}[-.]?\d{4}\b",  # (123) 456-7890
        r"\b\d{10}\b",  # 1234567890
        r"\+\d{1,3}[-.]?\d{1,4}[-.]?\d{1,4}[-.]?\d{1,9}\b",  # International
    ]
    for pattern in phone_patterns:
        redacted = re.sub(pattern, "[PHONE]", redacted)

    # Apply custom redaction rules from config if available
    if hasattr(config, "redact_rules") and config.redact_rules:
        redact_file = Path(config.redact_rules)
        if redact_file.exists():
            try:
                with open(redact_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            # Format: pattern|replacement
                            if "|" in line:
                                pattern, replacement = line.split("|", 1)
                                redacted = re.sub(pattern.strip(), replacement.strip(), redacted)

            except Exception:
                pass  # Silently fail if redaction file can't be read

    return redacted


def split_sentences(text: str) -> list[str]:
    """Split text into sentences using NLTK punkt tokenizer.

    Args:
        text: Input text

    Returns:
        List of sentences
    """
    download_nltk_data()

    # Use NLTK sentence tokenizer
    sentences = nltk.sent_tokenize(text)

    # Filter out very short sentences (likely artifacts)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 3]

    return sentences


def extract_speakers(text: str) -> list[tuple[str, str]]:
    """Extract speaker attributions using heuristics.

    Looks for patterns like "Name:" or "Name -" at the start of lines.

    Args:
        text: Input text

    Returns:
        List of (speaker, text) tuples
    """
    lines = text.split("\n")
    speakers: list[tuple[str, str]] = []
    current_speaker: Optional[str] = None
    current_text: list[str] = []

    # Pattern: "Name:" or "Name -" at start of line
    speaker_pattern = re.compile(r"^([A-Z][a-zA-Z\s]+?)[:\-]\s*(.+)$")

    for line in lines:
        line = line.strip()
        if not line:
            if current_speaker and current_text:
                speakers.append((current_speaker, "\n".join(current_text)))
                current_text = []
            continue

        match = speaker_pattern.match(line)
        if match:
            # Save previous speaker's text
            if current_speaker and current_text:
                speakers.append((current_speaker, "\n".join(current_text)))
                current_text = []

            # Start new speaker
            current_speaker = match.group(1).strip()
            current_text = [match.group(2).strip()]
        else:
            # Continue current speaker or add to unattributed
            if current_speaker:
                current_text.append(line)
            else:
                # Unattributed text
                if current_text:
                    current_text.append(line)
                else:
                    current_text = [line]
                    current_speaker = "[Unattributed]"

    # Add final speaker
    if current_speaker and current_text:
        speakers.append((current_speaker, "\n".join(current_text)))

    return speakers


def preprocess_note(note: Note, persist: bool = True) -> list[Segment]:
    """Preprocess a note: clean, split, and extract segments.

    Args:
        note: Note object to preprocess
        persist: Whether to persist segments to database

    Returns:
        List of Segment objects
    """
    if not note.content:
        return []

    config = get_config()
    db = get_db() if persist else None

    # Step 1: Normalize Unicode
    cleaned = normalize_unicode(note.content)

    # Step 2: Strip boilerplate
    cleaned = strip_boilerplate(cleaned)

    # Step 3: Redact sensitive information
    cleaned = redact_text(cleaned, config)

    # Step 4: Extract speakers (if applicable)
    speakers = extract_speakers(cleaned)

    segments: list[Segment] = []

    if speakers:
        # Create segments from speaker attributions
        for order, (speaker, text) in enumerate(speakers):
            # Split speaker text into sentences
            sentences = split_sentences(text)

            for sentence in sentences:
                segment = Segment(
                    id=uuid4(),
                    note_id=note.id,
                    project=note.project,
                    roles=note.roles + ([speaker] if speaker != "[Unattributed]" else []),
                    date=note.date,
                    source_file=note.source_file,
                    content=sentence,
                    segment_type="speaker_attributed",
                    order=order,
                )
                segments.append(segment)
    else:
        # No speaker attribution, just split into sentences
        sentences = split_sentences(cleaned)

        for order, sentence in enumerate(sentences):
            segment = Segment(
                id=uuid4(),
                note_id=note.id,
                project=note.project,
                roles=note.roles,
                date=note.date,
                source_file=note.source_file,
                content=sentence,
                segment_type="sentence",
                order=order,
            )
            segments.append(segment)

    # Persist segments to database
    if persist and db:
        for segment in segments:
            db.upsert_segment(
                segment_id=segment.id,
                note_id=segment.note_id,
                project=segment.project,
                date=segment.date,
                source_file=segment.source_file,
                content=segment.content,
                segment_type=segment.segment_type,
                order=segment.order,
            )

    return segments


def preprocess_file(file_path: str | Path, persist: bool = True) -> list[Segment]:
    """Preprocess a file by loading it as a note and preprocessing.

    Args:
        file_path: Path to file
        persist: Whether to persist segments to database

    Returns:
        List of Segment objects
    """
    from pathlib import Path

    file_path = Path(file_path)
    ext = file_path.suffix.lower()

    # Import parsers
    if ext in [".md", ".txt"]:
        from mtm.ingest.md_txt import parse_md_txt

        note = parse_md_txt(file_path)
    elif ext == ".docx":
        from mtm.ingest.docx_loader import parse_docx

        note = parse_docx(file_path)
    elif ext == ".pdf":
        from mtm.ingest.pdf_loader import parse_pdf

        note = parse_pdf(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    # If persisting, look up the note in the database by source_path
    # to get the correct note_id (the parsed note has a new UUID)
    if persist:
        db = get_db()
        # Try multiple path formats
        source_path_abs = str(file_path.resolve())
        source_path_rel = str(file_path)
        # Normalize path separators for Windows
        source_path_abs_norm = source_path_abs.replace("\\", "/")
        source_path_rel_norm = source_path_rel.replace("\\", "/")
        
        # Try to find note by source_path (try absolute, relative, and normalized versions)
        existing_notes = builtins.list(db.db["notes"].rows_where("source_path = ?", [source_path_abs]))
        if not existing_notes:
            existing_notes = builtins.list(db.db["notes"].rows_where("source_path = ?", [source_path_rel]))
        if not existing_notes:
            existing_notes = builtins.list(db.db["notes"].rows_where("source_path = ?", [source_path_abs_norm]))
        if not existing_notes:
            existing_notes = builtins.list(db.db["notes"].rows_where("source_path = ?", [source_path_rel_norm]))
        
        if existing_notes:
            # Use the note_id from the database
            note.id = existing_notes[0]["id"]
        else:
            # If not found, try to find by source_file (filename)
            source_file = file_path.name
            existing_notes = builtins.list(db.db["notes"].rows_where("source_file = ?", [source_file]))
            if existing_notes:
                # Use the first matching note_id
                note.id = existing_notes[0]["id"]

    return preprocess_note(note, persist=persist)

