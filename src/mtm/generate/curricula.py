"""Generate role-based curricula from extracted modules."""

import json
from pathlib import Path
from typing import Any, Optional

import yaml

from mtm.config import get_config
from mtm.storage.db import get_db


def load_role_taxonomy() -> dict[str, Any]:
    """Load role taxonomy from config file.

    Returns:
        Dictionary with role taxonomy and learning paths
    """
    config = get_config()
    taxonomy_path = Path("configs") / "role_taxonomy.yaml"
    
    if not taxonomy_path.exists():
        # Try alternative path
        taxonomy_path = Path(config.output_dir).parent / "configs" / "role_taxonomy.yaml"
    
    if not taxonomy_path.exists():
        return {}
    
    with open(taxonomy_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def generate_role_curriculum(
    role: str,
    project: Optional[str] = None,
    output_dir: Optional[str | Path] = None,
) -> Path:
    """Generate a role-based curriculum from extracted modules.

    Args:
        role: Role name
        project: Project name (None for all projects)
        output_dir: Output directory for curriculum file

    Returns:
        Path to generated curriculum file
    """
    config = get_config()
    db = get_db()
    taxonomy = load_role_taxonomy()
    
    if output_dir is None:
        output_dir = Path(config.output_dir) / "curricula"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get learning path configuration for role
    learning_paths = taxonomy.get("learning_paths", {})
    role_path = learning_paths.get(role, {})
    
    # Get modules for this role
    if project:
        modules = list(
            db.db["modules"].rows_where(
                "project = ? AND module_type IN ('tutorial', 'howto', 'faq')",
                [project],
            )
        )
    else:
        modules = list(
            db.db["modules"].rows_where(
                "module_type IN ('tutorial', 'howto', 'faq')"
            )
        )
    
    # Get role mappings
    role_mappings = list(
        db.db["topic_role_map"].rows_where("role = ?", [role])
    )
    
    # Map theme IDs to modules
    theme_to_modules: dict[str, list[dict[str, Any]]] = {}
    for module in modules:
        theme_ids_json = module.get("theme_ids", "[]")
        try:
            theme_ids = json.loads(theme_ids_json) if isinstance(theme_ids_json, str) else theme_ids_json
        except (json.JSONDecodeError, TypeError):
            theme_ids = []
        
        for theme_id in theme_ids:
            if theme_id not in theme_to_modules:
                theme_to_modules[theme_id] = []
            theme_to_modules[theme_id].append(module)
    
    # Build curriculum based on learning path
    curriculum_modules: list[dict[str, Any]] = []
    
    if role_path:
        path_modules = role_path.get("modules", [])
        for path_module in path_modules:
            module_type = path_module.get("type", "tutorial")
            theme_keywords = path_module.get("theme_keywords", [])
            order = path_module.get("order", 0)
            
            # Find matching modules
            for theme_id, mods in theme_to_modules.items():
                # Get theme keywords
                theme = db.db["themes"].get(theme_id)
                if not theme:
                    continue
                
                theme_keywords_json = theme.get("keywords", "[]")
                try:
                    theme_kw = json.loads(theme_keywords_json) if isinstance(theme_keywords_json, str) else theme_keywords_json
                except (json.JSONDecodeError, TypeError):
                    theme_kw = []
                
                # Check if theme keywords match
                if any(kw.lower() in " ".join(theme_kw).lower() for kw in theme_keywords):
                    for mod in mods:
                        if mod.get("module_type") == module_type:
                            curriculum_modules.append({
                                "order": order,
                                "module_id": mod["id"],
                                "title": mod.get("title", ""),
                                "description": mod.get("description", ""),
                                "module_type": module_type,
                            })
                            break
    
    # Sort by order
    curriculum_modules.sort(key=lambda x: x.get("order", 0))
    
    # Generate curriculum markdown
    curriculum_path = output_dir / f"{role.lower().replace(' ', '_')}_curriculum.md"
    
    with open(curriculum_path, "w", encoding="utf-8") as f:
        f.write(f"# {role} Learning Curriculum\n\n")
        f.write(f"**Role:** {role}\n")
        f.write(f"**Project:** {project or 'All Projects'}\n\n")
        
        if role_path:
            prerequisites = role_path.get("prerequisites", [])
            if prerequisites:
                f.write("## Prerequisites\n\n")
                for prereq in prerequisites:
                    f.write(f"- {prereq}\n")
                f.write("\n")
        
        f.write("## Curriculum Modules\n\n")
        
        for i, mod in enumerate(curriculum_modules, 1):
            f.write(f"### {i}. {mod['title']}\n\n")
            if mod.get("description"):
                f.write(f"{mod['description']}\n\n")
            f.write(f"**Type:** {mod['module_type']}\n")
            f.write(f"**Module ID:** {mod['module_id']}\n\n")
        
        if role_path:
            completion_criteria = role_path.get("completion_criteria", [])
            if completion_criteria:
                f.write("## Completion Criteria\n\n")
                for criterion in completion_criteria:
                    f.write(f"- {criterion}\n")
    
    return curriculum_path


def generate_all_curricula(
    project: Optional[str] = None,
    output_dir: Optional[str | Path] = None,
) -> list[Path]:
    """Generate curricula for all roles.

    Args:
        project: Project name (None for all projects)
        output_dir: Output directory for curriculum files

    Returns:
        List of paths to generated curriculum files
    """
    taxonomy = load_role_taxonomy()
    learning_paths = taxonomy.get("learning_paths", {})
    
    curricula = []
    for role in learning_paths.keys():
        try:
            curriculum_path = generate_role_curriculum(role, project=project, output_dir=output_dir)
            curricula.append(curriculum_path)
        except Exception as e:
            # Log error but continue
            print(f"Error generating curriculum for {role}: {e}")
    
    return curricula

