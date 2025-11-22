"""Version management and SemVer computation."""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from mtm.models import Backlinks, Module, VersionEntry
from mtm.storage.db import get_db


class ChangeType(Enum):
    """Type of change for SemVer computation."""

    MAJOR = "major"  # Structure changed
    MINOR = "minor"  # Items added
    PATCH = "patch"  # Text tweaks only


def compute_semver_change(old_module: dict, new_module: dict) -> ChangeType:
    """Compute SemVer change type based on module differences.

    Args:
        old_module: Previous module data
        new_module: New module data

    Returns:
        ChangeType indicating the level of change
    """
    # Check for structural changes (MAJOR)
    old_structure = {
        "themes": set(json.loads(old_module.get("theme_ids", "[]")) if isinstance(old_module.get("theme_ids"), str) else old_module.get("theme_ids", [])),
        "steps": set(json.loads(old_module.get("step_ids", "[]")) if isinstance(old_module.get("step_ids"), str) else old_module.get("step_ids", [])),
        "definitions": set(json.loads(old_module.get("definition_ids", "[]")) if isinstance(old_module.get("definition_ids"), str) else old_module.get("definition_ids", [])),
        "faqs": set(json.loads(old_module.get("faq_ids", "[]")) if isinstance(old_module.get("faq_ids"), str) else old_module.get("faq_ids", [])),
        "decisions": set(json.loads(old_module.get("decision_ids", "[]")) if isinstance(old_module.get("decision_ids"), str) else old_module.get("decision_ids", [])),
        "actions": set(json.loads(old_module.get("action_ids", "[]")) if isinstance(old_module.get("action_ids"), str) else old_module.get("action_ids", [])),
    }

    new_structure = {
        "themes": set(json.loads(new_module.get("theme_ids", "[]")) if isinstance(new_module.get("theme_ids"), str) else new_module.get("theme_ids", [])),
        "steps": set(json.loads(new_module.get("step_ids", "[]")) if isinstance(new_module.get("step_ids"), str) else new_module.get("step_ids", [])),
        "definitions": set(json.loads(new_module.get("definition_ids", "[]")) if isinstance(new_module.get("definition_ids"), str) else new_module.get("definition_ids", [])),
        "faqs": set(json.loads(new_module.get("faq_ids", "[]")) if isinstance(new_module.get("faq_ids"), str) else new_module.get("faq_ids", [])),
        "decisions": set(json.loads(new_module.get("decision_ids", "[]")) if isinstance(new_module.get("decision_ids"), str) else new_module.get("decision_ids", [])),
        "actions": set(json.loads(new_module.get("action_ids", "[]")) if isinstance(new_module.get("action_ids"), str) else new_module.get("action_ids", [])),
    }

    # Check if structure changed (items removed or type changed)
    for key in old_structure:
        removed = old_structure[key] - new_structure[key]
        if removed:
            return ChangeType.MAJOR

    # Check if module type changed
    if old_module.get("module_type") != new_module.get("module_type"):
        return ChangeType.MAJOR

    # Check for additions (MINOR)
    for key in new_structure:
        added = new_structure[key] - old_structure[key]
        if added:
            return ChangeType.MINOR

    # Check if title changed (could be MINOR or PATCH)
    if old_module.get("title") != new_module.get("title"):
        # If title changed significantly, it's MINOR
        return ChangeType.MINOR

    # Otherwise, it's just text/content changes (PATCH)
    return ChangeType.PATCH


def increment_version(current_version: int, change_type: ChangeType) -> int:
    """Increment version based on change type.

    Args:
        current_version: Current version number
        change_type: Type of change

    Returns:
        New version number
    """
    # Extract major, minor, patch from version
    # Version stored as integer: major * 10000 + minor * 100 + patch
    major = current_version // 10000
    minor = (current_version % 10000) // 100
    patch = current_version % 100

    if change_type == ChangeType.MAJOR:
        major += 1
        minor = 0
        patch = 0
    elif change_type == ChangeType.MINOR:
        minor += 1
        patch = 0
    else:  # PATCH
        patch += 1

    return major * 10000 + minor * 100 + patch


