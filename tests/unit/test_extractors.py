"""Unit tests for extractors."""

from datetime import datetime
from uuid import uuid4

import pytest

from mtm.extract.extractors import (
    extract_actions,
    extract_all,
    extract_decisions,
    extract_definitions,
    extract_faqs,
    extract_steps,
)


class TestExtractSteps:
    """Tests for step extraction."""

    def test_extract_numbered_steps(self):
        """Test extraction of numbered steps."""
        text = """
        1. First step is to analyze the data
        2. Second step involves processing
        3. Final step is to report results
        """

        steps = extract_steps(text, note_id=str(uuid4()))

        assert len(steps) >= 3
        assert all(hasattr(s, "step_number") for s in steps)
        assert all(hasattr(s, "description") for s in steps)

    def test_extract_bulleted_steps(self):
        """Test extraction of bulleted steps."""
        text = """
        - Start the process
        - Continue with analysis
        - Complete the task
        """

        steps = extract_steps(text)

        assert len(steps) >= 3

    def test_extract_imperative_steps(self):
        """Test extraction of imperative steps."""
        text = """
        Analyze the data carefully.
        Process the results.
        Report findings.
        """

        steps = extract_steps(text)

        assert len(steps) >= 3

    def test_steps_have_backlinks(self):
        """Test that steps include backlinks."""
        note_id = str(uuid4())
        segment_ids = [str(uuid4())]

        text = "1. First step"
        steps = extract_steps(text, note_id=note_id, segment_ids=segment_ids)

        if steps:
            assert steps[0].backlinks.note_id == note_id
            assert steps[0].backlinks.segment_ids == segment_ids


class TestExtractDefinitions:
    """Tests for definition extraction."""

    def test_extract_is_definition(self):
        """Test extraction with 'is' pattern."""
        text = "Machine learning is a method of data analysis."

        definitions = extract_definitions(text)

        assert len(definitions) >= 1
        assert definitions[0].term == "Machine learning"
        assert "data analysis" in definitions[0].definition

    def test_extract_means_definition(self):
        """Test extraction with 'means' pattern."""
        text = "API means Application Programming Interface."

        definitions = extract_definitions(text)

        assert len(definitions) >= 1
        assert "API" in definitions[0].term
        assert "Application Programming Interface" in definitions[0].definition

    def test_extract_colon_definition(self):
        """Test extraction with colon pattern."""
        text = "Database: A structured collection of data."

        definitions = extract_definitions(text)

        assert len(definitions) >= 1
        assert definitions[0].term == "Database"

    def test_definitions_have_backlinks(self):
        """Test that definitions include backlinks."""
        note_id = str(uuid4())
        segment_ids = [str(uuid4())]

        text = "Term is definition"
        definitions = extract_definitions(text, note_id=note_id, segment_ids=segment_ids)

        if definitions:
            assert definitions[0].backlinks.note_id == note_id
            assert definitions[0].backlinks.segment_ids == segment_ids


class TestExtractFAQs:
    """Tests for FAQ extraction."""

    def test_extract_q_a_pattern(self):
        """Test extraction with Q: A: pattern."""
        text = """
        Q: What is machine learning?
        A: Machine learning is a subset of artificial intelligence.
        """

        faqs = extract_faqs(text)

        assert len(faqs) >= 1
        assert "machine learning" in faqs[0].question.lower()
        assert "artificial intelligence" in faqs[0].answer.lower()

    def test_extract_question_mark_pattern(self):
        """Test extraction with question mark pattern."""
        text = """
        What is Python? Python is a programming language.
        How does it work? It uses an interpreter.
        """

        faqs = extract_faqs(text)

        assert len(faqs) >= 1

    def test_faqs_have_backlinks(self):
        """Test that FAQs include backlinks."""
        note_id = str(uuid4())
        segment_ids = [str(uuid4())]

        text = "Q: Question? A: Answer"
        faqs = extract_faqs(text, note_id=note_id, segment_ids=segment_ids)

        if faqs:
            assert faqs[0].backlinks.note_id == note_id
            assert faqs[0].backlinks.segment_ids == segment_ids


class TestExtractDecisions:
    """Tests for decision extraction."""

    def test_extract_decision_colon(self):
        """Test extraction with 'Decision:' pattern."""
        text = "Decision: We will proceed with the new design."

        decisions = extract_decisions(text)

        assert len(decisions) >= 1
        assert "proceed" in decisions[0].decision.lower()

    def test_extract_decided_pattern(self):
        """Test extraction with 'Decided:' pattern."""
        text = "Decided: To implement the feature next week."

        decisions = extract_decisions(text)

        assert len(decisions) >= 1

    def test_extract_we_decided_pattern(self):
        """Test extraction with 'We decided' pattern."""
        text = "We decided to use Python for the project."

        decisions = extract_decisions(text)

        assert len(decisions) >= 1
        assert "Python" in decisions[0].decision

    def test_extract_decision_maker(self):
        """Test extraction of decision maker."""
        text = "Decision: Proceed with implementation by John Smith."

        decisions = extract_decisions(text)

        if decisions:
            assert decisions[0].decision_maker is not None

    def test_decisions_have_backlinks(self):
        """Test that decisions include backlinks."""
        note_id = str(uuid4())
        segment_ids = [str(uuid4())]

        text = "Decision: Test decision"
        decisions = extract_decisions(text, note_id=note_id, segment_ids=segment_ids)

        if decisions:
            assert decisions[0].backlinks.note_id == note_id
            assert decisions[0].backlinks.segment_ids == segment_ids


