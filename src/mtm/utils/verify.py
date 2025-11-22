"""Verification utilities for checking system state."""

from pathlib import Path
from typing import Optional

from mtm.config import get_config
from mtm.storage.db import get_db


class VerificationError(Exception):
    """Exception raised when verification fails."""

    pass


def check_notes_exist(project: Optional[str] = None) -> tuple[bool, str]:
    """Check that notes exist in database.

    Args:
        project: Project filter (optional)

    Returns:
        Tuple of (success, message)
    """
    db = get_db()

    if project:
        notes = list(db.db["notes"].rows_where("project = ?", [project]))
    else:
        notes = list(db.db["notes"].rows_where("1=1"))

    count = len(notes)
    if count == 0:
        return False, f"No notes found{' in project ' + project if project else ''}"
    return True, f"Found {count} note(s)"


def check_segments_exist(project: Optional[str] = None) -> tuple[bool, str]:
    """Check that segments exist in database.

    Args:
        project: Project filter (optional)

    Returns:
        Tuple of (success, message)
    """
    db = get_db()

    if project:
        segments = list(db.db["segments"].rows_where("project = ?", [project]))
    else:
        segments = list(db.db["segments"].rows_where("1=1"))

    count = len(segments)
    if count == 0:
        return False, f"No segments found{' in project ' + project if project else ''}"
    return True, f"Found {count} segment(s)"


def check_themes_exist(project: Optional[str] = None) -> tuple[bool, str]:
    """Check that at least one theme exists in database.

    Args:
        project: Project filter (optional)

    Returns:
        Tuple of (success, message)
    """
    db = get_db()

    if project:
        themes = list(db.db["themes"].rows_where("project = ?", [project]))
    else:
        themes = list(db.db["themes"].rows_where("1=1"))

    count = len(themes)
    if count == 0:
        return False, f"No themes found{' in project ' + project if project else ''}"
    return True, f"Found {count} theme(s)"


def check_extractions_contain_steps_and_definitions(project: Optional[str] = None) -> tuple[bool, str]:
    """Check that extractions contain both steps and definitions.

    Args:
        project: Project filter (optional)

    Returns:
        Tuple of (success, message)
    """
    db = get_db()

    if project:
        steps = list(db.db["extractions"].rows_where("type = ? AND project = ?", ["step", project]))
        definitions = list(db.db["extractions"].rows_where("type = ? AND project = ?", ["definition", project]))
    else:
        steps = list(db.db["extractions"].rows_where("type = ?", ["step"]))
        definitions = list(db.db["extractions"].rows_where("type = ?", ["definition"]))

    step_count = len(steps)
    def_count = len(definitions)

    if step_count == 0 and def_count == 0:
        return False, "No steps or definitions found in extractions"
    elif step_count == 0:
        return False, f"No steps found in extractions (found {def_count} definition(s))"
    elif def_count == 0:
        return False, f"No definitions found in extractions (found {step_count} step(s))"

    return True, f"Found {step_count} step(s) and {def_count} definition(s) in extractions"


def check_modules_rendered(project: Optional[str] = None) -> tuple[bool, str]:
    """Check that modules exist in database.

    Args:
        project: Project filter (optional)

    Returns:
        Tuple of (success, message)
    """
    db = get_db()

    if project:
        modules = list(db.db["modules"].rows_where("project = ?", [project]))
    else:
        modules = list(db.db["modules"].rows_where("1=1"))

    count = len(modules)
    if count == 0:
        return False, f"No modules found{' in project ' + project if project else ''}"
    return True, f"Found {count} module(s)"


def check_versions_recorded(project: Optional[str] = None) -> tuple[bool, str]:
    """Check that at least one module has version history.

    Args:
        project: Project filter (optional)

    Returns:
        Tuple of (success, message)
    """
    db = get_db()

    # Get modules
    if project:
        modules = list(db.db["modules"].rows_where("project = ?", [project]))
    else:
        modules = list(db.db["modules"].rows_where("1=1"))

    if not modules:
        return False, "No modules found to check versions"

    # Check if any module has versions
    modules_with_versions = 0
    total_versions = 0

    for module in modules:
        module_id = module["id"]
        versions = list(db.db["versions"].rows_where("module_id = ?", [module_id]))
        if versions:
            modules_with_versions += 1
            total_versions += len(versions)

    if modules_with_versions == 0:
        return False, f"No version history found for any of {len(modules)} module(s)"
    return True, f"Found version history for {modules_with_versions} module(s) ({total_versions} total versions)"


def check_role_mapping_exists(project: Optional[str] = None) -> tuple[bool, str]:
    """Check that role mappings exist.

    Args:
        project: Project filter (optional)

    Returns:
        Tuple of (success, message)
    """
    db = get_db()

    if project:
        mappings = list(db.db["topic_role_map"].rows_where("project = ?", [project]))
    else:
        mappings = list(db.db["topic_role_map"].rows_where("1=1"))

    count = len(mappings)
    if count == 0:
        return False, f"No role mappings found{' in project ' + project if project else ''}"
    return True, f"Found {count} role mapping(s)"


def check_exports_produced() -> tuple[bool, str]:
    """Check that exports have been produced.

    Args:
        None

    Returns:
        Tuple of (success, message)
    """
    config = get_config()
    exports_dir = Path(config.output_dir) / "exports"

    if not exports_dir.exists():
        return False, f"Exports directory does not exist: {exports_dir}"

    # Check for zip files
    zip_files = list(exports_dir.glob("export_*.zip"))
    if not zip_files:
        return False, f"No export zip files found in {exports_dir}"

    # Check for timestamped directories
    dirs = [d for d in exports_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    if not dirs:
        return False, f"No export directories found in {exports_dir}"

    return True, f"Found {len(zip_files)} export zip file(s) and {len(dirs)} export directory(ies)"


def run_all_checks(
    project: Optional[str] = None,
    strict: bool = False,
) -> tuple[bool, list[tuple[str, bool, str]]]:
    """Run all verification checks.

    Args:
        project: Project filter (optional)
        strict: Whether to run in strict mode (all checks must pass)

    Returns:
        Tuple of (all_passed, list of (check_name, passed, message))
    """
    checks = [
        ("Notes exist", check_notes_exist, project),
        ("Segments exist", check_segments_exist, project),
        ("Themes exist", check_themes_exist, project),
        ("Extractions contain steps and definitions", check_extractions_contain_steps_and_definitions, project),
        ("Modules rendered", check_modules_rendered, project),
        ("Versions recorded", check_versions_recorded, project),
        ("Role mapping exists", check_role_mapping_exists, project),
        ("Exports produced", check_exports_produced, None),
    ]

    results: list[tuple[str, bool, str]] = []
    all_passed = True

    for check_name, check_func, check_project in checks:
        try:
            if check_project is not None:
                passed, message = check_func(check_project)
            else:
                passed, message = check_func()
            results.append((check_name, passed, message))
            if not passed:
                all_passed = False
        except Exception as e:
            results.append((check_name, False, f"Error: {str(e)}"))
            all_passed = False

    return all_passed, results

