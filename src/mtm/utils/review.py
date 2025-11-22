"""Review workflow utilities for module approval."""

import os
from typing import Optional

from mtm.storage.db import get_db


def set_module_state(
    module_id: str,
    state: str,
    owner: Optional[str] = None,
) -> None:
    """Set module approval state.

    Args:
        module_id: Module ID
        state: Approval state (draft, review, approved)
        owner: Owner identifier (defaults to current user)
    """
    if state not in ["draft", "review", "approved"]:
        raise ValueError(f"Invalid state: {state}. Must be 'draft', 'review', or 'approved'")

    db = get_db()
    
    if owner is None:
        owner = os.getenv("MTM_USER", os.getenv("USER", os.getenv("USERNAME", "system")))

    # Update module
    module = db.db["modules"].get(module_id)
    if not module:
        raise ValueError(f"Module {module_id} not found")

    db.db["modules"].update(module_id, {"approval_state": state, "owner": owner})

    # Log audit event
    db.log_audit(
        action="approval_state_change",
        entity_type="module",
        entity_id=module_id,
        user=owner,
        details={"old_state": module.get("approval_state", "draft"), "new_state": state},
    )


def get_modules_by_state(state: str, project: Optional[str] = None) -> list[dict]:
    """Get modules by approval state.

    Args:
        state: Approval state (draft, review, approved)
        project: Optional project filter

    Returns:
        List of module records
    """
    db = get_db()
    
    if project:
        modules = list(db.db["modules"].rows_where("approval_state = ? AND project = ?", [state, project]))
    else:
        modules = list(db.db["modules"].rows_where("approval_state = ?", [state]))
    
    return modules


def check_approval_required(module_id: str) -> bool:
    """Check if module requires approval before export.

    Args:
        module_id: Module ID

    Returns:
        True if approval is required
    """
    db = get_db()
    module = db.db["modules"].get(module_id)
    
    if not module:
        return False
    
    state = module.get("approval_state", "draft")
    return state != "approved"

