"""Unit tests for preprocessing module."""

from datetime import datetime
from uuid import uuid4

import pytest

from mtm.models import Note
from mtm.preprocess.clean import (
    extract_speakers,
    normalize_unicode,
    preprocess_note,
    redact_text,
    split_sentences,
    strip_boilerplate,
)


class TestNormalizeUnicode:
    """Tests for Unicode normalization."""

    def test_normalize_unicode_basic(self):
        """Test basic Unicode normalization."""
        text = "Café résumé naïve"
        result = normalize_unicode(text)
        assert "é" not in result
        assert "Cafe" in result

    def test_normalize_unicode_special_chars(self):
        """Test normalization of special characters."""
        text = "©®™€£¥"
        result = normalize_unicode(text)
        # Should convert to ASCII equivalents
        assert isinstance(result, str)


class TestStripBoilerplate:
    """Tests for boilerplate removal."""

    def test_strip_meeting_notes_header(self):
        """Test removal of meeting notes header."""
        text = "Meeting Notes\n\nThis is the actual content."
        result = strip_boilerplate(text)
        assert "Meeting Notes" not in result
        assert "actual content" in result

    def test_strip_attendees_line(self):
        """Test removal of attendees line."""
        text = "Attendees: John, Jane\n\nDiscussion about project."
        result = strip_boilerplate(text)
        assert "Attendees" not in result
        assert "Discussion" in result

    def test_strip_horizontal_rules(self):
        """Test removal of horizontal rules."""
        text = "Content before\n---\nContent after"
        result = strip_boilerplate(text)
        assert "---" not in result
        assert "Content before" in result
        assert "Content after" in result

    def test_strip_excessive_whitespace(self):
        """Test removal of excessive whitespace."""
        text = "Line 1\n\n\n\nLine 2"
        result = strip_boilerplate(text)
        # Should have max 2 newlines
        assert "\n\n\n" not in result

    def test_preserve_content(self):
        """Test that actual content is preserved."""
        text = "This is important content that should remain."
        result = strip_boilerplate(text)
        assert "important content" in result


class TestRedactText:
    """Tests for text redaction."""

    def test_redact_email(self):
        """Test email redaction."""
        text = "Contact me at john.doe@example.com for details."
        result = redact_text(text)
        assert "@example.com" not in result
        assert "[EMAIL]" in result

    def test_redact_phone_us_format(self):
        """Test US phone number redaction."""
        text = "Call me at 123-456-7890"
        result = redact_text(text)
        assert "123-456-7890" not in result
        assert "[PHONE]" in result

    def test_redact_phone_parentheses_format(self):
        """Test phone number with parentheses."""
        text = "Phone: (123) 456-7890"
        result = redact_text(text)
        assert "(123)" not in result
        assert "[PHONE]" in result

    def test_redact_multiple_phones(self):
        """Test redaction of multiple phone numbers."""
        text = "Call 123-456-7890 or 987-654-3210"
        result = redact_text(text)
        assert result.count("[PHONE]") == 2

    def test_preserve_non_sensitive(self):
        """Test that non-sensitive text is preserved."""
        text = "This is regular text without sensitive information."
        result = redact_text(text)
        assert "regular text" in result


class TestSplitSentences:
    """Tests for sentence splitting."""

    def test_split_simple_sentences(self):
        """Test splitting simple sentences."""
        text = "This is sentence one. This is sentence two. This is sentence three."
        result = split_sentences(text)
        assert len(result) == 3
        assert "sentence one" in result[0]
        assert "sentence two" in result[1]

    def test_split_with_abbreviations(self):
        """Test splitting with abbreviations."""
        text = "Dr. Smith said hello. Mr. Jones replied."
        result = split_sentences(text)
        # Should handle abbreviations correctly
        assert len(result) >= 2

    def test_filter_short_sentences(self):
        """Test that very short sentences are filtered."""
        text = "Hi. This is a longer sentence that should be kept."
        result = split_sentences(text)
        # Very short sentences should be filtered
        assert all(len(s.strip()) > 3 for s in result)


