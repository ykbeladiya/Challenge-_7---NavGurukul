"""Full-text search utilities."""

import json
from typing import Optional

from mtm.storage.db import get_db


def search_notes(
    query: str,
    project: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """Search notes by content.

    Args:
        query: Search query string
        project: Project filter (optional)
        limit: Maximum number of results

    Returns:
        List of matching notes with scores
    """
    db = get_db()
    query_lower = query.lower()

    # Get all notes
    if project:
        notes = list(db.db["notes"].rows_where("project = ?", [project]))
    else:
        notes = list(db.db["notes"].rows_where("1=1"))

    results: list[dict] = []

    for note in notes:
        content = (note.get("content", "") or "").lower()
        title = (note.get("title", "") or "").lower()

        # Simple scoring: count occurrences
        score = 0
        if query_lower in title:
            score += 10  # Title matches are more important
        score += content.count(query_lower) * 2
        score += title.count(query_lower) * 5

        if score > 0:
            results.append(
                {
                    "type": "note",
                    "id": note["id"],
                    "project": note.get("project", ""),
                    "title": note.get("title", ""),
                    "source_file": note.get("source_file", ""),
                    "source_path": note.get("source_path", ""),
                    "score": score,
                    "content_preview": (note.get("content", "") or "")[:200],
                }
            )

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def search_segments(
    query: str,
    project: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """Search segments by content.

    Args:
        query: Search query string
        project: Project filter (optional)
        limit: Maximum number of results

    Returns:
        List of matching segments with scores
    """
    db = get_db()
    query_lower = query.lower()

    # Get all segments
    if project:
        segments = list(db.db["segments"].rows_where("project = ?", [project]))
    else:
        segments = list(db.db["segments"].rows_where("1=1"))

    results: list[dict] = []

    for segment in segments:
        content = (segment.get("content", "") or "").lower()

        # Simple scoring: count occurrences
        score = content.count(query_lower) * 2

        if score > 0:
            # Get parent note for context
            note_id = segment.get("note_id")
            note = db.db["notes"].get(note_id) if note_id else None

            results.append(
                {
                    "type": "segment",
                    "id": segment["id"],
                    "note_id": note_id,
                    "project": segment.get("project", ""),
                    "source_file": segment.get("source_file", ""),
                    "score": score,
                    "content_preview": content[:200],
                    "note_title": note.get("title", "") if note else "",
                    "note_source_path": note.get("source_path", "") if note else "",
                }
            )

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def search_extractions(
    query: str,
    project: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """Search extractions by content.

    Args:
        query: Search query string
        project: Project filter (optional)
        limit: Maximum number of results

    Returns:
        List of matching extractions with scores
    """
    db = get_db()
    query_lower = query.lower()

    # Get all extractions
    if project:
        extractions = list(db.db["extractions"].rows_where("project = ?", [project]))
    else:
        extractions = list(db.db["extractions"].rows_where("1=1"))

    results: list[dict] = []

    for extraction in extractions:
        payload_str = extraction.get("payload", "{}")
        try:
            payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
        except (json.JSONDecodeError, TypeError):
            payload = {}

        # Search in payload fields
        searchable_text = " ".join(str(v) for v in payload.values() if v).lower()

        # Simple scoring: count occurrences
        score = searchable_text.count(query_lower) * 2

        if score > 0:
            # Get parent note for context
            note_id = extraction.get("note_id")
            note = db.db["notes"].get(note_id) if note_id else None

            results.append(
                {
                    "type": extraction.get("type", "extraction"),
                    "id": extraction["id"],
                    "note_id": note_id,
                    "project": extraction.get("project", ""),
                    "source_file": extraction.get("source_file", ""),
                    "score": score,
                    "payload": payload,
                    "note_title": note.get("title", "") if note else "",
                    "note_source_path": note.get("source_path", "") if note else "",
                }
            )

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def search_all(
    query: str,
    project: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """Search across all content types.

    Args:
        query: Search query string
        project: Project filter (optional)
        limit: Maximum number of results per type

    Returns:
        Combined list of all matches sorted by score
    """
    notes = search_notes(query, project=project, limit=limit)
    segments = search_segments(query, project=project, limit=limit)
    extractions = search_extractions(query, project=project, limit=limit)

    # Combine and sort by score
    all_results = notes + segments + extractions
    all_results.sort(key=lambda x: x["score"], reverse=True)

    return all_results

