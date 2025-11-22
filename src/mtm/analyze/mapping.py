"""Role and project mapping using keyword matching and fuzzy matching."""

import json
from pathlib import Path
from typing import Optional

import yaml
from rapidfuzz import fuzz

from mtm.config import get_config
from mtm.storage.db import get_db


def load_role_taxonomy(taxonomy_path: Optional[str | Path] = None) -> dict:
    """Load role taxonomy from YAML file.

    Args:
        taxonomy_path: Path to taxonomy file. Defaults to config value.

    Returns:
        Dictionary with role definitions
    """
    if taxonomy_path is None:
        config = get_config()
        project_root = Path(__file__).parent.parent.parent
        taxonomy_path = project_root / "configs" / "role_taxonomy.yaml"
    else:
        taxonomy_path = Path(taxonomy_path)

    if not taxonomy_path.exists():
        return {}

    with open(taxonomy_path, "r", encoding="utf-8") as f:
        taxonomy = yaml.safe_load(f)

    return taxonomy.get("roles", {})


def calculate_role_confidence(
    text: str,
    role_keywords: list[str],
    threshold: float = 60.0,
) -> float:
    """Calculate confidence score for role assignment using keyword matching and fuzzy matching.

    Args:
        text: Text to analyze
        role_keywords: List of keywords for the role
        threshold: Minimum fuzzy match threshold (0-100)

    Returns:
        Confidence score (0-100)
    """
    if not text or not role_keywords:
        return 0.0

    text_lower = text.lower()
    matches = 0
    total_score = 0.0

    for keyword in role_keywords:
        keyword_lower = keyword.lower()

        # Exact match
        if keyword_lower in text_lower:
            matches += 1
            total_score += 100.0
        else:
            # Fuzzy match using partial_ratio
            score = fuzz.partial_ratio(keyword_lower, text_lower)
            if score >= threshold:
                matches += 1
                total_score += score

    if matches == 0:
        return 0.0

    # Average score weighted by number of matches
    confidence = total_score / len(role_keywords)
    # Boost confidence if multiple keywords match
    match_ratio = matches / len(role_keywords)
    confidence = confidence * (0.7 + 0.3 * match_ratio)

    return min(100.0, confidence)


def map_segment_to_roles(
    segment_id: str,
    segment_content: str,
    project: str,
    taxonomy: Optional[dict] = None,
    min_confidence: float = 50.0,
) -> list[tuple[str, float]]:
    """Map a segment to roles based on content.

    Args:
        segment_id: Segment ID
        segment_content: Segment content text
        project: Project name
        taxonomy: Role taxonomy (loads if not provided)
        min_confidence: Minimum confidence threshold

    Returns:
        List of (role, confidence) tuples
    """
    if taxonomy is None:
        taxonomy = load_role_taxonomy()

    if not taxonomy:
        return []

    role_matches: list[tuple[str, float]] = []

    for role_name, role_data in taxonomy.items():
        keywords = role_data.get("keywords", [])
        project_keywords = role_data.get("projects", [])

        # Check project match first
        project_match = False
        for proj_keyword in project_keywords:
            if proj_keyword.lower() in project.lower():
                project_match = True
                break

        # Calculate confidence
        confidence = calculate_role_confidence(segment_content, keywords)

        # Boost confidence if project matches
        if project_match:
            confidence = min(100.0, confidence * 1.2)

        if confidence >= min_confidence:
            role_matches.append((role_name, confidence))

    # Sort by confidence (descending)
    role_matches.sort(key=lambda x: x[1], reverse=True)

    return role_matches


def map_theme_to_roles(
    theme_id: str,
    theme_keywords: list[str],
    project: str,
    taxonomy: Optional[dict] = None,
    min_confidence: float = 50.0,
) -> list[tuple[str, float]]:
    """Map a theme to roles based on keywords.

    Args:
        theme_id: Theme ID
        theme_keywords: List of theme keywords
        project: Project name
        taxonomy: Role taxonomy (loads if not provided)
        min_confidence: Minimum confidence threshold

    Returns:
        List of (role, confidence) tuples
    """
    if taxonomy is None:
        taxonomy = load_role_taxonomy()

    if not taxonomy:
        return []

    # Combine theme keywords into text for matching
    theme_text = " ".join(theme_keywords)

    role_matches: list[tuple[str, float]] = []

    for role_name, role_data in taxonomy.items():
        keywords = role_data.get("keywords", [])
        project_keywords = role_data.get("projects", [])

        # Check project match
        project_match = False
        for proj_keyword in project_keywords:
            if proj_keyword.lower() in project.lower():
                project_match = True
                break

        # Calculate confidence using theme keywords
        confidence = calculate_role_confidence(theme_text, keywords)

        # Boost confidence if project matches
        if project_match:
            confidence = min(100.0, confidence * 1.2)

        if confidence >= min_confidence:
            role_matches.append((role_name, confidence))

    # Sort by confidence (descending)
    role_matches.sort(key=lambda x: x[1], reverse=True)

    return role_matches