class TestExtractSpeakers:
    """Tests for speaker extraction."""

    def test_extract_speaker_with_colon(self):
        """Test extraction with colon format."""
        text = "John: This is what John said.\nJane: This is what Jane said."
        result = extract_speakers(text)
        assert len(result) == 2
        assert result[0][0] == "John"
        assert "John said" in result[0][1]
        assert result[1][0] == "Jane"

    def test_extract_speaker_with_dash(self):
        """Test extraction with dash format."""
        text = "John - This is what John said.\nJane - This is what Jane said."
        result = extract_speakers(text)
        assert len(result) == 2
        assert result[0][0] == "John"

    def test_extract_multiline_speaker(self):
        """Test extraction of multi-line speaker text."""
        text = "John: First line.\nSecond line.\nThird line."
        result = extract_speakers(text)
        assert len(result) == 1
        assert result[0][0] == "John"
        assert "Second line" in result[0][1]

    def test_unattributed_text(self):
        """Test handling of unattributed text."""
        text = "This is unattributed text.\nMore unattributed text."
        result = extract_speakers(text)
        # Should create unattributed segments
        assert len(result) > 0


class TestPreprocessNote:
    """Tests for full note preprocessing."""

    def test_preprocess_note_basic(self):
        """Test basic note preprocessing."""
        note = Note(
            id=uuid4(),
            project="test",
            roles=[],
            date=datetime.now(),
            source_file="test.md",
            content="This is sentence one. This is sentence two.",
        )

        segments = preprocess_note(note, persist=False)

        assert len(segments) > 0
        assert all(segment.note_id == note.id for segment in segments)
        assert all(segment.project == note.project for segment in segments)

    def test_preprocess_note_with_speakers(self):
        """Test preprocessing note with speaker attribution."""
        note = Note(
            id=uuid4(),
            project="test",
            roles=[],
            date=datetime.now(),
            source_file="test.md",
            content="John: This is what John said.\nJane: This is what Jane said.",
        )

        segments = preprocess_note(note, persist=False)

        assert len(segments) > 0
        # Check that segments have speaker information
        speaker_segments = [s for s in segments if s.segment_type == "speaker_attributed"]
        assert len(speaker_segments) > 0

    def test_preprocess_note_unicode(self):
        """Test preprocessing with Unicode characters."""
        note = Note(
            id=uuid4(),
            project="test",
            roles=[],
            date=datetime.now(),
            source_file="test.md",
            content="Café discussion about résumé.",
        )

        segments = preprocess_note(note, persist=False)

        # Unicode should be normalized
        all_content = " ".join(s.content for s in segments)
        assert "é" not in all_content or "Cafe" in all_content

    def test_preprocess_note_redaction(self):
        """Test that preprocessing redacts sensitive info."""
        note = Note(
            id=uuid4(),
            project="test",
            roles=[],
            date=datetime.now(),
            source_file="test.md",
            content="Contact john@example.com or call 123-456-7890.",
        )

        segments = preprocess_note(note, persist=False)

        all_content = " ".join(s.content for s in segments)
        assert "@example.com" not in all_content
        assert "123-456-7890" not in all_content

    def test_preprocess_note_boilerplate(self):
        """Test that preprocessing removes boilerplate."""
        note = Note(
            id=uuid4(),
            project="test",
            roles=[],
            date=datetime.now(),
            source_file="test.md",
            content="Meeting Notes\nAttendees: John, Jane\n\nActual content here.",
        )

        segments = preprocess_note(note, persist=False)

        all_content = " ".join(s.content for s in segments)
        assert "Meeting Notes" not in all_content
        assert "Attendees" not in all_content
        assert "Actual content" in all_content

    def test_preprocess_note_segment_order(self):
        """Test that segments maintain correct order."""
        note = Note(
            id=uuid4(),
            project="test",
            roles=[],
            date=datetime.now(),
            source_file="test.md",
            content="First sentence. Second sentence. Third sentence.",
        )

        segments = preprocess_note(note, persist=False)

        # Check ordering
        orders = [s.order for s in segments]
        assert orders == sorted(orders)

    def test_preprocess_note_preserves_metadata(self):
        """Test that preprocessing preserves note metadata."""
        note = Note(
            id=uuid4(),
            project="test_project",
            roles=["admin", "user"],
            date=datetime(2024, 1, 15),
            source_file="test.md",
            content="Test content.",
        )

        segments = preprocess_note(note, persist=False)

        assert all(s.project == "test_project" for s in segments)
        assert all(s.date == datetime(2024, 1, 15) for s in segments)
        assert all(s.source_file == "test.md" for s in segments)

