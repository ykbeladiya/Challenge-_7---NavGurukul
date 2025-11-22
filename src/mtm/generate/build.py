"""Module generation and rendering."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

import jinja2

try:
    from slugify import slugify as slugify_func
except ImportError:
    # Fallback if python-slugify not available
    import re

    def slugify_func(text: str, lowercase: bool = True, max_length: int = 50) -> str:
        """Simple slugify fallback."""
        text = text.lower() if lowercase else text
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[-\s]+", "-", text)
        return text[:max_length].strip("-")

from mtm.config import get_config
from mtm.models import Backlinks, Module
from mtm.storage.db import get_db


def slugify_text(text: str) -> str:
    """Convert text to URL-friendly slug.

    Args:
        text: Text to slugify

    Returns:
        Slugified text
    """
    return slugify_func(text, lowercase=True, max_length=50)


def load_template(template_name: str) -> jinja2.Template:
    """Load Jinja2 template from templates directory.

    Args:
        template_name: Name of template file (e.g., "tutorial.md.j2")

    Returns:
        Jinja2 Template object
    """
    template_dir = Path(__file__).parent / "templates"
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(template_dir)),
        autoescape=jinja2.select_autoescape(["html", "xml"]),
    )
    return env.get_template(template_name)


def get_module_data(module_id: str | UUID) -> dict:
    """Get all data for a module from database.

    Args:
        module_id: Module ID

    Returns:
        Dictionary with module data and related objects
    """
    db = get_db()
    module_id_str = str(module_id) if isinstance(module_id, UUID) else module_id

    # Get module
    module = db.db["modules"].get(module_id_str)
    if not module:
        return {}

    # Parse JSON arrays
    def parse_json_list(value: str | list) -> list[str]:
        if isinstance(value, list):
            return value
        try:
            return json.loads(value) if value else []
        except (json.JSONDecodeError, TypeError):
            return []

    theme_ids = parse_json_list(module.get("theme_ids", "[]"))
    step_ids = parse_json_list(module.get("step_ids", "[]"))
    definition_ids = parse_json_list(module.get("definition_ids", "[]"))
    faq_ids = parse_json_list(module.get("faq_ids", "[]"))
    decision_ids = parse_json_list(module.get("decision_ids", "[]"))
    action_ids = parse_json_list(module.get("action_ids", "[]"))
    topic_ids = parse_json_list(module.get("topic_ids", "[]"))

    # Get related objects
    themes = []
    for theme_id in theme_ids:
        theme = db.db["themes"].get(theme_id)
        if theme:
            themes.append(
                {
                    "id": theme["id"],
                    "name": theme.get("name", ""),
                    "description": theme.get("description", ""),
                    "keywords": json.loads(theme.get("keywords", "[]"))
                    if isinstance(theme.get("keywords"), str)
                    else theme.get("keywords", []),
                    "support_count": theme.get("support_count", 0),
                }
            )

    steps = []
    for step_id in step_ids:
        # Steps are stored in extractions table
        extraction = db.db["extractions"].get(step_id)
        if extraction and extraction.get("type") == "step":
            payload = json.loads(extraction.get("payload", "{}"))
            steps.append(
                {
                    "id": extraction["id"],
                    "step_number": payload.get("step_number"),
                    "title": payload.get("title", ""),
                    "description": payload.get("description", ""),
                    "roles": payload.get("roles", []),
                }
            )

    definitions = []
    for def_id in definition_ids:
        extraction = db.db["extractions"].get(def_id)
        if extraction and extraction.get("type") == "definition":
            payload = json.loads(extraction.get("payload", "{}"))
            definitions.append(
                {
                    "id": extraction["id"],
                    "term": payload.get("term", ""),
                    "definition": payload.get("definition", ""),
                    "context": payload.get("context"),
                }
            )

    faqs = []
    for faq_id in faq_ids:
        extraction = db.db["extractions"].get(faq_id)
        if extraction and extraction.get("type") == "faq":
            payload = json.loads(extraction.get("payload", "{}"))
            faqs.append(
                {
                    "id": extraction["id"],
                    "question": payload.get("question", ""),
                    "answer": payload.get("answer", ""),
                    "category": payload.get("category"),
                    "roles": payload.get("roles", []),
                }
            )

    decisions = []
    for decision_id in decision_ids:
        extraction = db.db["extractions"].get(decision_id)
        if extraction and extraction.get("type") == "decision":
            payload = json.loads(extraction.get("payload", "{}"))
            decisions.append(
                {
                    "id": extraction["id"],
                    "decision": payload.get("decision", ""),
                    "rationale": payload.get("rationale"),
                    "decision_maker": payload.get("decision_maker"),
                    "status": payload.get("status"),
                }
            )

    actions = []
    for action_id in action_ids:
        extraction = db.db["extractions"].get(action_id)
        if extraction and extraction.get("type") == "action":
            payload = json.loads(extraction.get("payload", "{}"))
            actions.append(
                {
                    "id": extraction["id"],
                    "action": payload.get("action", ""),
                    "assignee": payload.get("assignee"),
                    "due_date": payload.get("due_date"),
                    "status": payload.get("status", "pending"),
                }
            )

    # Parse backlinks
    backlinks = Backlinks()
    if module.get("note_id"):
        backlinks.note_id = UUID(module["note_id"])

    return {
        "module": module,
        "themes": themes,
        "steps": steps,
        "definitions": definitions,
        "faqs": faqs,
        "decisions": decisions,
        "actions": actions,
        "backlinks": backlinks,
    }


def render_module(
    module_id: str | UUID,
    output_dir: Optional[str | Path] = None,
    role: Optional[str] = None,
    theme_slug: Optional[str] = None,
) -> Path:
    """Render a module to markdown file.

    Args:
        module_id: Module ID
        output_dir: Output directory (defaults to config)
        role: Role name for path (optional)
        theme_slug: Theme slug for path (optional)

    Returns:
        Path to rendered file
    """
    config = get_config()
    db = get_db()

    if output_dir is None:
        output_dir = Path(config.output_dir) / "modules"
    else:
        output_dir = Path(output_dir)

    # Get module data
    module_data = get_module_data(module_id)
    if not module_data:
        raise ValueError(f"Module {module_id} not found")

    module = module_data["module"]
    project = module.get("project", "default")
    module_type = module.get("module_type", "module")
    title = module.get("title", "Untitled")

    # Determine template based on module type
    template_map = {
        "tutorial": "tutorial.md.j2",
        "faq": "faq.md.j2",
        "howto": "howto.md.j2",
        "how-to": "howto.md.j2",
        "role_path": "role_path.md.j2",
        "index": "index.md.j2",
    }
    template_name = template_map.get(module_type.lower(), "tutorial.md.j2")

    # Build output path: outputs/modules/<project>/<role>/<theme_slug>/<title>.md
    output_path = output_dir / project
    if role:
        output_path = output_path / role
    if theme_slug:
        output_path = output_path / theme_slug

    output_path.mkdir(parents=True, exist_ok=True)

    # Generate filename
    filename = f"{slugify_text(title)}.md"
    file_path = output_path / filename

    # Prepare template context
    backlinks = module_data["backlinks"]
    segment_ids = []
    if backlinks.segment_ids:
        segment_ids = [str(sid) for sid in backlinks.segment_ids]

    context = {
        "title": title,
        "description": module.get("description", ""),
        "content": module.get("content", ""),
        "project": project,
        "module_type": module_type,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": module.get("version", 1),
        "themes": module_data["themes"],
        "steps": module_data["steps"],
        "definitions": module_data["definitions"],
        "faqs": module_data["faqs"],
        "decisions": module_data["decisions"],
        "actions": module_data["actions"],
        "backlinks": {
            "note_id": str(backlinks.note_id) if backlinks.note_id else None,
            "segment_ids": segment_ids,
        },
        "counts": {
            "themes": len(module_data["themes"]),
            "steps": len(module_data["steps"]),
            "definitions": len(module_data["definitions"]),
            "faqs": len(module_data["faqs"]),
            "decisions": len(module_data["decisions"]),
            "actions": len(module_data["actions"]),
        },
        "role": role,
    }

    # Add TOC generation
    toc_items = []
    if module_data["steps"]:
        toc_items.append({"title": "Steps", "anchor": "steps"})
    if module_data["definitions"]:
        toc_items.append({"title": "Key Definitions", "anchor": "key-definitions"})
    if module_data["faqs"]:
        toc_items.append({"title": "Frequently Asked Questions", "anchor": "frequently-asked-questions"})
    context["toc"] = toc_items

    # Render template
    template = load_template(template_name)
    rendered = template.render(**context)

    # Write file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(rendered)

    return file_path


def generate_project_index(
    project: str,
    output_dir: Optional[str | Path] = None,
) -> Path:
    """Generate project index.

    Args:
        project: Project name
        output_dir: Output directory (defaults to config)

    Returns:
        Path to rendered index file
    """
    config = get_config()
    db = get_db()

    if output_dir is None:
        output_dir = Path(config.output_dir) / "modules"
    else:
        output_dir = Path(output_dir)

    # Get all modules for project
    modules = list(db.db["modules"].rows_where("project = ?", [project]))

    # Get themes
    themes = list(db.db["themes"].rows_where("project = ?", [project]))

    # Get role mappings
    role_mappings = list(db.db["topic_role_map"].rows_where("project = ?", [project]))

    # Organize role mappings
    roles_dict: dict[str, list] = {}
    for mapping in role_mappings:
        role = mapping.get("role", "Unknown")
        if role not in roles_dict:
            roles_dict[role] = []
        roles_dict[role].append(mapping)

    # Prepare context
    context = {
        "title": f"{project} - Project Index",
        "description": f"Index of all modules and content for {project} project",
        "project": project,
        "module_type": "index",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": 1,
        "counts": {
            "modules": len(modules),
            "themes": len(themes),
            "steps": 0,
            "definitions": 0,
            "faqs": 0,
            "decisions": 0,
            "actions": 0,
            "topics": 0,
        },
        "all_modules": [
            {
                "title": m.get("title", "Untitled"),
                "module_type": m.get("module_type", "module"),
                "project": m.get("project", project),
                "version": m.get("version", 1),
                "description": m.get("description", ""),
                "filename": f"{slugify_text(m.get('title', 'untitled'))}.md",
            }
            for m in modules
        ],
        "all_themes": [
            {
                "name": t.get("name", ""),
                "description": t.get("description", ""),
                "project": t.get("project", project),
                "support_count": t.get("support_count", 0),
                "keywords": json.loads(t.get("keywords", "[]"))
                if isinstance(t.get("keywords"), str)
                else t.get("keywords", []),
            }
            for t in themes
        ],
        "role_mappings": roles_dict,
        "backlinks": {"note_id": None, "segment_ids": []},
        "toc": [
            {"title": "Overview", "anchor": "overview"},
            {"title": "Project Index", "anchor": "project-index"},
            {"title": "All Modules", "anchor": "all-modules"},
            {"title": "All Themes", "anchor": "all-themes"},
        ],
    }

    # Render template
    template = load_template("index.md.j2")
    rendered = template.render(**context)

    # Write file
    output_path = output_dir / project
    output_path.mkdir(parents=True, exist_ok=True)
    file_path = output_path / "index.md"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(rendered)

    return file_path


def generate_global_index(
    output_dir: Optional[str | Path] = None,
) -> Path:
    """Generate global index across all projects.

    Args:
        output_dir: Output directory (defaults to config)

    Returns:
        Path to rendered index file
    """
    config = get_config()
    db = get_db()

    if output_dir is None:
        output_dir = Path(config.output_dir) / "modules"
    else:
        output_dir = Path(output_dir)

    # Get all modules
    modules = list(db.db["modules"].rows_where("1=1"))

    # Get all themes
    themes = list(db.db["themes"].rows_where("1=1"))

    # Get all projects
    projects = set()
    for module in modules:
        projects.add(module.get("project", "default"))
    for theme in themes:
        projects.add(theme.get("project", "global"))

    # Organize by project
    projects_data: dict[str, dict] = {}
    for project in projects:
        proj_modules = [m for m in modules if m.get("project") == project]
        proj_themes = [t for t in themes if t.get("project") == project]
        proj_role_mappings = list(db.db["topic_role_map"].rows_where("project = ?", [project]))

        # Organize role mappings
        roles_dict: dict[str, dict] = {}
        for mapping in proj_role_mappings:
            role = mapping.get("role", "Unknown")
            if role not in roles_dict:
                roles_dict[role] = {"count": 0, "confidences": []}
            roles_dict[role]["count"] += 1
            roles_dict[role]["confidences"].append(mapping.get("confidence", 0.0))

        # Calculate average confidence
        for role, data in roles_dict.items():
            if data["confidences"]:
                data["avg_confidence"] = sum(data["confidences"]) / len(data["confidences"])
            else:
                data["avg_confidence"] = 0.0
            del data["confidences"]

        projects_data[project] = {
            "modules": [
                {
                    "title": m.get("title", "Untitled"),
                    "module_type": m.get("module_type", "module"),
                    "filename": f"{slugify_text(m.get('title', 'untitled'))}.md",
                }
                for m in proj_modules
            ],
            "themes": [
                {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "support_count": t.get("support_count", 0),
                }
                for t in proj_themes
            ],
            "roles": roles_dict,
            "counts": {
                "modules": len(proj_modules),
                "themes": len(proj_themes),
                "steps": 0,
                "definitions": 0,
                "faqs": 0,
                "decisions": 0,
                "actions": 0,
            },
        }

    # Prepare context
    context = {
        "title": "Global Index",
        "description": "Index of all modules and content across all projects",
        "project": "global",
        "module_type": "index",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": 1,
        "counts": {
            "modules": len(modules),
            "themes": len(themes),
            "steps": 0,
            "definitions": 0,
            "faqs": 0,
            "decisions": 0,
            "actions": 0,
            "topics": 0,
        },
        "projects": projects_data,
        "all_modules": [
            {
                "title": m.get("title", "Untitled"),
                "module_type": m.get("module_type", "module"),
                "project": m.get("project", "default"),
                "version": m.get("version", 1),
                "description": m.get("description", ""),
                "filename": f"{slugify_text(m.get('title', 'untitled'))}.md",
            }
            for m in modules
        ],
        "all_themes": [
            {
                "name": t.get("name", ""),
                "description": t.get("description", ""),
                "project": t.get("project", "global"),
                "support_count": t.get("support_count", 0),
                "keywords": json.loads(t.get("keywords", "[]"))
                if isinstance(t.get("keywords"), str)
                else t.get("keywords", []),
            }
            for t in themes
        ],
        "backlinks": {"note_id": None, "segment_ids": []},
        "toc": [
            {"title": "Overview", "anchor": "overview"},
            {"title": "Project Index", "anchor": "project-index"},
            {"title": "Per-Project Indexes", "anchor": "per-project-indexes"},
        ],
    }

    # Render template
    template = load_template("index.md.j2")
    rendered = template.render(**context)

    # Write file
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / "index.md"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(rendered)

    return file_path


def generate_modules(
    project: Optional[str] = None,
    role: Optional[str] = None,
    output_dir: Optional[str | Path] = None,
) -> list[Path]:
    """Generate all modules for a project or globally.

    Args:
        project: Project name (None for all projects)
        role: Role name for filtering (optional)
        output_dir: Output directory (defaults to config)

    Returns:
        List of rendered file paths
    """
    db = get_db()
    rendered_files: list[Path] = []

    # Get modules
    if project:
        modules = list(db.db["modules"].rows_where("project = ?", [project]))
    else:
        modules = list(db.db["modules"].rows_where("1=1"))

    # Get role mappings for themes
    role_mappings: dict[str, list[str]] = {}  # theme_id -> [roles]
    if role:
        mappings = list(db.db["topic_role_map"].rows_where("role = ?", [role]))
        for mapping in mappings:
            theme_id = mapping.get("topic_id")
            if theme_id not in role_mappings:
                role_mappings[theme_id] = []
            role_mappings[theme_id].append(mapping.get("role"))

    # Render each module
    for module in modules:
        module_id = module["id"]
        module_project = module.get("project", "default")
        module_themes = json.loads(module.get("theme_ids", "[]"))

        # Determine theme slug
        theme_slug = None
        if module_themes:
            first_theme_id = module_themes[0]
            theme = db.db["themes"].get(first_theme_id)
            if theme:
                theme_slug = slugify_text(theme.get("name", "theme"))

        # Render module
        try:
            file_path = render_module(
                module_id,
                output_dir=output_dir,
                role=role,
                theme_slug=theme_slug,
            )
            rendered_files.append(file_path)
        except Exception as e:
            print(f"Error rendering module {module_id}: {e}")
            continue

    # Generate indexes
    if project:
        try:
            index_path = generate_project_index(project, output_dir=output_dir)
            rendered_files.append(index_path)
        except Exception as e:
            print(f"Error generating project index: {e}")
    else:
        try:
            index_path = generate_global_index(output_dir=output_dir)
            rendered_files.append(index_path)
        except Exception as e:
            print(f"Error generating global index: {e}")

    return rendered_files

