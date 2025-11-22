"""Export utilities for creating knowledge base exports."""

import csv
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from mtm.config import get_config
from mtm.storage.db import get_db


def export_to_csvs(
    output_dir: Path,
    project: Optional[str] = None,
) -> dict[str, Path]:
    """Export all data to CSV files.

    Args:
        output_dir: Output directory for CSV files
        project: Project name (None for all projects)

    Returns:
        Dictionary mapping table name to CSV file path
    """
    db = get_db()
    csv_files: dict[str, Path] = {}

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export steps (from extractions table)
    if project:
        steps = list(db.db["extractions"].rows_where("type = ? AND project = ?", ["step", project]))
    else:
        steps = list(db.db["extractions"].rows_where("type = ?", ["step"]))

    if steps:
        steps_path = output_dir / "steps.csv"
        with open(steps_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "id",
                    "project",
                    "step_number",
                    "title",
                    "description",
                    "date",
                    "source_file",
                    "note_id",
                ],
            )
            writer.writeheader()
            for step in steps:
                payload = json.loads(step.get("payload", "{}"))
                writer.writerow(
                    {
                        "id": step["id"],
                        "project": step.get("project", ""),
                        "step_number": payload.get("step_number", ""),
                        "title": payload.get("title", ""),
                        "description": payload.get("description", ""),
                        "date": step.get("date", ""),
                        "source_file": step.get("source_file", ""),
                        "note_id": step.get("note_id", ""),
                    }
                )
        csv_files["steps"] = steps_path

    # Export definitions
    if project:
        definitions = list(db.db["extractions"].rows_where("type = ? AND project = ?", ["definition", project]))
    else:
        definitions = list(db.db["extractions"].rows_where("type = ?", ["definition"]))

    if definitions:
        definitions_path = output_dir / "definitions.csv"
        with open(definitions_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "id",
                    "project",
                    "term",
                    "definition",
                    "context",
                    "date",
                    "source_file",
                    "note_id",
                ],
            )
            writer.writeheader()
            for definition in definitions:
                payload = json.loads(definition.get("payload", "{}"))
                writer.writerow(
                    {
                        "id": definition["id"],
                        "project": definition.get("project", ""),
                        "term": payload.get("term", ""),
                        "definition": payload.get("definition", ""),
                        "context": payload.get("context", ""),
                        "date": definition.get("date", ""),
                        "source_file": definition.get("source_file", ""),
                        "note_id": definition.get("note_id", ""),
                    }
                )
        csv_files["definitions"] = definitions_path

    # Export FAQs
    if project:
        faqs = list(db.db["extractions"].rows_where("type = ? AND project = ?", ["faq", project]))
    else:
        faqs = list(db.db["extractions"].rows_where("type = ?", ["faq"]))

    if faqs:
        faqs_path = output_dir / "faqs.csv"
        with open(faqs_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "id",
                    "project",
                    "question",
                    "answer",
                    "category",
                    "date",
                    "source_file",
                    "note_id",
                ],
            )
            writer.writeheader()
            for faq in faqs:
                payload = json.loads(faq.get("payload", "{}"))
                writer.writerow(
                    {
                        "id": faq["id"],
                        "project": faq.get("project", ""),
                        "question": payload.get("question", ""),
                        "answer": payload.get("answer", ""),
                        "category": payload.get("category", ""),
                        "date": faq.get("date", ""),
                        "source_file": faq.get("source_file", ""),
                        "note_id": faq.get("note_id", ""),
                    }
                )
        csv_files["faqs"] = faqs_path

    # Export decisions
    if project:
        decisions = list(db.db["extractions"].rows_where("type = ? AND project = ?", ["decision", project]))
    else:
        decisions = list(db.db["extractions"].rows_where("type = ?", ["decision"]))

    if decisions:
        decisions_path = output_dir / "decisions.csv"
        with open(decisions_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "id",
                    "project",
                    "decision",
                    "rationale",
                    "decision_maker",
                    "status",
                    "date",
                    "source_file",
                    "note_id",
                ],
            )
            writer.writeheader()
            for decision in decisions:
                payload = json.loads(decision.get("payload", "{}"))
                writer.writerow(
                    {
                        "id": decision["id"],
                        "project": decision.get("project", ""),
                        "decision": payload.get("decision", ""),
                        "rationale": payload.get("rationale", ""),
                        "decision_maker": payload.get("decision_maker", ""),
                        "status": payload.get("status", ""),
                        "date": decision.get("date", ""),
                        "source_file": decision.get("source_file", ""),
                        "note_id": decision.get("note_id", ""),
                    }
                )
        csv_files["decisions"] = decisions_path

    # Export actions
    if project:
        actions = list(db.db["extractions"].rows_where("type = ? AND project = ?", ["action", project]))
    else:
        actions = list(db.db["extractions"].rows_where("type = ?", ["action"]))

    if actions:
        actions_path = output_dir / "actions.csv"
        with open(actions_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "id",
                    "project",
                    "action",
                    "assignee",
                    "due_date",
                    "status",
                    "date",
                    "source_file",
                    "note_id",
                ],
            )
            writer.writeheader()
            for action in actions:
                payload = json.loads(action.get("payload", "{}"))
                writer.writerow(
                    {
                        "id": action["id"],
                        "project": action.get("project", ""),
                        "action": payload.get("action", ""),
                        "assignee": payload.get("assignee", ""),
                        "due_date": payload.get("due_date", ""),
                        "status": payload.get("status", ""),
                        "date": action.get("date", ""),
                        "source_file": action.get("source_file", ""),
                        "note_id": action.get("note_id", ""),
                    }
                )
        csv_files["actions"] = actions_path

    # Export themes
    if project:
        themes = list(db.db["themes"].rows_where("project = ?", [project]))
    else:
        themes = list(db.db["themes"].rows_where("1=1"))

    if themes:
        themes_path = output_dir / "themes.csv"
        with open(themes_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "id",
                    "project",
                    "name",
                    "description",
                    "keywords",
                    "support_count",
                    "note_id",
                    "created_at",
                ],
            )
            writer.writeheader()
            for theme in themes:
                keywords = theme.get("keywords", "[]")
                if isinstance(keywords, str):
                    keywords = json.loads(keywords)
                writer.writerow(
                    {
                        "id": theme["id"],
                        "project": theme.get("project", ""),
                        "name": theme.get("name", ""),
                        "description": theme.get("description", ""),
                        "keywords": ", ".join(keywords) if keywords else "",
                        "support_count": theme.get("support_count", 0),
                        "note_id": theme.get("note_id", ""),
                        "created_at": theme.get("created_at", ""),
                    }
                )
        csv_files["themes"] = themes_path

    return csv_files


