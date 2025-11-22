"""Pydantic models for meeting-to-modules data structures."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Backlinks(BaseModel):
    """Backlinks to source notes and segments."""

    note_id: Optional[UUID] = None
    segment_ids: list[UUID] = Field(default_factory=list)


class Note(BaseModel):
    """A meeting note document."""

    id: UUID = Field(default_factory=uuid4)
    project: str
    roles: list[str] = Field(default_factory=list)
    date: datetime
    source_file: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    content: Optional[str] = None
    title: Optional[str] = None
    metadata: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Segment(BaseModel):
    """A segment or section within a note."""

    id: UUID = Field(default_factory=uuid4)
    note_id: UUID
    project: str
    roles: list[str] = Field(default_factory=list)
    date: datetime
    source_file: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    content: str
    segment_type: Optional[str] = None  # e.g., "paragraph", "list", "quote"
    order: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Theme(BaseModel):
    """A theme or topic identified across multiple notes."""

    id: UUID = Field(default_factory=uuid4)
    project: str
    name: str
    description: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    support_count: int = 0  # Number of supporting documents
    backlinks: Backlinks = Field(default_factory=Backlinks)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Step(BaseModel):
    """A process step or procedure."""

    id: UUID = Field(default_factory=uuid4)
    project: str
    step_number: Optional[int] = None
    title: str
    description: Optional[str] = None
    roles: list[str] = Field(default_factory=list)
    date: datetime
    source_file: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    backlinks: Backlinks = Field(default_factory=Backlinks)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Definition(BaseModel):
    """A definition or glossary entry."""

    id: UUID = Field(default_factory=uuid4)
    project: str
    term: str
    definition: str
    context: Optional[str] = None
    roles: list[str] = Field(default_factory=list)
    date: datetime
    source_file: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    backlinks: Backlinks = Field(default_factory=Backlinks)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class FAQ(BaseModel):
    """A frequently asked question and answer."""

    id: UUID = Field(default_factory=uuid4)
    project: str
    question: str
    answer: str
    category: Optional[str] = None
    roles: list[str] = Field(default_factory=list)
    date: datetime
    source_file: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    backlinks: Backlinks = Field(default_factory=Backlinks)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Decision(BaseModel):
    """A decision made during a meeting."""

    id: UUID = Field(default_factory=uuid4)
    project: str
    decision: str
    rationale: Optional[str] = None
    decision_maker: Optional[str] = None
    roles: list[str] = Field(default_factory=list)
    date: datetime
    source_file: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    status: Optional[str] = None  # e.g., "pending", "approved", "rejected"
    backlinks: Backlinks = Field(default_factory=Backlinks)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Action(BaseModel):
    """An action item or task."""

    id: UUID = Field(default_factory=uuid4)
    project: str
    action: str
    assignee: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None  # e.g., "pending", "in_progress", "completed"
    roles: list[str] = Field(default_factory=list)
    date: datetime
    source_file: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    backlinks: Backlinks = Field(default_factory=Backlinks)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Topic(BaseModel):
    """A topic discussed in a meeting."""

    id: UUID = Field(default_factory=uuid4)
    project: str
    name: str
    description: Optional[str] = None
    roles: list[str] = Field(default_factory=list)
    date: datetime
    source_file: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    backlinks: Backlinks = Field(default_factory=Backlinks)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Module(BaseModel):
    """A generated module containing structured content."""

    id: UUID = Field(default_factory=uuid4)
    project: str
    title: str
    description: Optional[str] = None
    module_type: Optional[str] = None  # e.g., "guide", "reference", "tutorial"
    content: Optional[str] = None
    themes: list[UUID] = Field(default_factory=list)  # Theme IDs
    steps: list[UUID] = Field(default_factory=list)  # Step IDs
    definitions: list[UUID] = Field(default_factory=list)  # Definition IDs
    faqs: list[UUID] = Field(default_factory=list)  # FAQ IDs
    decisions: list[UUID] = Field(default_factory=list)  # Decision IDs
    actions: list[UUID] = Field(default_factory=list)  # Action IDs
    topics: list[UUID] = Field(default_factory=list)  # Topic IDs
    backlinks: Backlinks = Field(default_factory=Backlinks)
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class VersionEntry(BaseModel):
    """Version tracking entry for modules."""

    id: UUID = Field(default_factory=uuid4)
    module_id: UUID
    version: int
    project: str
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    changes: Optional[str] = None  # Description of changes
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    backlinks: Backlinks = Field(default_factory=Backlinks)

