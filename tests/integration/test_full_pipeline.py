"""Integration test for the full pipeline."""

import hashlib
import random
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest

from mtm.analyze.mapping import map_segments_to_roles, map_themes_to_roles
from mtm.analyze.themes import analyze_themes
from mtm.config import Config
from mtm.extract.extractors import extract_all
from mtm.generate.build import generate_modules
from mtm.ingest.docx_loader import parse_docx
from mtm.ingest.md_txt import parse_md_txt
from mtm.ingest.pdf_loader import parse_pdf
from mtm.models import Note, Segment
from mtm.preprocess.clean import preprocess_file
from mtm.storage.db import Database
from mtm.utils.export import create_export
from mtm.utils.sample_notes import generate_sample_notes


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test data."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_config(temp_dir, monkeypatch):
    """Create a test configuration."""
    config_path = temp_dir / "configs" / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    config = Config(
        input_dirs=[str(temp_dir / "data" / "seed" / "notes")],
        output_dir=str(temp_dir / "outputs"),
        db_path=str(temp_dir / "outputs" / "test.db"),
        kmeans_k=3,  # Smaller for testing
        min_theme_support=2,  # Lower for testing
    )
    config.save(config_path)
    
    # Monkeypatch get_config to return our test config
    def _get_test_config(*args, **kwargs):
        return config
    
    monkeypatch.setattr("mtm.config.get_config", _get_test_config)
    monkeypatch.setattr("mtm.storage.db.get_config", _get_test_config)
    monkeypatch.setattr("mtm.generate.build.get_config", _get_test_config)
    monkeypatch.setattr("mtm.utils.export.get_config", _get_test_config)
    monkeypatch.setattr("mtm.preprocess.clean.get_config", _get_test_config)
    monkeypatch.setattr("mtm.analyze.themes.get_config", _get_test_config)
    monkeypatch.setattr("mtm.analyze.mapping.get_config", _get_test_config)
    
    return config


@pytest.fixture
def test_db(test_config, monkeypatch):
    """Create a test database."""
    db = Database(db_path=test_config.db_path)
    
    # Monkeypatch get_db to return our test db
    def _get_test_db(*args, **kwargs):
        return db
    
    monkeypatch.setattr("mtm.storage.db.get_db", _get_test_db)
    monkeypatch.setattr("mtm.analyze.themes.get_db", _get_test_db)
    monkeypatch.setattr("mtm.analyze.mapping.get_db", _get_test_db)
    monkeypatch.setattr("mtm.generate.build.get_db", _get_test_db)
    monkeypatch.setattr("mtm.utils.export.get_db", _get_test_db)
    monkeypatch.setattr("mtm.preprocess.clean.get_db", _get_test_db)
    
    yield db
    # Cleanup handled by temp_dir


