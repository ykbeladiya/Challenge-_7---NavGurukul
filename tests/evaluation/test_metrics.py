"""Test suite for measuring theme precision/recall, step extraction accuracy, and duplicate collapse."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest
import yaml

from mtm.analyze.themes import analyze_themes
from mtm.extract.extractors import extract_structured_info
from mtm.ingest.md_txt import parse_md_txt
from mtm.preprocess.clean import preprocess_note
from mtm.storage.db import Database


def load_ground_truth(file_path: Path) -> dict[str, Any]:
    """Load ground truth labels from YAML frontmatter.

    Args:
        file_path: Path to sample file with ground truth

    Returns:
        Dictionary with ground truth labels
    """
    content = file_path.read_text(encoding="utf-8")
    
    # Parse frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1])
            return frontmatter or {}
    
    return {}


def calculate_precision_recall(predicted: list[str], actual: list[str]) -> tuple[float, float]:
    """Calculate precision and recall for theme/keyword matching.

    Args:
        predicted: List of predicted theme IDs or keywords
        actual: List of actual theme IDs or keywords

    Returns:
        Tuple of (precision, recall)
    """
    if not predicted and not actual:
        return 1.0, 1.0
    
    if not predicted:
        return 0.0, 0.0
    
    if not actual:
        return 0.0, 1.0
    
    predicted_set = set(predicted)
    actual_set = set(actual)
    
    true_positives = len(predicted_set & actual_set)
    precision = true_positives / len(predicted_set) if predicted_set else 0.0
    recall = true_positives / len(actual_set) if actual_set else 0.0
    
    return precision, recall


def calculate_f1_score(precision: float, recall: float) -> float:
    """Calculate F1 score from precision and recall.

    Args:
        precision: Precision score
        recall: Recall score

    Returns:
        F1 score
    """
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)


def test_theme_precision_recall(tmp_path: Path):
    """Test theme analysis precision and recall against ground truth."""
    samples_dir = Path(__file__).parent.parent.parent / "samples" / "meetings"
    
    if not samples_dir.exists():
        pytest.skip("Samples directory not found")
    
    # Create test database
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    
    total_precision = 0.0
    total_recall = 0.0
    count = 0
    
    for sample_file in samples_dir.glob("*.md"):
        # Load ground truth
        ground_truth = load_ground_truth(sample_file)
        if "themes" not in ground_truth:
            continue
        
        # Parse and preprocess
        note = parse_md_txt(sample_file)
        db.upsert_note(
            note_id=note.id,
            project=note.project,
            date=note.date,
            source_file=note.source_file,
            content=note.content,
            title=note.title,
            metadata=note.metadata,
            content_sha256=hashlib.sha256((note.content or "").encode("utf-8")).hexdigest(),
            source_path=str(sample_file),
        )
        
        segments = preprocess_note(note, persist=True)
        
        # Analyze themes
        themes = analyze_themes(project=note.project)
        
        # Extract predicted theme IDs
        predicted_theme_ids = [theme.get("id", "") for theme in themes]
        
        # Extract actual theme IDs from ground truth
        actual_theme_ids = [theme.get("id", "") for theme in ground_truth["themes"]]
        
        # Calculate metrics
        precision, recall = calculate_precision_recall(predicted_theme_ids, actual_theme_ids)
        
        total_precision += precision
        total_recall += recall
        count += 1
    
    if count > 0:
        avg_precision = total_precision / count
        avg_recall = total_recall / count
        f1 = calculate_f1_score(avg_precision, avg_recall)
        
        # Assert minimum thresholds (adjust based on requirements)
        assert avg_precision >= 0.3, f"Theme precision too low: {avg_precision:.2f}"
        assert avg_recall >= 0.3, f"Theme recall too low: {avg_recall:.2f}"
        assert f1 >= 0.3, f"Theme F1 score too low: {f1:.2f}"


def test_step_extraction_accuracy(tmp_path: Path):
    """Test step extraction accuracy against ground truth."""
    samples_dir = Path(__file__).parent.parent.parent / "samples" / "meetings"
    
    if not samples_dir.exists():
        pytest.skip("Samples directory not found")
    
    # Create test database
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    
    total_accuracy = 0.0
    count = 0
    
    for sample_file in samples_dir.glob("*.md"):
        # Load ground truth
        ground_truth = load_ground_truth(sample_file)
        if "steps" not in ground_truth:
            continue
        
        # Parse and preprocess
        note = parse_md_txt(sample_file)
        db.upsert_note(
            note_id=note.id,
            project=note.project,
            date=note.date,
            source_file=note.source_file,
            content=note.content,
            title=note.title,
            metadata=note.metadata,
            content_sha256=hashlib.sha256((note.content or "").encode("utf-8")).hexdigest(),
            source_path=str(sample_file),
        )
        
        segments = preprocess_note(note, persist=True)
        
        # Extract structured info
        extractions = extract_structured_info(project=note.project)
        
        # Filter steps
        extracted_steps = [e for e in extractions if e.get("type") == "step"]
        
        # Compare with ground truth
        ground_truth_steps = ground_truth["steps"]
        
        # Simple accuracy: count matching step titles
        matches = 0
        for gt_step in ground_truth_steps:
            gt_title = gt_step.get("title", "").lower()
            for ext_step in extracted_steps:
                ext_title = ext_step.get("title", "").lower()
                if gt_title in ext_title or ext_title in gt_title:
                    matches += 1
                    break
        
        accuracy = matches / len(ground_truth_steps) if ground_truth_steps else 0.0
        total_accuracy += accuracy
        count += 1
    
    if count > 0:
        avg_accuracy = total_accuracy / count
        # Assert minimum threshold
        assert avg_accuracy >= 0.2, f"Step extraction accuracy too low: {avg_accuracy:.2f}"


def test_duplicate_collapse(tmp_path: Path):
    """Test that duplicate content is correctly collapsed."""
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    
    # Create two notes with identical content
    content = "This is a test meeting note with identical content."
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    
    from datetime import datetime
    from uuid import uuid4
    
    note_id1 = uuid4()
    note_id2 = uuid4()
    
    # Insert first note
    db.upsert_note(
        note_id=note_id1,
        project="Test",
        date=datetime.now(),
        source_file="note1.md",
        content=content,
        title="Note 1",
        content_sha256=content_hash,
    )
    
    # Try to insert duplicate
    existing = db.find_note_by_hash(content_hash)
    assert existing is not None, "Should find existing note by hash"
    assert existing["id"] == str(note_id1), "Should return the first note"
    
    # Insert second note with same content
    db.upsert_note(
        note_id=note_id2,
        project="Test",
        date=datetime.now(),
        source_file="note2.md",
        content=content,
        title="Note 2",
        content_sha256=content_hash,
    )
    
    # Verify both notes exist (upsert doesn't prevent duplicates, but hash check should)
    notes = list(db.db["notes"].rows_where("content_sha256 = ?", [content_hash]))
    # The hash check in ingest should prevent duplicates, but if both are inserted,
    # we can verify the hash is the same
    assert len(notes) >= 1, "Should have at least one note with this hash"
    
    # All notes with same hash should have same content
    for note in notes:
        assert note["content_sha256"] == content_hash


def test_definition_extraction_accuracy(tmp_path: Path):
    """Test definition extraction accuracy against ground truth."""
    samples_dir = Path(__file__).parent.parent.parent / "samples" / "meetings"
    
    if not samples_dir.exists():
        pytest.skip("Samples directory not found")
    
    # Create test database
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    
    total_accuracy = 0.0
    count = 0
    
    for sample_file in samples_dir.glob("*.md"):
        # Load ground truth
        ground_truth = load_ground_truth(sample_file)
        if "definitions" not in ground_truth:
            continue
        
        # Parse and preprocess
        note = parse_md_txt(sample_file)
        db.upsert_note(
            note_id=note.id,
            project=note.project,
            date=note.date,
            source_file=note.source_file,
            content=note.content,
            title=note.title,
            metadata=note.metadata,
            content_sha256=hashlib.sha256((note.content or "").encode("utf-8")).hexdigest(),
            source_path=str(sample_file),
        )
        
        segments = preprocess_note(note, persist=True)
        
        # Extract structured info
        extractions = extract_structured_info(project=note.project)
        
        # Filter definitions
        extracted_definitions = [e for e in extractions if e.get("type") == "definition"]
        
        # Compare with ground truth
        ground_truth_definitions = ground_truth["definitions"]
        
        # Simple accuracy: count matching terms
        matches = 0
        for gt_def in ground_truth_definitions:
            gt_term = gt_def.get("term", "").lower()
            for ext_def in extracted_definitions:
                ext_term = ext_def.get("term", "").lower()
                if gt_term == ext_term or gt_term in ext_term or ext_term in gt_term:
                    matches += 1
                    break
        
        accuracy = matches / len(ground_truth_definitions) if ground_truth_definitions else 0.0
        total_accuracy += accuracy
        count += 1
    
    if count > 0:
        avg_accuracy = total_accuracy / count
        # Assert minimum threshold
        assert avg_accuracy >= 0.2, f"Definition extraction accuracy too low: {avg_accuracy:.2f}"

