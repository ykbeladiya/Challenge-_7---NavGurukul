"""Extractors for structured information from meeting notes."""

import re
from datetime import datetime
from typing import Optional
from uuid import uuid4

from dateutil import parser as date_parser

from mtm.models import Action, Backlinks, Decision, Definition, FAQ, Step


def extract_steps(
    text: str,
    note_id: Optional[str] = None,
    segment_ids: Optional[list[str]] = None,
    project: str = "default",
    date: Optional[datetime] = None,
    source_file: str = "",
) -> list[Step]:
    """Extract steps from numbered or bulleted imperatives.

    Args:
        text: Text to extract from
        note_id: Note ID for backlinks
        segment_ids: Segment IDs for backlinks
        project: Project name
        date: Date for the step
        source_file: Source file path

    Returns:
        List of Step objects
    """
    if not date:
        date = datetime.now()

    steps: list[Step] = []

    # Pattern for numbered steps: "1. Do something" or "1) Do something"
    numbered_pattern = re.compile(
        r"^\s*(?:\d+[.)]|\d+\.)\s+(.+?)(?=\n\s*(?:\d+[.)]|\d+\.)|\n\n|$)",
        re.MULTILINE | re.DOTALL,
    )

    # Pattern for bulleted steps: "- Do something" or "* Do something"
    bulleted_pattern = re.compile(
        r"^\s*[-*•]\s+(.+?)(?=\n\s*[-*•]|\n\n|$)",
        re.MULTILINE | re.DOTALL,
    )

    # Pattern for imperative verbs at start
    imperative_pattern = re.compile(
        r"^\s*(?:[A-Z][a-z]+)\s+(.+?)(?=\n|$)",
        re.MULTILINE,
    )

    step_number = 1

    # Extract numbered steps
    for match in numbered_pattern.finditer(text):
        content = match.group(1).strip()
        if len(content) > 5:  # Filter very short matches
            # Check if it's imperative (starts with verb)
            if re.match(r"^[A-Z][a-z]+\s", content):
                step = Step(
                    id=uuid4(),
                    project=project,
                    step_number=step_number,
                    title=content[:100] if len(content) > 100 else content,
                    description=content,
                    date=date,
                    source_file=source_file,
                    backlinks=Backlinks(note_id=note_id, segment_ids=segment_ids or []),
                )
                steps.append(step)
                step_number += 1

    # Extract bulleted steps
    for match in bulleted_pattern.finditer(text):
        content = match.group(1).strip()
        if len(content) > 5 and content not in [s.description for s in steps]:
            if re.match(r"^[A-Z][a-z]+\s", content):
                step = Step(
                    id=uuid4(),
                    project=project,
                    step_number=step_number,
                    title=content[:100] if len(content) > 100 else content,
                    description=content,
                    date=date,
                    source_file=source_file,
                    backlinks=Backlinks(note_id=note_id, segment_ids=segment_ids or []),
                )
                steps.append(step)
                step_number += 1

    return steps


def extract_definitions(
    text: str,
    note_id: Optional[str] = None,
    segment_ids: Optional[list[str]] = None,
    project: str = "default",
    date: Optional[datetime] = None,
    source_file: str = "",
) -> list[Definition]:
    """Extract definitions using "X is/means/defines" patterns.

    Args:
        text: Text to extract from
        note_id: Note ID for backlinks
        segment_ids: Segment IDs for backlinks
        project: Project name
        date: Date for the definition
        source_file: Source file path

    Returns:
        List of Definition objects
    """
    if not date:
        date = datetime.now()

    definitions: list[Definition] = []

    # Pattern: "Term is definition" or "Term means definition" or "Term defines definition"
    definition_patterns = [
        re.compile(
            r"([A-Z][A-Za-z\s]+?)\s+(?:is|are)\s+(.+?)(?=[\.\n]|$)",
            re.IGNORECASE,
        ),
        re.compile(
            r"([A-Z][A-Za-z\s]+?)\s+means\s+(.+?)(?=[\.\n]|$)",
            re.IGNORECASE,
        ),
        re.compile(
            r"([A-Z][A-Za-z\s]+?)\s+defines?\s+(.+?)(?=[\.\n]|$)",
            re.IGNORECASE,
        ),
        re.compile(
            r"([A-Z][A-Za-z\s]+?):\s+(.+?)(?=[\.\n]|$)",
            re.IGNORECASE,
        ),  # "Term: definition"
    ]

    for pattern in definition_patterns:
        for match in pattern.finditer(text):
            term = match.group(1).strip()
            definition_text = match.group(2).strip()

            # Filter out very short or invalid matches
            if len(term) > 2 and len(definition_text) > 5:
                # Avoid duplicates
                if not any(d.term.lower() == term.lower() for d in definitions):
                    definition = Definition(
                        id=uuid4(),
                        project=project,
                        term=term,
                        definition=definition_text,
                        date=date,
                        source_file=source_file,
                        backlinks=Backlinks(note_id=note_id, segment_ids=segment_ids or []),
                    )
                    definitions.append(definition)

    return definitions