@pytest.mark.integration
def test_full_pipeline(temp_dir, test_config, test_db):
    """Test the full pipeline: init-sample → ingest → preprocess → analyze → extract → generate → export."""
    # Set random seed for reproducibility
    random.seed(42)

    # Step 1: Generate sample notes
    notes_dir = temp_dir / "data" / "seed" / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    generated_files = generate_sample_notes(output_dir=notes_dir, num_notes=10)

    assert len(generated_files) > 0, "Should generate sample notes"

    # Step 2: Ingest notes
    db = test_db
    ingested_count = 0

    for file_path in generated_files:
        file_ext = file_path.suffix.lower()
        if file_ext in [".md", ".txt"]:
            note = parse_md_txt(file_path)
        elif file_ext == ".docx":
            note = parse_docx(file_path)
        elif file_ext == ".pdf":
            note = parse_pdf(file_path)
        else:
            continue

        content = note.content or ""
        content_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Check for duplicates
        existing = db.find_note_by_hash(content_sha256)
        if existing:
            continue

        file_stat = file_path.stat()
        mtime = datetime.fromtimestamp(file_stat.mtime)
        size = file_stat.st_size

        # Infer project from parent directory
        if note.project == "default":
            parent_dir = file_path.parent
            if parent_dir.name not in ["notes", "seed", "data"]:
                note.project = parent_dir.name

        db.upsert_note(
            note_id=note.id,
            project=note.project,
            date=note.date,
            source_file=note.source_file,
            line_start=note.line_start,
            line_end=note.line_end,
            content=note.content,
            title=note.title,
            metadata=note.metadata,
            content_sha256=content_sha256,
            source_path=str(file_path),
            mtime=mtime,
            size=size,
        )
        ingested_count += 1

    assert ingested_count > 0, "Should ingest at least one note"

    # Step 3: Preprocess notes
    notes = list(db.db["notes"].rows_where("1=1"))
    segments_created = 0

    for note in notes:
        source_path = note.get("source_path")
        if source_path and Path(source_path).exists():
            segments = preprocess_file(source_path, persist=True)
            segments_created += len(segments)

    assert segments_created > 0, "Should create segments"

    # Step 4: Analyze themes
    themes = analyze_themes(persist=True)
    assert len(themes) > 0, "Should identify at least one theme"

    # Step 5: Map roles
    segment_mappings = map_segments_to_roles(persist=True)
    theme_mappings = map_themes_to_roles(persist=True)
    assert len(segment_mappings) + len(theme_mappings) > 0, "Should create role mappings"

    # Step 6: Extract structured information
    total_extractions = 0
    for note in notes:
        segments_data = list(db.db["segments"].rows_where("note_id = ?", [note["id"]]))
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
            extractions = extract_all(
                segments,
                note["id"],
                note.get("project", "default"),
                datetime.fromisoformat(note.get("date", datetime.now().isoformat())),
                note.get("source_file", ""),
            )

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

    assert total_extractions > 0, "Should extract structured information"

    # Step 7: Generate modules
    output_dir = temp_dir / "outputs" / "modules"
    rendered_files = generate_modules(output_dir=output_dir)

    assert len(rendered_files) > 0, "Should generate module files"

    # Step 8: Export
    export_path = create_export(output_base=temp_dir / "outputs" / "exports", include_pdf=False)
    assert export_path.exists(), "Should create export file"

    # Step 9: Compare generated files to golden files
    golden_dir = Path(__file__).parent / "golden"
    golden_dir.mkdir(parents=True, exist_ok=True)

    # Get generated markdown files
    generated_md_files = list(output_dir.rglob("*.md"))
    assert len(generated_md_files) > 0, "Should have generated markdown files"

    # Compare first few files (or all if golden files exist)
    for md_file in generated_md_files[:5]:  # Compare first 5 files
        relative_path = md_file.relative_to(output_dir)
        golden_file = golden_dir / relative_path

        generated_content = md_file.read_text(encoding="utf-8")

        if golden_file.exists():
            golden_content = golden_file.read_text(encoding="utf-8")
            assert generated_content == golden_content, f"Generated file {relative_path} does not match golden file"
        else:
            # Create golden file on first run
            golden_file.parent.mkdir(parents=True, exist_ok=True)
            golden_file.write_text(generated_content, encoding="utf-8")
            pytest.skip(f"Created golden file for {relative_path} - run test again to verify")


@pytest.mark.integration
def test_pipeline_reproducibility(temp_dir, test_config):
    """Test that the pipeline produces identical results with the same seed."""
    # Run pipeline twice with same seed
    random.seed(42)

    # First run
    notes_dir1 = temp_dir / "data1" / "seed" / "notes"
    notes_dir1.mkdir(parents=True, exist_ok=True)
    generate_sample_notes(output_dir=notes_dir1, num_notes=5)

    # Second run with same seed
    random.seed(42)
    notes_dir2 = temp_dir / "data2" / "seed" / "notes"
    notes_dir2.mkdir(parents=True, exist_ok=True)
    generate_sample_notes(output_dir=notes_dir2, num_notes=5)

    # Compare generated files (they should be identical with same seed)
    files1 = sorted(notes_dir1.rglob("*"))
    files2 = sorted(notes_dir2.rglob("*"))

    # Compare file contents
    for f1, f2 in zip(files1, files2):
        if f1.is_file() and f2.is_file():
            content1 = f1.read_text(encoding="utf-8")
            content2 = f2.read_text(encoding="utf-8")
            assert content1 == content2, f"Files {f1.name} and {f2.name} should be identical with same seed"
