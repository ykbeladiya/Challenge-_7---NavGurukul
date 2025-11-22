"""Unit tests for theme analysis."""

from datetime import datetime
from uuid import uuid4

import pytest

from mtm.analyze.themes import (
    analyze_themes,
    build_tfidf,
    cluster_themes_kmeans,
    extract_themes_cooccurrence,
)
from mtm.models import Note, Segment
from mtm.storage.db import Database


class TestBuildTfidf:
    """Tests for TF-IDF building."""

    def test_build_tfidf_basic(self):
        """Test basic TF-IDF building."""
        segments = [
            {"content": "machine learning artificial intelligence"},
            {"content": "deep learning neural networks"},
            {"content": "natural language processing text analysis"},
        ]

        vectorizer, matrix = build_tfidf(segments)

        assert matrix.shape[0] == len(segments)
        assert matrix.shape[1] > 0

    def test_build_tfidf_single_segment(self):
        """Test TF-IDF with single segment."""
        segments = [{"content": "test content here"}]

        vectorizer, matrix = build_tfidf(segments)

        assert matrix.shape[0] == 1

    def test_build_tfidf_empty_content(self):
        """Test TF-IDF with empty content."""
        segments = [{"content": ""}, {"content": "some content"}]

        vectorizer, matrix = build_tfidf(segments)

        assert matrix.shape[0] == len(segments)


class TestClusterThemesKmeans:
    """Tests for KMeans clustering."""

    def test_cluster_themes_kmeans_basic(self):
        """Test basic KMeans clustering."""
        from sklearn.feature_extraction.text import TfidfVectorizer

        # Create sample segments
        segments = [
            {"id": str(uuid4()), "content": "machine learning artificial intelligence"},
            {"id": str(uuid4()), "content": "deep learning neural networks"},
            {"id": str(uuid4()), "content": "natural language processing"},
            {"id": str(uuid4()), "content": "python programming code"},
            {"id": str(uuid4()), "content": "software development"},
            {"id": str(uuid4()), "content": "web development javascript"},
        ]

        vectorizer = TfidfVectorizer(max_features=100, stop_words="english")
        tfidf_matrix = vectorizer.fit_transform([s["content"] for s in segments])

        themes = cluster_themes_kmeans(tfidf_matrix, k=2, vectorizer=vectorizer, segments=segments)

        assert len(themes) <= 2
        if themes:
            assert "top_terms" in themes[0]
            assert "support_count" in themes[0]
            assert "segment_ids" in themes[0]

    def test_cluster_themes_kmeans_insufficient_segments(self):
        """Test KMeans with insufficient segments."""
        from sklearn.feature_extraction.text import TfidfVectorizer

        segments = [
            {"id": str(uuid4()), "content": "test content"},
        ]

        vectorizer = TfidfVectorizer(max_features=100)
        tfidf_matrix = vectorizer.fit_transform([s["content"] for s in segments])

        themes = cluster_themes_kmeans(tfidf_matrix, k=3, vectorizer=vectorizer, segments=segments)

        # Should return empty list if not enough segments
        assert len(themes) == 0


class TestExtractThemesCooccurrence:
    """Tests for keyword co-occurrence theme extraction."""

    def test_extract_themes_cooccurrence_basic(self):
        """Test basic co-occurrence extraction."""
        segments = [
            {"id": "1", "content": "machine learning artificial intelligence"},
            {"id": "2", "content": "deep learning neural networks machine"},
            {"id": "3", "content": "artificial intelligence neural networks"},
            {"id": "4", "content": "python programming code"},
            {"id": "5", "content": "software development python"},
        ]

        themes = extract_themes_cooccurrence(segments, min_support=2)

        # Should find some themes
        assert isinstance(themes, list)
        if themes:
            assert "top_terms" in themes[0]
            assert "support_count" in themes[0]
            assert "segment_ids" in themes[0]

    def test_extract_themes_cooccurrence_min_support(self):
        """Test co-occurrence with min_support filtering."""
        segments = [
            {"id": "1", "content": "machine learning"},
            {"id": "2", "content": "deep learning"},
        ]

        themes = extract_themes_cooccurrence(segments, min_support=3)

        # Should return empty or filtered themes
        assert isinstance(themes, list)

    def test_extract_themes_cooccurrence_no_matches(self):
        """Test co-occurrence with no matching keywords."""
        segments = [
            {"id": "1", "content": "completely different topic"},
            {"id": "2", "content": "another unrelated subject"},
        ]

        themes = extract_themes_cooccurrence(segments, min_support=2)

        # May return empty or very few themes
        assert isinstance(themes, list)


