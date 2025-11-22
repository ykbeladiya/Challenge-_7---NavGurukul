"""Database management using sqlite-utils."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

import sqlite_utils

from mtm.config import get_config


class Database:
    """Database manager for meeting-to-modules."""

    def __init__(self, db_path: Optional[str | Path] = None):
        """Initialize database connection.

        Args:
            db_path: Path to database file. Defaults to config value.
        """
        if db_path is None:
            config = get_config()
            db_path = config.db_path
        
        # Convert to Path if it's a string
        if isinstance(db_path, str):
            db_path = Path(db_path)

        # Ensure database directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db = sqlite_utils.Database(str(db_path))
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        """Initialize database schema with all tables, indexes, and foreign keys."""
        # Notes table
        if "notes" not in self.db.table_names():
            self.db["notes"].create(
                {
                    "id": str,  # UUID as string
                    "project": str,
                    "date": str,  # ISO format datetime
                    "source_file": str,
                    "line_start": int,
                    "line_end": int,
                    "content": str,
                    "title": str,
                    "metadata": str,  # JSON string
                    "content_sha256": str,  # SHA256 hash of content for duplicate detection
                    "source_path": str,  # Original file path
                    "mtime": str,  # File modification time
                    "size": int,  # File size in bytes
                    "created_at": str,
                    "updated_at": str,
                },
                pk="id",
            )
            self.db["notes"].create_index(["project"])
            self.db["notes"].create_index(["date"])
            self.db["notes"].create_index(["source_file"])
            self.db["notes"].create_index(["content_sha256"])  # For duplicate detection
        else:
            # Check and add new columns if they don't exist (for existing databases)
            table = self.db["notes"]
            columns = table.columns_dict

            # Add missing columns using ALTER TABLE
            if "content_sha256" not in columns:
                self.db.execute("ALTER TABLE notes ADD COLUMN content_sha256 TEXT")
                table.create_index(["content_sha256"])
            if "source_path" not in columns:
                self.db.execute("ALTER TABLE notes ADD COLUMN source_path TEXT")
            if "mtime" not in columns:
                self.db.execute("ALTER TABLE notes ADD COLUMN mtime TEXT")
            if "size" not in columns:
                self.db.execute("ALTER TABLE notes ADD COLUMN size INTEGER")

        # Segments table
        if "segments" not in self.db.table_names():
            self.db["segments"].create(
                {
                    "id": str,  # UUID as string
                    "note_id": str,  # FK to notes
                    "project": str,
                    "date": str,
                    "source_file": str,
                    "line_start": int,
                    "line_end": int,
                    "content": str,
                    "segment_type": str,
                    "order": int,
                    "created_at": str,
                    "updated_at": str,
                },
                pk="id",
                foreign_keys=[("note_id", "notes", "id")],
            )
            self.db["segments"].create_index(["note_id"])
            self.db["segments"].create_index(["project"])
            self.db["segments"].create_index(["date"])

        # Themes table
        if "themes" not in self.db.table_names():
            self.db["themes"].create(
                {
                    "id": str,  # UUID as string
                    "project": str,
                    "name": str,
                    "description": str,
                    "keywords": str,  # JSON array
                    "support_count": int,
                    "note_id": str,  # FK to notes (from backlinks)
                    "created_at": str,
                    "updated_at": str,
                },
                pk="id",
                foreign_keys=[("note_id", "notes", "id")],
            )
            self.db["themes"].create_index(["project"])
            self.db["themes"].create_index(["name"])

        # Extractions table (polymorphic - stores different extraction types)
        if "extractions" not in self.db.table_names():
            self.db["extractions"].create(
                {
                    "id": str,  # UUID as string
                    "type": str,  # step, definition, faq, decision, action, topic
                    "project": str,
                    "payload": str,  # JSON string
                    "note_id": str,  # FK to notes (from backlinks)
                    "segment_ids": str,  # JSON array of UUIDs
                    "source_file": str,
                    "line_start": int,
                    "line_end": int,
                    "date": str,
                    "created_at": str,
                    "updated_at": str,
                },
                pk="id",
                foreign_keys=[("note_id", "notes", "id")],
            )
            self.db["extractions"].create_index(["type"])
            self.db["extractions"].create_index(["project"])
            self.db["extractions"].create_index(["note_id"])

        # Topic-role mapping table
        if "topic_role_map" not in self.db.table_names():
            self.db["topic_role_map"].create(
                {
                    "id": str,  # UUID as string
                    "topic_id": str,  # References extraction with type='topic' or segment/theme ID
                    "role": str,
                    "project": str,
                    "confidence": float,  # Confidence score (0-100)
                    "created_at": str,
                },
                pk="id",
            )
            self.db["topic_role_map"].create_index(["topic_id"])
            self.db["topic_role_map"].create_index(["role"])
            self.db["topic_role_map"].create_index(["project"])
            self.db["topic_role_map"].create_index(["confidence"])
        else:
            # Add confidence column if it doesn't exist (for existing databases)
            table = self.db["topic_role_map"]
            columns = table.columns_dict
            if "confidence" not in columns:
                self.db.execute("ALTER TABLE topic_role_map ADD COLUMN confidence REAL DEFAULT 0.0")
                table.create_index(["confidence"])

        # Modules table
        if "modules" not in self.db.table_names():
            self.db["modules"].create(
                {
                    "id": str,  # UUID as string
                    "project": str,
                    "title": str,
                    "description": str,
                    "module_type": str,
                    "content": str,
                    "theme_ids": str,  # JSON array
                    "step_ids": str,  # JSON array
                    "definition_ids": str,  # JSON array
                    "faq_ids": str,  # JSON array
                    "decision_ids": str,  # JSON array
                    "action_ids": str,  # JSON array
                    "topic_ids": str,  # JSON array
                    "note_id": str,  # FK to notes (from backlinks)
                    "version": int,
                    "created_at": str,
                    "updated_at": str,
                },
                pk="id",
                foreign_keys=[("note_id", "notes", "id")],
            )
            self.db["modules"].create_index(["project"])
            self.db["modules"].create_index(["module_type"])
            self.db["modules"].create_index(["version"])
        else:
            # Add review workflow columns if they don't exist
            table = self.db["modules"]
            columns = table.columns_dict
            if "approval_state" not in columns:
                self.db.execute("ALTER TABLE modules ADD COLUMN approval_state TEXT DEFAULT 'draft'")
                table.create_index(["approval_state"])
            if "owner" not in columns:
                self.db.execute("ALTER TABLE modules ADD COLUMN owner TEXT")
                table.create_index(["owner"])

        # Versions table
        if "versions" not in self.db.table_names():
            self.db["versions"].create(
                {
                    "id": str,  # UUID as string
                    "module_id": str,  # FK to modules
                    "version": int,
                    "project": str,
                    "title": str,
                    "description": str,
                    "content": str,
                    "changes": str,
                    "created_by": str,
                    "note_id": str,  # FK to notes (from backlinks)
                    "created_at": str,
                },
                pk="id",
                foreign_keys=[
                    ("module_id", "modules", "id"),
                    ("note_id", "notes", "id"),
                ],
            )
            self.db["versions"].create_index(["module_id"])
            self.db["versions"].create_index(["version"])
            self.db["versions"].create_index(["project"])

        # Runs table (for tracking processing runs)
        if "runs" not in self.db.table_names():
            self.db["runs"].create(
                {
                    "id": str,  # UUID as string
                    "run_type": str,  # ingest, preprocess, analyze, extract, generate
                    "project": str,
                    "status": str,  # started, completed, failed
                    "input_files": str,  # JSON array
                    "output_files": str,  # JSON array
                    "config": str,  # JSON object
                    "error": str,
                    "started_at": str,
                    "completed_at": str,
                    "created_at": str,
                },
                pk="id",
            )
            self.db["runs"].create_index(["run_type"])
            self.db["runs"].create_index(["project"])
            self.db["runs"].create_index(["status"])
            self.db["runs"].create_index(["started_at"])

        # Audit log table (for tracking who/what/when)
        if "audit_log" not in self.db.table_names():
            self.db["audit_log"].create(
                {
                    "id": str,  # UUID as string
                    "action": str,  # create, update, delete, approve, reject, export, etc.
                    "entity_type": str,  # note, segment, theme, module, extraction, etc.
                    "entity_id": str,  # ID of the entity
                    "user": str,  # User identifier (from environment or CLI)
                    "details": str,  # JSON object with action-specific details
                    "content_hash": str,  # SHA256 hash of content before/after change
                    "created_at": str,  # Timestamp
                },
                pk="id",
            )
            self.db["audit_log"].create_index(["action"])
            self.db["audit_log"].create_index(["entity_type"])
            self.db["audit_log"].create_index(["entity_id"])
            self.db["audit_log"].create_index(["user"])
            self.db["audit_log"].create_index(["created_at"])

    # Upsert helpers

    def upsert_note(
        self,
        note_id: UUID | str,
        project: str,
        date: datetime,
        source_file: str,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None,
        content: Optional[str] = None,
        title: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        content_sha256: Optional[str] = None,
        source_path: Optional[str] = None,
        mtime: Optional[datetime] = None,
        size: Optional[int] = None,
    ) -> None:
        """Upsert a note."""
        now = datetime.now().isoformat()
        note_id_str = str(note_id) if isinstance(note_id, UUID) else note_id

        record = {
            "id": note_id_str,
            "project": project,
            "date": date.isoformat(),
            "source_file": source_file,
            "line_start": line_start,
            "line_end": line_end,
            "content": content or "",
            "title": title or "",
            "metadata": json.dumps(metadata or {}),
            "content_sha256": content_sha256 or "",
            "source_path": source_path or source_file,
            "mtime": mtime.isoformat() if mtime else now,
            "size": size or 0,
            "updated_at": now,
        }

        # Check if exists to set created_at
        try:
            existing = self.db["notes"].get(note_id_str)
            record["created_at"] = existing["created_at"]
        except sqlite_utils.db.NotFoundError:
            # Note doesn't exist yet, set created_at to now
            record["created_at"] = now

        self.db["notes"].upsert(record, pk="id")

    def find_note_by_hash(self, content_sha256: str) -> Optional[dict[str, Any]]:
        """Find a note by content SHA256 hash.

        Args:
            content_sha256: SHA256 hash of content

        Returns:
            Note record if found, None otherwise
        """
        results = list(self.db["notes"].rows_where("content_sha256 = ?", [content_sha256], limit=1))
        return results[0] if results else None

    def upsert_segment(
        self,
        segment_id: UUID | str,
        note_id: UUID | str,
        project: str,
        date: datetime,
        source_file: str,
        content: str,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None,
        segment_type: Optional[str] = None,
        order: int = 0,
    ) -> None:
        """Upsert a segment."""
        now = datetime.now().isoformat()
        segment_id_str = str(segment_id) if isinstance(segment_id, UUID) else segment_id
        note_id_str = str(note_id) if isinstance(note_id, UUID) else note_id

        record = {
            "id": segment_id_str,
            "note_id": note_id_str,
            "project": project,
            "date": date.isoformat(),
            "source_file": source_file,
            "line_start": line_start,
            "line_end": line_end,
            "content": content,
            "segment_type": segment_type or "",
            "order": order,
            "updated_at": now,
        }

        try:
            existing = self.db["segments"].get(segment_id_str)
            record["created_at"] = existing["created_at"]
        except sqlite_utils.db.NotFoundError:
            # Segment doesn't exist yet, set created_at to now
            record["created_at"] = now

        self.db["segments"].upsert(record, pk="id")

    def upsert_theme(
        self,
        theme_id: UUID | str,
        project: str,
        name: str,
        description: Optional[str] = None,
        keywords: Optional[list[str]] = None,
        support_count: int = 0,
        note_id: Optional[UUID | str] = None,
    ) -> None:
        """Upsert a theme."""
        now = datetime.now().isoformat()
        theme_id_str = str(theme_id) if isinstance(theme_id, UUID) else theme_id

        record = {
            "id": theme_id_str,
            "project": project,
            "name": name,
            "description": description or "",
            "keywords": json.dumps(keywords or []),
            "support_count": support_count,
            "note_id": str(note_id) if note_id else None,
            "updated_at": now,
        }

        existing = self.db["themes"].get(theme_id_str)
        if existing:
            record["created_at"] = existing["created_at"]
        else:
            record["created_at"] = now

        self.db["themes"].upsert(record, pk="id")

    def upsert_extraction(
        self,
        extraction_id: UUID | str,
        extraction_type: str,
        project: str,
        payload: dict[str, Any],
        note_id: Optional[UUID | str] = None,
        segment_ids: Optional[list[UUID | str]] = None,
        source_file: Optional[str] = None,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None,
        date: Optional[datetime] = None,
    ) -> None:
        """Upsert an extraction (step, definition, faq, decision, action, topic)."""
        now = datetime.now().isoformat()
        extraction_id_str = (
            str(extraction_id) if isinstance(extraction_id, UUID) else extraction_id
        )

        # Convert segment_ids to strings
        segment_ids_str = (
            [str(sid) if isinstance(sid, UUID) else sid for sid in segment_ids]
            if segment_ids
            else []
        )

        record = {
            "id": extraction_id_str,
            "type": extraction_type,
            "project": project,
            "payload": json.dumps(payload),
            "note_id": str(note_id) if note_id else None,
            "segment_ids": json.dumps(segment_ids_str),
            "source_file": source_file or "",
            "line_start": line_start,
            "line_end": line_end,
            "date": date.isoformat() if date else now,
            "updated_at": now,
        }

        existing = self.db["extractions"].get(extraction_id_str)
        if existing:
            record["created_at"] = existing["created_at"]
        else:
            record["created_at"] = now

        self.db["extractions"].upsert(record, pk="id")

    def upsert_topic_role(
        self,
        topic_id: UUID | str,
        role: str,
        project: str,
    ) -> None:
        """Upsert a topic-role mapping."""
        from uuid import uuid4

        topic_id_str = str(topic_id) if isinstance(topic_id, UUID) else topic_id
        now = datetime.now().isoformat()

        # Check if mapping already exists
        existing = self.db["topic_role_map"].rows_where(
            "topic_id = ? AND role = ?", [topic_id_str, role]
        )
        if existing:
            return  # Already exists

        record = {
            "id": str(uuid4()),
            "topic_id": topic_id_str,
            "role": role,
            "project": project,
            "created_at": now,
        }

        self.db["topic_role_map"].insert(record)

    def upsert_module(
        self,
        module_id: UUID | str,
        project: str,
        title: str,
        description: Optional[str] = None,
        module_type: Optional[str] = None,
        content: Optional[str] = None,
        theme_ids: Optional[list[UUID | str]] = None,
        step_ids: Optional[list[UUID | str]] = None,
        definition_ids: Optional[list[UUID | str]] = None,
        faq_ids: Optional[list[UUID | str]] = None,
        decision_ids: Optional[list[UUID | str]] = None,
        action_ids: Optional[list[UUID | str]] = None,
        topic_ids: Optional[list[UUID | str]] = None,
        note_id: Optional[UUID | str] = None,
        version: int = 1,
    ) -> None:
        """Upsert a module."""
        now = datetime.now().isoformat()
        module_id_str = str(module_id) if isinstance(module_id, UUID) else module_id

        # Convert all ID lists to JSON strings
        def to_json_ids(ids: Optional[list[UUID | str]]) -> str:
            if not ids:
                return "[]"
            return json.dumps([str(i) if isinstance(i, UUID) else i for i in ids])

        record = {
            "id": module_id_str,
            "project": project,
            "title": title,
            "description": description or "",
            "module_type": module_type or "",
            "content": content or "",
            "theme_ids": to_json_ids(theme_ids),
            "step_ids": to_json_ids(step_ids),
            "definition_ids": to_json_ids(definition_ids),
            "faq_ids": to_json_ids(faq_ids),
            "decision_ids": to_json_ids(decision_ids),
            "action_ids": to_json_ids(action_ids),
            "topic_ids": to_json_ids(topic_ids),
            "note_id": str(note_id) if note_id else None,
            "version": version,
            "updated_at": now,
        }

        existing = self.db["modules"].get(module_id_str)
        if existing:
            record["created_at"] = existing["created_at"]
        else:
            record["created_at"] = now

        self.db["modules"].upsert(record, pk="id")

    def upsert_version(
        self,
        version_id: UUID | str,
        module_id: UUID | str,
        version: int,
        project: str,
        title: str,
        description: Optional[str] = None,
        content: Optional[str] = None,
        changes: Optional[str] = None,
        created_by: Optional[str] = None,
        note_id: Optional[UUID | str] = None,
    ) -> None:
        """Upsert a version entry."""
        now = datetime.now().isoformat()
        version_id_str = str(version_id) if isinstance(version_id, UUID) else version_id
        module_id_str = str(module_id) if isinstance(module_id, UUID) else module_id

        record = {
            "id": version_id_str,
            "module_id": module_id_str,
            "version": version,
            "project": project,
            "title": title,
            "description": description or "",
            "content": content or "",
            "changes": changes or "",
            "created_by": created_by or "",
            "note_id": str(note_id) if note_id else None,
            "created_at": now,
        }

        self.db["versions"].upsert(record, pk="id")

    def upsert_run(
        self,
        run_id: UUID | str,
        run_type: str,
        project: str,
        status: str = "started",
        input_files: Optional[list[str]] = None,
        output_files: Optional[list[str]] = None,
        config: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ) -> None:
        """Upsert a processing run."""
        now = datetime.now().isoformat()
        run_id_str = str(run_id) if isinstance(run_id, UUID) else run_id

        record = {
            "id": run_id_str,
            "run_type": run_type,
            "project": project,
            "status": status,
            "input_files": json.dumps(input_files or []),
            "output_files": json.dumps(output_files or []),
            "config": json.dumps(config or {}),
            "error": error or "",
            "started_at": started_at.isoformat() if started_at else now,
            "completed_at": completed_at.isoformat() if completed_at else None,
            "created_at": now,
        }

        self.db["runs"].upsert(record, pk="id")

    def log_audit(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        user: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        content_hash: Optional[str] = None,
    ) -> None:
        """Log an audit event.

        Args:
            action: Action performed (create, update, delete, approve, reject, export, etc.)
            entity_type: Type of entity (note, segment, theme, module, extraction, etc.)
            entity_id: ID of the entity
            user: User identifier (defaults to environment variable or 'system')
            details: Additional action-specific details as JSON
            content_hash: SHA256 hash of content before/after change
        """
        import os
        import hashlib
        from uuid import uuid4

        if user is None:
            user = os.getenv("MTM_USER", os.getenv("USER", os.getenv("USERNAME", "system")))

        now = datetime.now().isoformat()
        record = {
            "id": str(uuid4()),
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "user": user,
            "details": json.dumps(details or {}),
            "content_hash": content_hash or "",
            "created_at": now,
        }

        self.db["audit_log"].insert(record)

    def get_audit_log(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        action: Optional[str] = None,
        user: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get audit log entries.

        Args:
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            action: Filter by action
            user: Filter by user
            limit: Maximum number of entries to return

        Returns:
            List of audit log entries
        """
        conditions = []
        params = []

        if entity_type:
            conditions.append("entity_type = ?")
            params.append(entity_type)
        if entity_id:
            conditions.append("entity_id = ?")
            params.append(entity_id)
        if action:
            conditions.append("action = ?")
            params.append(action)
        if user:
            conditions.append("user = ?")
            params.append(user)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"{where_clause} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        return list(self.db["audit_log"].rows_where(query, params))


# Global database instance (lazy loaded)
_db: Optional[Database] = None


def get_db(db_path: Optional[str | Path] = None) -> Database:
    """Get or create global database instance.

    Args:
        db_path: Path to database file. Only used on first call.

    Returns:
        Global Database instance
    """
    global _db
    if _db is None:
        _db = Database(db_path)
    return _db