def convert_markdown_to_pdf(
    markdown_file: Path,
    output_pdf: Optional[Path] = None,
) -> Optional[Path]:
    """Convert Markdown file to PDF using pandoc.

    Args:
        markdown_file: Path to Markdown file
        output_pdf: Output PDF path (defaults to same name with .pdf extension)

    Returns:
        Path to PDF file if successful, None if pandoc not available
    """
    if output_pdf is None:
        output_pdf = markdown_file.with_suffix(".pdf")

    # Check if pandoc is available
    pandoc_path = shutil.which("pandoc")
    if not pandoc_path:
        return None

    try:
        import subprocess

        # Run pandoc
        result = subprocess.run(
            [
                pandoc_path,
                str(markdown_file),
                "-o",
                str(output_pdf),
                "--pdf-engine=wkhtmltopdf",  # Try wkhtmltopdf first
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            # Try with default PDF engine
            result = subprocess.run(
                [pandoc_path, str(markdown_file), "-o", str(output_pdf)],
                capture_output=True,
                text=True,
                timeout=30,
            )

        if result.returncode == 0 and output_pdf.exists():
            return output_pdf
        else:
            return None

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return None


def create_export(
    project: Optional[str] = None,
    output_base: Optional[str | Path] = None,
    include_pdf: bool = True,
    enable_redaction: Optional[bool] = None,
) -> Path:
    """Create a complete knowledge base export.

    Args:
        project: Project name (None for all projects)
        output_base: Base output directory (defaults to config)
        include_pdf: Whether to include PDF conversions
        enable_redaction: Whether to redact PII (defaults to config)

    Returns:
        Path to zip file containing the export
    """
    config = get_config()

    if output_base is None:
        output_base = Path(config.output_dir) / "exports"
    else:
        output_base = Path(output_base)

    # Check for PII if redaction is enabled
    if enable_redaction is None:
        # Try to get from config
        redaction_config = getattr(config, "redaction", {})
        if isinstance(redaction_config, dict):
            enable_redaction = redaction_config.get("enable_redaction", False)
        else:
            enable_redaction = False

    # Pre-export PII check
    if enable_redaction:
        from mtm.preprocess.redact import get_redactor

        redactor = get_redactor(
            {
                "allowlist": getattr(config, "redaction", {}).get("allowlist", []) if hasattr(config, "redaction") else [],
                "denylist": getattr(config, "redaction", {}).get("denylist", []) if hasattr(config, "redaction") else [],
                "use_ner": getattr(config, "redaction", {}).get("use_ner", True) if hasattr(config, "redaction") else True,
            }
        )
        
        # Check for PII in notes
        db = get_db()
        notes = list(db.db["notes"].rows_where("1=1" if not project else "project = ?", [project] if project else []))
        pii_detected = False
        for note in notes:
            if redactor.check_for_pii(note.get("content", "")):
                pii_detected = True
                break
        
        if pii_detected:
            # Log warning but continue (redaction will be applied during export)
            import warnings
            warnings.warn("PII detected in export. Redaction will be applied.", UserWarning)

    # Create timestamped directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = output_base / timestamp
    export_dir.mkdir(parents=True, exist_ok=True)

    # Export CSVs
    csv_files = export_to_csvs(export_dir, project=project)

    # Export modules as Markdown (if available)
    from mtm.generate.build import generate_modules

    try:
        module_files = generate_modules(project=project, output_dir=export_dir / "modules")
        # Convert to PDF if requested and pandoc available
        if include_pdf:
            pdf_dir = export_dir / "pdfs"
            pdf_dir.mkdir(parents=True, exist_ok=True)
            pdf_count = 0

            for md_file in module_files:
                if md_file.suffix == ".md":
                    pdf_file = convert_markdown_to_pdf(
                        md_file, output_pdf=pdf_dir / md_file.with_suffix(".pdf").name
                    )
                    if pdf_file:
                        pdf_count += 1

            if pdf_count == 0:
                # Remove empty PDF directory
                pdf_dir.rmdir()

    except Exception:
        pass  # Continue even if module generation fails

    # Create README
    readme_path = export_dir / "README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(f"# Knowledge Base Export\n\n")
        f.write(f"**Export Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Project:** {project or 'All Projects'}\n\n")
        f.write("## Contents\n\n")
        f.write("This export contains:\n\n")
        for name, path in csv_files.items():
            f.write(f"- `{path.name}` - {name.capitalize()} data\n")
        if (export_dir / "modules").exists():
            f.write("- `modules/` - Generated module files\n")
        if (export_dir / "pdfs").exists():
            f.write("- `pdfs/` - PDF versions of modules\n")
        f.write("\n")

    # Create zip file
    zip_path = output_base / f"export_{timestamp}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Add all files in export directory
        for file_path in export_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(export_dir)
                zipf.write(file_path, arcname)

    return zip_path

