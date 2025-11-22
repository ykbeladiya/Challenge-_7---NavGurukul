"""CLI interface for meeting-to-modules."""

import builtins
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from mtm import __version__
from mtm.config import get_config
from mtm.ingest.docx_loader import parse_docx
from mtm.ingest.md_txt import parse_md_txt
from mtm.ingest.pdf_loader import parse_pdf
from mtm.storage.db import get_db
from mtm.utils.logging import create_logger

app = typer.Typer(
    name="mtm",
    help="Meeting-to-modules: Convert meeting notes to structured modules\n\n"
    "Examples:\n"
    "  mtm init-sample              # Generate sample data\n"
    "  mtm ingest data/notes/       # Ingest notes from directory\n"
    "  mtm preprocess file.md       # Preprocess a file\n"
    "  mtm analyze                  # Analyze themes\n"
    "  mtm extract                  # Extract structured info\n"
    "  mtm generate                 # Generate modules\n"
    "  mtm export                   # Export knowledge base\n"
    "  mtm search 'deployment'      # Search content\n"
    "  mtm list --themes            # List themes\n"
    "  mtm verify                   # Verify system",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"mtm version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        help="Show version and exit",
    ),
) -> None:
    """Meeting-to-modules CLI."""
    pass


@app.command()
def ingest(
    source: Optional[str] = typer.Argument(None, help="Source file or directory (default: use config input_dirs)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory"),
    format: Optional[str] = typer.Option(None, "--format", "-f", help="Input format (auto-detect if not specified)"),
) -> None:
    """Ingest meeting notes from various sources.
    
    Supports Markdown (.md), Text (.txt), Word (.docx), and PDF (.pdf) files.
    Files are parsed, deduplicated, and stored in the database.
    
    Examples:
        mtm ingest                          # Ingest from config input_dirs
        mtm ingest data/meeting-notes/      # Ingest from specific directory
        mtm ingest meeting.md               # Ingest a single file
    """
    logger = create_logger("ingest")
    config = get_config()
    db = get_db()

    # Determine input directories
    if source:
        input_paths = [Path(source)]
    else:
        input_paths = [Path(d) for d in config.input_dirs]

    # Collect all files to process
    files_to_process: list[Path] = []
    for input_path in input_paths:
        input_path = Path(input_path)
        if not input_path.exists():
            console.print(f"[yellow]Warning: Path does not exist: {input_path}[/yellow]")
            continue

        if input_path.is_file():
            files_to_process.append(input_path)
        elif input_path.is_dir():
            # Recursively find all supported files
            for ext in [".md", ".txt", ".docx", ".pdf"]:
                files_to_process.extend(input_path.rglob(f"*{ext}"))

    if not files_to_process:
        logger.add_error("no_files", "No files found to ingest", "Check input_dirs in config or provide a source path")
        logger.finish(success=False)
        raise typer.Exit(1)

    console.print(f"[green]Found {len(files_to_process)} file(s) to process[/green]")

    # Statistics
    stats: dict[str, int] = defaultdict(int)
    skipped_files: list[tuple[str, str]] = []  # (file, reason)

    # Route files by extension
    extension_routes = {
        ".md": parse_md_txt,
        ".txt": parse_md_txt,
        ".docx": parse_docx,
        ".pdf": parse_pdf,
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Processing files...", total=len(files_to_process))

        for file_path in files_to_process:
            file_ext = file_path.suffix.lower()
            progress.update(task, description=f"[cyan]Processing {file_path.name}...")

            # Skip unsupported extensions
            if file_ext not in extension_routes:
                stats["skipped"] += 1
                skipped_files.append((str(file_path), f"Unsupported extension: {file_ext}"))
                logger.add_skipped_file(str(file_path), f"Unsupported extension: {file_ext}")
                progress.advance(task)
                continue

            try:
                # Parse file
                parser = extension_routes[file_ext]
                note = parser(file_path)

                # Compute content hash
                content = note.content or ""
                content_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()

                # Check for duplicates
                existing = db.find_note_by_hash(content_sha256)
                if existing:
                    stats["skipped"] += 1
                    skipped_files.append((str(file_path), "Duplicate content (same SHA256)"))
                    logger.add_skipped_file(str(file_path), "Duplicate content (same SHA256)")
                    progress.advance(task)
                    continue

                # Get file metadata
                file_stat = file_path.stat()
                mtime = datetime.fromtimestamp(file_stat.st_mtime)
                size = file_stat.st_size

                # Infer project from parent directory if missing
                if note.project == "default":
                    # Try to infer from parent directory name
                    parent_name = file_path.parent.name
                    if parent_name and parent_name not in ["notes", "data", "seed", "input", "inputs"]:
                        note.project = parent_name
                    else:
                        # Try grandparent
                        grandparent_name = file_path.parent.parent.name
                        if grandparent_name and grandparent_name not in ["data", "seed", "input", "inputs"]:
                            note.project = grandparent_name

                # Update metadata with file info
                note.metadata.update(
                    {
                        "source_path": str(file_path),
                        "mtime": mtime.isoformat(),
                        "size": str(size),
                    }
                )

                # Persist to database
                db.upsert_note(
                    note_id=note.id,
                    project=note.project,
                    date=note.date,
                    source_file=str(file_path),
                    content=note.content,
                    title=note.title,
                    metadata=note.metadata,
                    content_sha256=content_sha256,
                    source_path=str(file_path),
                    mtime=mtime,
                    size=size,
                )

                # Update statistics
                stats[file_ext] = stats.get(file_ext, 0) + 1
                stats["ingested"] = stats.get("ingested", 0) + 1
                logger.increment_count("ingested")
                logger.increment_count(file_ext.replace(".", ""))

            except Exception as e:
                import traceback
                error_type = type(e).__name__
                error_msg = str(e) if str(e) else repr(e)
                if not error_msg or error_msg == f"{error_type}()":
                    error_msg = f"{error_type}: {repr(e)}"
                error_trace = traceback.format_exc()
                stats["errors"] = stats.get("errors", 0) + 1
                skipped_files.append((str(file_path), f"Error: {error_msg}"))
                logger.add_error("processing_error", f"Error processing {file_path}: {error_msg}", "Check file format and permissions")
                console.print(f"[red]Error processing {file_path}: {error_msg}[/red]")
                # Always print traceback for debugging
                console.print(f"[dim]Traceback: {error_trace}[/dim]")

            progress.advance(task)

    # Display summary table
    table = Table(title="Ingestion Summary", show_header=True, header_style="bold magenta")
    table.add_column("Type", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right", style="green")

    # Add file type counts
    for ext in [".md", ".txt", ".docx", ".pdf"]:
        count = stats.get(ext, 0)
        if count > 0:
            table.add_row(f"{ext.upper()} files", str(count))

    # Add summary rows
    table.add_row("", "")  # Separator
    table.add_row("[bold]Total Ingested[/bold]", f"[bold green]{stats.get('ingested', 0)}[/bold green]")
    table.add_row("[bold]Skipped[/bold]", f"[yellow]{stats.get('skipped', 0)}[/yellow]")
    table.add_row("[bold]Errors[/bold]", f"[red]{stats.get('errors', 0)}[/red]")

    console.print()
    console.print(table)

    # Update logger counts
    for ext in [".md", ".txt", ".docx", ".pdf"]:
        count = stats.get(ext, 0)
        if count > 0:
            logger.increment_count(ext.replace(".", ""), count)
    logger.increment_count("skipped", stats.get("skipped", 0))
    logger.increment_count("errors", stats.get("errors", 0))

    # Finish logging
    has_errors = stats.get("errors", 0) > 0
    logger.finish(success=not has_errors)

    # Exit with error code if there were errors
    if has_errors:
        raise typer.Exit(1)


@app.command()
def preprocess(
    input: Optional[str] = typer.Argument(None, help="Input file path (default: process all ingested notes)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory"),
    clean: bool = typer.Option(True, "--clean", "--no-clean", help="Clean and normalize text"),
) -> None:
    """Preprocess meeting notes (clean, normalize, segment).
    
    Cleans text, normalizes formatting, and segments content into smaller chunks
    for analysis. Segments are stored in the database.
    
    Examples:
        mtm preprocess meeting.md           # Preprocess a single file
        mtm preprocess file.md --no-clean   # Preprocess without cleaning
    """
    logger = create_logger("preprocess")
    from mtm.preprocess.clean import preprocess_file

    try:
        if input:
            # Process specific file
            input_path = Path(input)
            if not input_path.exists():
                logger.add_error("file_not_found", f"Input path does not exist: {input}", "Check the file path and try again")
                logger.finish(success=False)
                raise typer.Exit(1)

            if input_path.is_file():
                segments = preprocess_file(input_path, persist=True)
                logger.increment_count("segments_created", len(segments))
                console.print(f"[green]Created {len(segments)} segment(s)[/green]")
                logger.finish(success=True)
            else:
                logger.add_error("not_implemented", "Directory preprocessing not yet implemented", "Process files individually for now")
                logger.finish(success=False)
                console.print("[yellow]Directory preprocessing not yet implemented[/yellow]")
                raise typer.Exit(1)
        else:
            # Process all ingested notes
            db = get_db()
            notes = builtins.list(db.db["notes"].rows_where("1=1"))
            
            if not notes:
                logger.add_error("no_notes", "No notes found in database", "Run 'ingest' command first to add notes")
                logger.finish(success=False)
                console.print("[yellow]No notes found. Run 'ingest' first.[/yellow]")
                raise typer.Exit(1)
            
            total_segments = 0
            for note in notes:
                source_path = note.get("source_path")
                if source_path and Path(source_path).exists():
                    segments = preprocess_file(Path(source_path), persist=True)
                    total_segments += len(segments)
                    logger.increment_count("segments_created", len(segments))
            
            logger.increment_count("notes_processed", len(notes))
            console.print(f"[green]Processed {len(notes)} note(s), created {total_segments} segment(s)[/green]")
            logger.finish(success=True)

    except Exception as e:
        import traceback
        error_type = type(e).__name__
        error_msg = str(e) if str(e) else repr(e)
        error_trace = traceback.format_exc()
        logger.add_error("preprocess_error", f"Error preprocessing: {error_msg}", "Check file format and permissions")
        logger.finish(success=False)
        console.print(f"[red]Error preprocessing: {error_type}: {error_msg}[/red]")
        # Print traceback for debugging
        if not error_msg or "recursion" in error_msg.lower() or "RecursionError" in error_type:
            console.print(f"[dim]Traceback:\n{error_trace}[/dim]")
        raise typer.Exit(1)


@app.command()
def analyze(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name (default: all projects)"),
) -> None:
    """Analyze meeting notes to identify themes, topics, and roles.
    
    Uses TF-IDF vectorization and KMeans clustering to identify themes across
    segments. Maps segments and themes to roles based on content analysis.
    
    Examples:
        mtm analyze                         # Analyze all projects
        mtm analyze --project Onboarding   # Analyze specific project
    """
    logger = create_logger("analyze")
    from mtm.analyze.themes import analyze_themes
    from mtm.analyze.mapping import map_segments_to_roles, map_themes_to_roles

    try:
        # Analyze themes
        themes = analyze_themes(project=project, persist=True)
        logger.increment_count("themes_created", len(themes))

        # Map roles
        segment_mappings = map_segments_to_roles(project=project, persist=True)
        theme_mappings = map_themes_to_roles(project=project, persist=True)
        logger.increment_count("role_mappings_created", len(segment_mappings) + len(theme_mappings))

        console.print(f"[green]Analyzed {len(themes)} theme(s)[/green]")
        logger.finish(success=True)

    except Exception as e:
        logger.add_error("analysis_error", f"Error during analysis: {str(e)}", "Ensure segments exist by running 'preprocess' first")
        logger.finish(success=False)
        console.print(f"[red]Error during analysis: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def extract(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name (default: all projects)"),
) -> None:
    """Extract structured information from meeting notes.
    
    Extracts steps, definitions, FAQs, decisions, and actions from notes.
    Results are stored in the extractions table.
    
    Examples:
        mtm extract                         # Extract from all projects
        mtm extract --project Deployment   # Extract from specific project
    """
    logger = create_logger("extract")
    from mtm.storage.db import get_db
    from mtm.extract.extractors import extract_all
    from mtm.models import Segment

    try:
        db = get_db()

        # Get all notes for project
        if project:
            notes = builtins.list(db.db["notes"].rows_where("project = ?", [project]))
        else:
            notes = builtins.list(db.db["notes"].rows_where("1=1"))

        total_extractions = 0

        for note in notes:
            # Get segments for this note
            segments_data = builtins.list(db.db["segments"].rows_where("note_id = ?", [note["id"]]))
            segments = [
                Segment(
                    id=seg["id"],
                    note_id=seg["note_id"],
                    project=seg.get("project", ""),
                    date=datetime.fromisoformat(seg.get("date", datetime.now().isoformat())),
                    source_file=seg.get("source_file", ""),
                    content=seg.get("content", ""),
                )
                for seg in segments_data
            ]

            if segments:
                # Extract all types
                extractions = extract_all(
                    segments,
                    note["id"],
                    note.get("project", "default"),
                    datetime.fromisoformat(note.get("date", datetime.now().isoformat())),
                    note.get("source_file", ""),
                )

                # Persist extractions
                for ext_type, ext_list in extractions.items():
                    for ext in ext_list:
                        db.upsert_extraction(
                            extraction_id=ext.id,
                            extraction_type=ext_type,
                            project=ext.project,
                            payload=ext.model_dump(),
                            note_id=note["id"],
                            source_file=ext.source_file,
                            date=ext.date,
                        )
                        total_extractions += 1
                        logger.increment_count(ext_type)

        console.print(f"[green]Extracted {total_extractions} item(s)[/green]")
        logger.finish(success=True)

    except Exception as e:
        logger.add_error("extraction_error", f"Error during extraction: {str(e)}", "Ensure segments exist by running 'preprocess' first")
        logger.finish(success=False)
        console.print(f"[red]Error during extraction: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def generate(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name (default: all projects)"),
    role: Optional[str] = typer.Option(None, "--role", "-r", help="Role name for filtering"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory"),
) -> None:
    """Generate modules from meeting notes using Jinja2 templates.
    
    Creates formatted Markdown modules (tutorials, FAQs, how-tos, role paths)
    from extracted information. Modules are saved to outputs/modules/.
    
    Examples:
        mtm generate                        # Generate all modules
        mtm generate --project Support     # Generate for specific project
        mtm generate --role Developer      # Generate for specific role
    """
    logger = create_logger("generate")
    from mtm.generate.build import generate_modules

    try:
        rendered_files = generate_modules(project=project, role=role, output_dir=output)

        if rendered_files:
            logger.increment_count("files_generated", len(rendered_files))
            console.print(f"[green]Generated {len(rendered_files)} file(s):[/green]")
            for file_path in rendered_files[:20]:  # Show first 20
                console.print(f"  [dim]{file_path}[/dim]")
            if len(rendered_files) > 20:
                console.print(f"  ... and {len(rendered_files) - 20} more")
        else:
            logger.add_error("no_modules", "No modules generated", "Run 'ingest' and 'analyze' commands first to create modules")
            logger.finish(success=False)
            raise typer.Exit(1)

        logger.finish(success=True)

    except Exception as e:
        logger.add_error("generation_error", f"Error generating modules: {str(e)}", "Check database connection and module data")
        logger.finish(success=False)
        console.print(f"[red]Error generating modules: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def diff(
    file1: str = typer.Argument(..., help="First module/version ID or file path"),
    file2: str = typer.Argument(..., help="Second module/version ID or file path"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for diff"),
    format: str = typer.Option("markdown", "--format", "-f", help="Output format (markdown, html, unified)"),
    context: int = typer.Option(3, "--context", "-c", help="Number of context lines"),
) -> None:
    """Generate diff between two module versions or files.
    
    Compares two modules or versions and generates a diff in the specified format.
    Supports Markdown, HTML, and unified diff formats.
    
    Examples:
        mtm diff <module_id1> <module_id2>        # Compare module versions
        mtm diff file1.md file2.md                 # Compare files
        mtm diff <id1> <id2> --format html         # Generate HTML diff
        mtm diff <id1> <id2> --context 5          # Show 5 context lines
    """
    logger = create_logger("diff")
    from pathlib import Path

    from mtm.utils.diff import diff_modules, generate_markdown_diff, generate_html_diff, generate_unified_diff

    try:
        # Check if inputs are files or module IDs
        file1_path = Path(file1)
        file2_path = Path(file2)

        if file1_path.exists() and file2_path.exists():
            # Compare files
            with open(file1_path, "r", encoding="utf-8") as f:
                content1 = f.read()
            with open(file2_path, "r", encoding="utf-8") as f:
                content2 = f.read()

            if format == "html":
                diff_content = generate_html_diff(content1, content2, str(file1_path), str(file2_path), context)
                ext = "html"
            elif format == "unified":
                diff_content = generate_unified_diff(content1, content2, str(file1_path), str(file2_path), context)
                ext = "diff"
            else:  # markdown
                diff_content = generate_markdown_diff(content1, content2, str(file1_path), str(file2_path), context)
                ext = "md"

            # Write output
            if output:
                output_path = Path(output)
            else:
                output_path = Path("outputs") / "diffs" / f"{file1_path.stem}_vs_{file2_path.stem}.{ext}"

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(diff_content)

            logger.increment_count("diffs_created")
            console.print(f"[green]Diff written to:[/green] {output_path}")

        else:
            # Compare modules/versions by ID
            diff_path = diff_modules(file1, file2, output_path=output, format=format, context_lines=context)
            logger.increment_count("diffs_created")
            console.print(f"[green]Diff written to:[/green] {diff_path}")

        logger.finish(success=True)

    except Exception as e:
        logger.add_error("diff_error", f"Error generating diff: {str(e)}", "Verify file paths or module IDs exist in database")
        logger.finish(success=False)
        console.print(f"[red]Error generating diff: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list(
    themes: bool = typer.Option(False, "--themes", help="List themes"),
    modules: bool = typer.Option(False, "--modules", help="List modules"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project"),
) -> None:
    """List themes or modules in the knowledge base.
    
    Displays a formatted table of themes or modules with their properties.
    Use --themes or --modules to specify what to list.
    
    Examples:
        mtm list --themes                    # List all themes
        mtm list --modules                   # List all modules
        mtm list --themes --project Support  # List themes for project
    """
    logger = create_logger("list")
    from rich.table import Table

    from mtm.storage.db import get_db

    db = get_db()

    if themes:
        if project:
            themes_list = builtins.list(db.db["themes"].rows_where("project = ?", [project]))
        else:
            themes_list = builtins.list(db.db["themes"].rows_where("1=1"))

        if themes_list:
            table = Table(title="Themes", show_header=True, header_style="bold magenta")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Project", style="green")
            table.add_column("Top Terms", style="yellow")
            table.add_column("Support Count", justify="right", style="blue")

            for theme in themes_list:
                keywords = theme.get("keywords", "[]")
                if isinstance(keywords, str):
                    try:
                        keywords = json.loads(keywords)
                    except (json.JSONDecodeError, TypeError):
                        keywords = []
                top_terms = ", ".join(keywords[:5]) if keywords else "N/A"

                table.add_row(
                    theme["id"][:8] + "...",
                    theme.get("project", ""),
                    top_terms,
                    str(theme.get("support_count", 0)),
                )
            logger.increment_count("themes_listed", len(themes_list))
            console.print()
            console.print(table)
        else:
            logger.add_error("no_themes", "No themes found", "Run 'analyze' command to generate themes")
            console.print("[yellow]No themes found[/yellow]")

    elif modules:
        if project:
            modules_list = builtins.list(db.db["modules"].rows_where("project = ?", [project]))
        else:
            modules_list = builtins.list(db.db["modules"].rows_where("1=1"))

        if modules_list:
            table = Table(title="Modules", show_header=True, header_style="bold magenta")
            table.add_column("Project", style="green")
            table.add_column("Title", style="cyan")
            table.add_column("Type", style="yellow")
            table.add_column("Version", justify="right", style="blue")
            table.add_column("Themes", style="dim")

            for module in modules_list:
                theme_ids = json.loads(module.get("theme_ids", "[]")) if isinstance(module.get("theme_ids"), str) else module.get("theme_ids", [])
                theme_names = []
                for theme_id in theme_ids[:3]:
                    theme = db.db["themes"].get(theme_id)
                    if theme:
                        theme_names.append(theme.get("name", "")[:20])
                themes_str = ", ".join(theme_names) if theme_names else "None"
                if len(theme_ids) > 3:
                    themes_str += f" (+{len(theme_ids) - 3})"

                roles = set()
                for theme_id in theme_ids:
                    role_mappings = builtins.list(db.db["topic_role_map"].rows_where("topic_id = ?", [theme_id]))
                    for mapping in role_mappings:
                        roles.add(mapping.get("role", ""))
                roles_str = ", ".join(sorted(roles)) if roles else "N/A"

                version_num = module.get("version", 1)
                major = version_num // 10000
                minor = (version_num % 10000) // 100
                patch = version_num % 100
                version_str = f"{major}.{minor}.{patch}"

                table.add_row(
                    module.get("project", ""),
                    module.get("title", "Untitled")[:40],
                    module.get("module_type", "module"),
                    version_str,
                    themes_str,
                )
            logger.increment_count("modules_listed", len(modules_list))
            console.print()
            console.print(table)
        else:
            logger.add_error("no_modules", "No modules found", "Run 'generate' command to create modules")
            console.print("[yellow]No modules found[/yellow]")

    else:
        logger.add_error("no_option", "No list option specified", "Use --themes or --modules to list content")
        console.print("[yellow]Please specify --themes or --modules[/yellow]")
        logger.finish(success=False)
        raise typer.Exit(1)
    logger.finish(success=True)


@app.command()
def export(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name (default: all projects)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory for exports"),
    no_pdf: bool = typer.Option(False, "--no-pdf", help="Skip PDF conversions (pandoc not required)"),
) -> None:
    """Export knowledge base to CSV files and optional PDFs.
    
    Creates a timestamped export directory containing:
    - CSV files: steps.csv, definitions.csv, faqs.csv, decisions.csv, actions.csv, themes.csv
    - Markdown modules
    - PDF versions (if pandoc is available and --pdf is used)
    - README.md with export information
    
    Examples:
        mtm export                           # Export all projects
        mtm export --project Onboarding     # Export specific project
        mtm export --no-pdf                  # Skip PDF conversion
    """
    logger = create_logger("export")
    from mtm.utils.export import create_export

    try:
        zip_path = create_export(project=project, output_base=output, include_pdf=not no_pdf)

        logger.increment_count("exports_created")
        console.print(f"[green]Export created:[/green] {zip_path}")
        console.print(f"[dim]Export directory:[/dim] {zip_path.parent / zip_path.stem.replace('export_', '')}")

        logger.finish(success=True)

    except Exception as e:
        logger.add_error("export_error", f"Error creating export: {str(e)}", "Check database connection and output directory permissions")
        logger.finish(success=False)
        console.print(f"[red]Error creating export: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def init_sample(
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory (default: data/seed/notes)"),
    count: int = typer.Option(20, "--count", "-c", help="Number of notes to generate"),
) -> None:
    """Initialize sample meeting notes for testing.
    
    Generates realistic sample notes across multiple projects (Onboarding,
    Deployment, Support) with varied formats (.md, .txt, .docx, .pdf).
    Notes include front matter metadata and role tags.
    
    Examples:
        mtm init-sample                      # Generate 20 sample notes
        mtm init-sample --count 50          # Generate 50 notes
        mtm init-sample --output data/test/ # Generate to custom directory
    """
    logger = create_logger("init_sample")
    from mtm.utils.sample_notes import generate_sample_notes

    try:
        generated_files = generate_sample_notes(output_dir=output, num_notes=count)

        if generated_files:
            logger.increment_count("notes_generated", len(generated_files))
            console.print(f"[green]Generated {len(generated_files)} note(s):[/green]")
            
            # Group by project
            projects: dict[str, list[Path]] = {}
            for file_path in generated_files:
                project = file_path.parent.name
                if project not in projects:
                    projects[project] = []
                projects[project].append(file_path)

            for project, files in projects.items():
                logger.increment_count(f"project_{project}", len(files))
                console.print(f"  [cyan]{project}:[/cyan] {len(files)} note(s)")
                for file_path in files[:3]:  # Show first 3
                    console.print(f"    [dim]{file_path.name}[/dim]")
                if len(files) > 3:
                    console.print(f"    ... and {len(files) - 3} more")
        else:
            logger.add_error("no_files", "No notes generated", "Check output directory permissions")
            logger.finish(success=False)
            raise typer.Exit(1)

        logger.finish(success=True)

    except Exception as e:
        logger.add_error("generation_error", f"Error generating sample notes: {str(e)}", "Check output directory permissions and dependencies")
        logger.finish(success=False)
        console.print(f"[red]Error generating sample notes: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def reindex(
    source: Optional[str] = typer.Argument(None, help="Source directory (default: current)"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reindexing even if index exists"),
) -> None:
    """Reindex meeting notes database.
    
    Rebuilds database indexes for improved search performance.
    Use --force to rebuild even if indexes already exist.
    
    Examples:
        mtm reindex                         # Reindex current directory
        mtm reindex data/notes/             # Reindex specific directory
        mtm reindex --force                 # Force reindexing
    """
    logger = create_logger("reindex")
    try:
        console.print(f"[green]Reindexing:[/green] {source or '.'}")
        # TODO: Implement reindexing logic
        console.print("[yellow]Reindexing not yet implemented[/yellow]")
        logger.add_error("not_implemented", "Reindexing not yet implemented", "This feature is coming soon")
        logger.finish(success=False)
    except Exception as e:
        logger.add_error("reindex_error", f"Error during reindexing: {str(e)}", "Check database connection and permissions")
        logger.finish(success=False)
        console.print(f"[red]Error during reindexing: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query string"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum number of results"),
) -> None:
    """Search across notes, segments, and extractions.
    
    Performs full-text search across all content in the knowledge base.
    Results are ranked by relevance score and include preview snippets.
    
    Examples:
        mtm search "deployment process"      # Search for phrase
        mtm search deployment --limit 10     # Limit results to 10
        mtm search "onboarding" --project Onboarding  # Search in project
    """
    logger = create_logger("search")
    from rich.table import Table

    from mtm.utils.search import search_all

    try:
        results = search_all(query, project=project, limit=limit)
        logger.increment_count("results_found", len(results))

        if results:
            table = Table(title=f"Search Results ({len(results)} found)", show_header=True, header_style="bold magenta")
            table.add_column("Type", style="cyan", no_wrap=True)
            table.add_column("Score", justify="right", style="green")
            table.add_column("Project", style="yellow")
            table.add_column("Preview", style="dim")
            table.add_column("Source", style="blue")

            for result in results[:limit]:
                preview = result.get("content_preview", result.get("payload", {}).get("title", ""))[:60]
                if len(preview) > 60:
                    preview = preview[:57] + "..."

                source = result.get("source_path") or result.get("note_source_path") or result.get("source_file", "")
                if len(source) > 40:
                    source = "..." + source[-37:]

                table.add_row(
                    result.get("type", "unknown"),
                    str(result.get("score", 0)),
                    result.get("project", ""),
                    preview,
                    source,
                )

            console.print()
            console.print(table)

            # Show top 5 detailed results
            if len(results) > 0:
                console.print()
                console.print("[bold]Top Results:[/bold]")
                for i, result in enumerate(results[:5], 1):
                    console.print(f"\n[cyan]{i}. {result.get('type', 'unknown').upper()}[/cyan] (Score: {result.get('score', 0)})")
                    if result.get("title"):
                        console.print(f"   Title: {result.get('title')}")
                    if result.get("content_preview"):
                        console.print(f"   Preview: {result.get('content_preview')[:200]}")
                    source = result.get("source_path") or result.get("note_source_path") or result.get("source_file", "")
                    if source:
                        console.print(f"   Source: {source}")
        else:
            logger.add_error("no_results", f"No results found for query: {query}", "Try different search terms or check if data has been ingested")
            logger.finish(success=False)
            raise typer.Exit(1)

        logger.finish(success=True)

    except Exception as e:
        logger.add_error("search_error", f"Error searching: {str(e)}", "Check database connection and query syntax")
        logger.finish(success=False)
        console.print(f"[red]Error searching: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def verify(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter checks by project"),
    strict: bool = typer.Option(False, "--strict", help="Strict validation mode (all checks must pass)"),
) -> None:
    """Verify system state and data integrity.
    
    Runs comprehensive checks to ensure the system is functioning correctly:
    - Notes exist and are ingested
    - Segments are created
    - Themes are identified
    - Extractions contain steps and definitions
    - Modules are rendered
    - Versions are recorded
    - Role mappings exist
    - Exports are produced
    
    Examples:
        mtm verify                          # Verify all projects
        mtm verify --project Support        # Verify specific project
        mtm verify --strict                 # Strict mode (all must pass)
    """
    logger = create_logger("verify")
    from rich.table import Table

    from mtm.utils.verify import run_all_checks

    try:
        all_passed, results = run_all_checks(project=project, strict=strict)
        
        # Log check results
        for check_name, passed, message in results:
            if not passed:
                logger.add_error(f"check_{check_name.lower().replace(' ', '_')}", message, f"Run '{check_name.lower()}' related commands to fix this issue")
            logger.increment_count("checks_passed" if passed else "checks_failed")

        # Create results table
        table = Table(title="Verification Results", show_header=True, header_style="bold magenta")
        table.add_column("Check", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center", style="bold")
        table.add_column("Message", style="dim")

        for check_name, passed, message in results:
            status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
            table.add_row(check_name, status, message)

        console.print()
        console.print(table)

        # Summary
        passed_count = sum(1 for _, passed, _ in results if passed)
        total_count = len(results)

        console.print()
        if all_passed:
            console.print(f"[green]All {total_count} check(s) passed[/green]")
        else:
            console.print(f"[red]{total_count - passed_count} of {total_count} check(s) failed[/red]")
            console.print("[yellow]Please review the failed checks above[/yellow]")
            logger.finish(success=False)
            raise typer.Exit(1)

        logger.finish(success=all_passed)

    except typer.Exit:
        raise
    except Exception as e:
        logger.add_error("verification_error", f"Error during verification: {str(e)}", "Check database connection and system state")
        logger.finish(success=False)
        console.print(f"[red]Error during verification: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