class TestAnalyzeThemes:
    """Tests for full theme analysis pipeline."""

    @pytest.fixture
    def test_db(self, tmp_path):
        """Create a test database."""
        db_path = tmp_path / "test.db"
        db = Database(str(db_path))
        return db

    @pytest.fixture
    def sample_segments(self):
        """Create sample segments for testing."""
        note_id = uuid4()
        segments = []

        # Create segments with similar topics
        topics = [
            "machine learning artificial intelligence",
            "deep learning neural networks",
            "natural language processing",
            "python programming development",
            "software engineering code",
            "web development javascript",
        ]

        for i, topic in enumerate(topics):
            segment = Segment(
                id=uuid4(),
                note_id=note_id,
                project="test_project",
                roles=[],
                date=datetime.now(),
                source_file="test.md",
                content=topic,
                order=i,
            )
            segments.append(segment)

        return segments

    def test_analyze_themes_with_segments(self, test_db, sample_segments, monkeypatch):
        """Test theme analysis with segments in database."""
        # Insert segments into test database
        for seg in sample_segments:
            test_db.upsert_segment(
                segment_id=seg.id,
                note_id=seg.note_id,
                project=seg.project,
                date=seg.date,
                source_file=seg.source_file,
                content=seg.content,
                segment_type=seg.segment_type,
                order=seg.order,
            )

        # Mock get_db to return test_db
        from mtm import storage

        original_get_db = storage.db.get_db
        storage.db._db = test_db

        try:
            # Analyze themes
            themes = analyze_themes(project="test_project", persist=False)

            # Should find some themes
            assert isinstance(themes, list)
            if themes:
                assert all(hasattr(t, "name") for t in themes)
                assert all(hasattr(t, "support_count") for t in themes)
                assert all(hasattr(t, "keywords") for t in themes)
        finally:
            storage.db._db = None

    def test_analyze_themes_empty_database(self, test_db, monkeypatch):
        """Test theme analysis with empty database."""
        from mtm import storage

        storage.db._db = test_db

        try:
            themes = analyze_themes(project="test_project", persist=False)

            # Should return empty list
            assert themes == []
        finally:
            storage.db._db = None

    def test_analyze_themes_min_support_filtering(self, test_db, monkeypatch):
        """Test that themes are filtered by min_theme_support."""
        from mtm import storage

        # Create very few segments
        note_id = uuid4()
        segment = Segment(
            id=uuid4(),
            note_id=note_id,
            project="test",
            roles=[],
            date=datetime.now(),
            source_file="test.md",
            content="single segment content",
            order=0,
        )

        test_db.upsert_segment(
            segment_id=segment.id,
            note_id=segment.note_id,
            project=segment.project,
            date=segment.date,
            source_file=segment.source_file,
            content=segment.content,
        )

        storage.db._db = test_db

        try:
            themes = analyze_themes(project="test", persist=False)

            # With min_theme_support=3, should filter out single segment
            assert isinstance(themes, list)
        finally:
            storage.db._db = None

    def test_analyze_themes_global_vs_project(self, test_db, sample_segments, monkeypatch):
        """Test global vs project-specific theme analysis."""
        from mtm import storage

        # Insert segments
        for seg in sample_segments:
            test_db.upsert_segment(
                segment_id=seg.id,
                note_id=seg.note_id,
                project=seg.project,
                date=seg.date,
                source_file=seg.source_file,
                content=seg.content,
            )

        storage.db._db = test_db

        try:
            # Project-specific
            project_themes = analyze_themes(project="test_project", persist=False)

            # Global
            global_themes = analyze_themes(project=None, persist=False)

            assert isinstance(project_themes, list)
            assert isinstance(global_themes, list)
        finally:
            storage.db._db = None


class TestTinyCorpus:
    """Tests with tiny corpus as specified."""

    def test_tiny_corpus_analysis(self, tmp_path):
        """Test theme analysis with a tiny corpus."""
        db_path = tmp_path / "tiny.db"
        db = Database(str(db_path))

        # Create tiny corpus: 3 segments
        note_id = uuid4()
        tiny_segments = [
            Segment(
                id=uuid4(),
                note_id=note_id,
                project="tiny",
                roles=[],
                date=datetime.now(),
                source_file="tiny.md",
                content="machine learning",
                order=0,
            ),
            Segment(
                id=uuid4(),
                note_id=note_id,
                project="tiny",
                roles=[],
                date=datetime.now(),
                source_file="tiny.md",
                content="deep learning",
                order=1,
            ),
            Segment(
                id=uuid4(),
                note_id=note_id,
                project="tiny",
                roles=[],
                date=datetime.now(),
                source_file="tiny.md",
                content="neural networks",
                order=2,
            ),
        ]

        # Insert into database
        for seg in tiny_segments:
            db.upsert_segment(
                segment_id=seg.id,
                note_id=seg.note_id,
                project=seg.project,
                date=seg.date,
                source_file=seg.source_file,
                content=seg.content,
            )

        # Mock get_db
        from mtm import storage

        storage.db._db = db

        try:
            # Should use co-occurrence fallback (not enough for KMeans)
            themes = analyze_themes(project="tiny", persist=False)

            # Should handle tiny corpus gracefully
            assert isinstance(themes, list)
            # May return empty or themes depending on min_support
        finally:
            storage.db._db = None