def create_version_entry(
    module_id: UUID | str,
    module: dict,
    change_type: ChangeType,
    changes: Optional[str] = None,
    created_by: Optional[str] = None,
) -> VersionEntry:
    """Create a version entry for a module.

    Args:
        module_id: Module ID
        module: Module data dictionary
        change_type: Type of change
        changes: Description of changes
        created_by: Creator identifier

    Returns:
        VersionEntry object
    """
    db = get_db()

    # Get current version
    current_version = module.get("version", 1)
    new_version = increment_version(current_version, change_type)

    # Parse backlinks
    from mtm.models import Backlinks

    backlinks = Backlinks()
    if module.get("note_id"):
        backlinks.note_id = UUID(module["note_id"])

    version_entry = VersionEntry(
        id=uuid4(),
        module_id=UUID(module_id) if isinstance(module_id, str) else module_id,
        version=new_version,
        project=module.get("project", "default"),
        title=module.get("title", "Untitled"),
        description=module.get("description"),
        content=module.get("content"),
        changes=changes or f"{change_type.value.capitalize()} change",
        created_by=created_by,
        backlinks=backlinks,
    )

    # Persist to database
    db.upsert_version(
        version_id=version_entry.id,
        module_id=version_entry.module_id,
        version=version_entry.version,
        project=version_entry.project,
        title=version_entry.title,
        description=version_entry.description,
        content=version_entry.content,
        changes=version_entry.changes,
        created_by=version_entry.created_by,
        note_id=version_entry.backlinks.note_id,
    )

    # Update module version
    db.db["modules"].update(
        str(module_id),
        {"version": new_version},
    )

    return version_entry


def write_changelog(
    module_id: UUID | str,
    output_path: Optional[str | Path] = None,
) -> Path:
    """Write CHANGELOG.md for a module.

    Args:
        module_id: Module ID
        output_path: Output path for changelog (defaults to module directory)

    Returns:
        Path to changelog file
    """
    db = get_db()
    module_id_str = str(module_id) if isinstance(module_id, UUID) else module_id

    # Get module
    module = db.db["modules"].get(module_id_str)
    if not module:
        raise ValueError(f"Module {module_id} not found")

    # Get all versions
    versions = list(
        db.db["versions"].rows_where(
            "module_id = ?", [module_id_str], order_by="version DESC"
        )
    )

    if output_path is None:
        from mtm.config import get_config

        config = get_config()
        project = module.get("project", "default")
        output_path = Path(config.output_dir) / "modules" / project / "CHANGELOG.md"
    else:
        output_path = Path(output_path)

    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate changelog content
    changelog_lines = [
        f"# Changelog - {module.get('title', 'Untitled')}",
        "",
        f"**Project:** {module.get('project', 'default')}",
        f"**Module ID:** `{module_id_str}`",
        "",
        "## Versions",
        "",
    ]

    for version in versions:
        version_num = version.get("version", 0)
        major = version_num // 10000
        minor = (version_num % 10000) // 100
        patch = version_num % 100
        semver = f"{major}.{minor}.{patch}"

        changelog_lines.append(f"### Version {semver}")
        changelog_lines.append("")
        changelog_lines.append(f"**Date:** {version.get('created_at', 'Unknown')}")
        if version.get("created_by"):
            changelog_lines.append(f"**Created by:** {version.get('created_by')}")
        changelog_lines.append("")
        changelog_lines.append(f"**Changes:** {version.get('changes', 'No description')}")
        changelog_lines.append("")

        if version.get("description"):
            changelog_lines.append(f"*{version.get('description')}*")
            changelog_lines.append("")

    # Write file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(changelog_lines))

    return output_path