def extract_faqs(
    text: str,
    note_id: Optional[str] = None,
    segment_ids: Optional[list[str]] = None,
    project: str = "default",
    date: Optional[datetime] = None,
    source_file: str = "",
) -> list[FAQ]:
    """Extract FAQs using Q?/A: patterns.

    Args:
        text: Text to extract from
        note_id: Note ID for backlinks
        segment_ids: Segment IDs for backlinks
        project: Project name
        date: Date for the FAQ
        source_file: Source file path

    Returns:
        List of FAQ objects
    """
    if not date:
        date = datetime.now()

    faqs: list[FAQ] = []

    # Pattern: "Q: question?" or "Question?" followed by "A: answer"
    qa_pattern = re.compile(
        r"(?:Q[.:]\s*|Question[.:]\s*)?(.+?\?)\s*(?:A[.:]\s*|Answer[.:]\s*)?(.+?)(?=\n\s*(?:Q[.:]|Question)|$)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )

    for match in qa_pattern.finditer(text):
        question = match.group(1).strip()
        answer = match.group(2).strip() if match.lastindex >= 2 else ""

        # If no answer found, try to find it in next lines
        if not answer:
            # Look for answer pattern separately
            answer_match = re.search(
                r"A[.:]\s*(.+?)(?=\n\s*(?:Q[.:]|Question)|$)",
                text[match.end() :],
                re.IGNORECASE | re.DOTALL,
            )
            if answer_match:
                answer = answer_match.group(1).strip()

        if len(question) > 3 and len(answer) > 5:
            faq = FAQ(
                id=uuid4(),
                project=project,
                question=question,
                answer=answer,
                date=date,
                source_file=source_file,
                backlinks=Backlinks(note_id=note_id, segment_ids=segment_ids or []),
            )
            faqs.append(faq)

    return faqs


def extract_decisions(
    text: str,
    note_id: Optional[str] = None,
    segment_ids: Optional[list[str]] = None,
    project: str = "default",
    date: Optional[datetime] = None,
    source_file: str = "",
) -> list[Decision]:
    """Extract decisions using "Decided", "Decision:" patterns.

    Args:
        text: Text to extract from
        note_id: Note ID for backlinks
        segment_ids: Segment IDs for backlinks
        project: Project name
        date: Date for the decision
        source_file: Source file path

    Returns:
        List of Decision objects
    """
    if not date:
        date = datetime.now()

    decisions: list[Decision] = []

    # Pattern: "Decided: ..." or "Decision: ..." or "We decided to ..."
    decision_patterns = [
        re.compile(
            r"(?:Decided|Decision)[:]\s*(.+?)(?=\n|$)",
            re.IGNORECASE | re.MULTILINE,
        ),
        re.compile(
            r"(?:We|The team|The group)\s+decided\s+(?:to\s+)?(.+?)(?=[\.\n]|$)",
            re.IGNORECASE | re.MULTILINE,
        ),
    ]

    for pattern in decision_patterns:
        for match in pattern.finditer(text):
            decision_text = match.group(1).strip()

            if len(decision_text) > 5:
                # Try to extract decision maker from context
                decision_maker = None
                # Look for patterns like "by John" or "by the team"
                maker_match = re.search(
                    r"\b(?:by|from|made by)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
                    text[max(0, match.start() - 50) : match.end()],
                    re.IGNORECASE,
                )
                if maker_match:
                    decision_maker = maker_match.group(1)

                decision = Decision(
                    id=uuid4(),
                    project=project,
                    decision=decision_text,
                    decision_maker=decision_maker,
                    date=date,
                    source_file=source_file,
                    backlinks=Backlinks(note_id=note_id, segment_ids=segment_ids or []),
                )
                decisions.append(decision)

    return decisions


def extract_actions(
    text: str,
    note_id: Optional[str] = None,
    segment_ids: Optional[list[str]] = None,
    project: str = "default",
    date: Optional[datetime] = None,
    source_file: str = "",
) -> list[Action]:
    """Extract actions using "Action:", owner names, due dates.

    Args:
        text: Text to extract from
        note_id: Note ID for backlinks
        segment_ids: Segment IDs for backlinks
        project: Project name
        date: Date for the action
        source_file: Source file path

    Returns:
        List of Action objects
    """
    if not date:
        date = datetime.now()

    actions: list[Action] = []

    # Pattern: "Action: ..." or "Action item: ..."
    action_pattern = re.compile(
        r"Action(?:\s+item)?[.:]\s*(.+?)(?=\n\s*(?:Action|$))",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )

    for match in action_pattern.finditer(text):
        action_text = match.group(1).strip()

        if len(action_text) < 5:
            continue

        # Extract assignee (look for "by John" or "assigned to John" or "@John")
        assignee = None
        assignee_patterns = [
            r"\b(?:by|assigned to|owner:|@)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:will|to|should)",
        ]
        for pattern in assignee_patterns:
            assignee_match = re.search(pattern, action_text, re.IGNORECASE)
            if assignee_match:
                assignee = assignee_match.group(1)
                break

        # Extract due date using dateutil
        due_date = None
        date_patterns = [
            r"(?:due|by|deadline)[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
            r"(?:due|by|deadline)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(?:due|by|deadline)[:\s]+([A-Za-z]+\s+\d{1,2})",
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",  # Standalone dates
        ]

        for pattern in date_patterns:
            date_match = re.search(pattern, action_text, re.IGNORECASE)
            if date_match:
                date_str = date_match.group(1)
                try:
                    due_date = date_parser.parse(date_str, default=date)
                    break
                except (ValueError, TypeError):
                    continue

        # Extract status if present
        status = None
        status_match = re.search(
            r"\b(status|state)[:\s]+(pending|in progress|completed|done|open|closed)",
            action_text,
            re.IGNORECASE,
        )
        if status_match:
            status = status_match.group(2).lower()

        action = Action(
            id=uuid4(),
            project=project,
            action=action_text,
            assignee=assignee,
            due_date=due_date,
            status=status or "pending",
            date=date,
            source_file=source_file,
            backlinks=Backlinks(note_id=note_id, segment_ids=segment_ids or []),
        )
        actions.append(action)

    return actions


def extract_all(
    text: str,
    note_id: Optional[str] = None,
    segment_ids: Optional[list[str]] = None,
    project: str = "default",
    date: Optional[datetime] = None,
    source_file: str = "",
) -> dict[str, list]:
    """Extract all types of structured information.

    Args:
        text: Text to extract from
        note_id: Note ID for backlinks
        segment_ids: Segment IDs for backlinks
        project: Project name
        date: Date for the extractions
        source_file: Source file path

    Returns:
        Dictionary with keys: steps, definitions, faqs, decisions, actions
    """
    return {
        "steps": extract_steps(text, note_id, segment_ids, project, date, source_file),
        "definitions": extract_definitions(text, note_id, segment_ids, project, date, source_file),
        "faqs": extract_faqs(text, note_id, segment_ids, project, date, source_file),
        "decisions": extract_decisions(text, note_id, segment_ids, project, date, source_file),
        "actions": extract_actions(text, note_id, segment_ids, project, date, source_file),
    }