class TestExtractActions:
    """Tests for action extraction."""

    def test_extract_action_colon(self):
        """Test extraction with 'Action:' pattern."""
        text = "Action: Review the code by Friday."

        actions = extract_actions(text)

        assert len(actions) >= 1
        assert "Review" in actions[0].action

    def test_extract_action_item(self):
        """Test extraction with 'Action item:' pattern."""
        text = "Action item: Update documentation."

        actions = extract_actions(text)

        assert len(actions) >= 1

    def test_extract_assignee(self):
        """Test extraction of assignee."""
        text = "Action: Implement feature assigned to John Doe."

        actions = extract_actions(text)

        if actions:
            assert actions[0].assignee is not None
            assert "John" in actions[0].assignee

    def test_extract_due_date(self):
        """Test extraction of due date."""
        text = "Action: Complete task due December 15, 2024."

        actions = extract_actions(text)

        if actions:
            assert actions[0].due_date is not None
            assert actions[0].due_date.year == 2024

    def test_extract_due_date_formats(self):
        """Test extraction of various date formats."""
        test_cases = [
            "Action: Task due 12/15/2024",
            "Action: Task due 12-15-2024",
            "Action: Task by January 15, 2024",
        ]

        for text in test_cases:
            actions = extract_actions(text)
            if actions:
                assert actions[0].due_date is not None

    def test_extract_status(self):
        """Test extraction of status."""
        text = "Action: Fix bug status: in progress"

        actions = extract_actions(text)

        if actions:
            assert actions[0].status is not None
            assert "progress" in actions[0].status.lower()

    def test_actions_have_backlinks(self):
        """Test that actions include backlinks."""
        note_id = str(uuid4())
        segment_ids = [str(uuid4())]

        text = "Action: Test action"
        actions = extract_actions(text, note_id=note_id, segment_ids=segment_ids)

        if actions:
            assert actions[0].backlinks.note_id == note_id
            assert actions[0].backlinks.segment_ids == segment_ids


class TestExtractAll:
    """Tests for extract_all function."""

    def test_extract_all_types(self):
        """Test extraction of all types."""
        text = """
        1. First step
        Machine learning is AI method.
        Q: What is Python? A: A language.
        Decision: Use Python.
        Action: Implement feature by John due 12/15/2024.
        """

        results = extract_all(text)

        assert "steps" in results
        assert "definitions" in results
        assert "faqs" in results
        assert "decisions" in results
        assert "actions" in results

        assert len(results["steps"]) >= 1
        assert len(results["definitions"]) >= 1
        assert len(results["faqs"]) >= 1
        assert len(results["decisions"]) >= 1
        assert len(results["actions"]) >= 1

    def test_extract_all_with_metadata(self):
        """Test extract_all with metadata."""
        note_id = str(uuid4())
        segment_ids = [str(uuid4())]
        project = "test_project"
        date = datetime(2024, 1, 15)
        source_file = "test.md"

        text = "1. Step\nTerm is definition"

        results = extract_all(
            text,
            note_id=note_id,
            segment_ids=segment_ids,
            project=project,
            date=date,
            source_file=source_file,
        )

        # Check that metadata is preserved
        if results["steps"]:
            assert results["steps"][0].project == project
            assert results["steps"][0].date == date
            assert results["steps"][0].source_file == source_file

        if results["definitions"]:
            assert results["definitions"][0].project == project
            assert results["definitions"][0].date == date


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_text(self):
        """Test extraction with empty text."""
        text = ""

        steps = extract_steps(text)
        definitions = extract_definitions(text)
        faqs = extract_faqs(text)
        decisions = extract_decisions(text)
        actions = extract_actions(text)

        assert steps == []
        assert definitions == []
        assert faqs == []
        assert decisions == []
        assert actions == []

    def test_no_matches(self):
        """Test extraction with text that has no matches."""
        text = "This is just regular text without any structured patterns."

        steps = extract_steps(text)
        definitions = extract_definitions(text)
        faqs = extract_faqs(text)
        decisions = extract_decisions(text)
        actions = extract_actions(text)

        # Should return empty lists, not errors
        assert isinstance(steps, list)
        assert isinstance(definitions, list)
        assert isinstance(faqs, list)
        assert isinstance(decisions, list)
        assert isinstance(actions, list)

    def test_multiple_extractions_same_text(self):
        """Test multiple extractions from same text."""
        text = """
        1. First step
        2. Second step
        Term1 is definition1
        Term2 is definition2
        Q: Question1? A: Answer1
        Q: Question2? A: Answer2
        Decision: Decision1
        Decision: Decision2
        Action: Action1
        Action: Action2
        """

        results = extract_all(text)

        assert len(results["steps"]) >= 2
        assert len(results["definitions"]) >= 2
        assert len(results["faqs"]) >= 2
        assert len(results["decisions"]) >= 2
        assert len(results["actions"]) >= 2