def persist_role_mappings(
    topic_id: str,
    role_matches: list[tuple[str, float]],
    project: str,
    persist: bool = True,
) -> None:
    """Persist role mappings to topic_role_map table.

    Args:
        topic_id: Topic/segment ID
        role_matches: List of (role, confidence) tuples
        project: Project name
        persist: Whether to persist to database
    """
    if not persist:
        return

    db = get_db()

    for role, confidence in role_matches:
        # Check if mapping already exists
        existing = list(
            db.db["topic_role_map"].rows_where(
                "topic_id = ? AND role = ?", [topic_id, role]
            )
        )

        if existing:
            # Update confidence if higher
            existing_confidence = existing[0].get("confidence", 0.0)
            if confidence > existing_confidence:
                db.db["topic_role_map"].update(
                    existing[0]["id"],
                    {"confidence": confidence},
                )
        else:
            # Insert new mapping
            from datetime import datetime
            from uuid import uuid4

            record = {
                "id": str(uuid4()),
                "topic_id": topic_id,
                "role": role,
                "project": project,
                "confidence": confidence,
                "created_at": datetime.now().isoformat(),
            }
            db.db["topic_role_map"].insert(record)


def map_segments_to_roles(
    project: Optional[str] = None,
    min_confidence: float = 50.0,
    persist: bool = True,
) -> dict[str, list[tuple[str, float]]]:
    """Map all segments in a project to roles.

    Args:
        project: Project name (None for all projects)
        min_confidence: Minimum confidence threshold
        persist: Whether to persist mappings

    Returns:
        Dictionary mapping segment_id to list of (role, confidence) tuples
    """
    db = get_db()
    taxonomy = load_role_taxonomy()

    # Fetch segments
    if project:
        segments = list(
            db.db["segments"].rows_where("project = ?", [project], order_by="created_at")
        )
    else:
        segments = list(db.db["segments"].rows_where("1=1", order_by="created_at"))

    mappings: dict[str, list[tuple[str, float]]] = {}

    for segment in segments:
        segment_id = segment["id"]
        content = segment.get("content", "")
        seg_project = segment.get("project", project or "default")

        role_matches = map_segment_to_roles(
            segment_id, content, seg_project, taxonomy, min_confidence
        )

        if role_matches:
            mappings[segment_id] = role_matches
            persist_role_mappings(segment_id, role_matches, seg_project, persist)

    return mappings


def map_themes_to_roles(
    project: Optional[str] = None,
    min_confidence: float = 50.0,
    persist: bool = True,
) -> dict[str, list[tuple[str, float]]]:
    """Map all themes in a project to roles.

    Args:
        project: Project name (None for all projects)
        min_confidence: Minimum confidence threshold
        persist: Whether to persist mappings

    Returns:
        Dictionary mapping theme_id to list of (role, confidence) tuples
    """
    db = get_db()
    taxonomy = load_role_taxonomy()

    # Fetch themes
    if project:
        themes = list(
            db.db["themes"].rows_where("project = ?", [project], order_by="created_at")
        )
    else:
        themes = list(db.db["themes"].rows_where("1=1", order_by="created_at"))

    mappings: dict[str, list[tuple[str, float]]] = {}

    for theme in themes:
        theme_id = theme["id"]
        keywords_json = theme.get("keywords", "[]")
        theme_project = theme.get("project", project or "global")

        try:
            theme_keywords = json.loads(keywords_json) if isinstance(keywords_json, str) else keywords_json
        except (json.JSONDecodeError, TypeError):
            theme_keywords = []

        if not theme_keywords:
            continue

        role_matches = map_theme_to_roles(
            theme_id, theme_keywords, theme_project, taxonomy, min_confidence
        )

        if role_matches:
            mappings[theme_id] = role_matches
            persist_role_mappings(theme_id, role_matches, theme_project, persist)

    return mappings

