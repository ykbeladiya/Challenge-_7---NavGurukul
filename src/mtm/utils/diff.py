"""Diff utilities for comparing modules and generating unified diffs."""

import difflib
from pathlib import Path
from typing import Optional


def generate_unified_diff(
    old_text: str,
    new_text: str,
    old_label: str = "old",
    new_label: str = "new",
    context_lines: int = 3,
) -> str:
    """Generate unified diff between two texts.

    Args:
        old_text: Old text content
        new_text: New text content
        old_label: Label for old version
        new_label: Label for new version
        context_lines: Number of context lines to include

    Returns:
        Unified diff as string
    """
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=old_label,
        tofile=new_label,
        lineterm="",
        n=context_lines,
    )

    return "".join(diff)


def generate_html_diff(
    old_text: str,
    new_text: str,
    old_label: str = "old",
    new_label: str = "new",
    context_lines: int = 3,
) -> str:
    """Generate HTML diff between two texts.

    Args:
        old_text: Old text content
        new_text: New text content
        old_label: Label for old version
        new_label: Label for new version
        context_lines: Number of context lines to include

    Returns:
        HTML diff as string
    """
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    differ = difflib.HtmlDiff()
    html_diff = differ.make_file(
        old_lines,
        new_lines,
        fromdesc=old_label,
        todesc=new_label,
        context=True,
        numlines=context_lines,
    )

    return html_diff


def generate_markdown_diff(
    old_text: str,
    new_text: str,
    old_label: str = "old",
    new_label: str = "new",
    context_lines: int = 3,
) -> str:
    """Generate Markdown-formatted diff.

    Args:
        old_text: Old text content
        new_text: New text content
        old_label: Label for old version
        new_label: Label for new version
        context_lines: Number of context lines to include

    Returns:
        Markdown diff as string
    """
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    diff_lines = [
        f"# Diff: {old_label} → {new_label}",
        "",
        "## Unified Diff",
        "",
        "```diff",
    ]

    # Generate unified diff
    unified = generate_unified_diff(old_text, new_text, old_label, new_label, context_lines)
    diff_lines.append(unified)
    diff_lines.append("```")
    diff_lines.append("")

    # Add summary
    added = sum(1 for line in new_lines if line not in old_lines)
    removed = sum(1 for line in old_lines if line not in new_lines)

    diff_lines.append("## Summary")
    diff_lines.append("")
    diff_lines.append(f"- **Lines added:** {added}")
    diff_lines.append(f"- **Lines removed:** {removed}")
    diff_lines.append(f"- **Context lines:** {context_lines}")

    return "\n".join(diff_lines)


def diff_modules(
    module_id1: str,
    module_id2: str,
    output_path: Optional[str | Path] = None,
    format: str = "markdown",
    context_lines: int = 3,
) -> Path:
    """Generate diff between two module versions.

    Args:
        module_id1: First module/version ID
        module_id2: Second module/version ID
        output_path: Output path for diff file
        format: Output format (markdown, html, unified)
        context_lines: Number of context lines

    Returns:
        Path to diff file
    """
    from mtm.storage.db import get_db

    db = get_db()

    # Get modules/versions
    module1 = db.db["modules"].get(module_id1) or db.db["versions"].get(module_id1)
    module2 = db.db["modules"].get(module_id2) or db.db["versions"].get(module_id2)

    if not module1:
        raise ValueError(f"Module/version {module_id1} not found")
    if not module2:
        raise ValueError(f"Module/version {module_id2} not found")

    # Get content
    content1 = module1.get("content", "")
    content2 = module2.get("content", "")

    # Generate labels
    label1 = f"{module1.get('title', 'Module')} (v{module1.get('version', 1)})"
    label2 = f"{module2.get('title', 'Module')} (v{module2.get('version', 1)})"

    # Generate diff based on format
    if format == "html":
        diff_content = generate_html_diff(content1, content2, label1, label2, context_lines)
        ext = "html"
    elif format == "unified":
        diff_content = generate_unified_diff(content1, content2, label1, label2, context_lines)
        ext = "diff"
    else:  # markdown
        diff_content = generate_markdown_diff(content1, content2, label1, label2, context_lines)
        ext = "md"

    # Write file
    if output_path is None:
        from mtm.config import get_config

        config = get_config()
        output_path = Path(config.output_dir) / "diffs" / f"{module_id1}_vs_{module_id2}.{ext}"
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(diff_content)

    return output_path

