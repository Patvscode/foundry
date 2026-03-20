"""Parse agent responses for actionable suggestions and execute approved actions."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from foundry.storage.database import Database
from foundry.storage.queries import insert_note, insert_task, new_id

logger = logging.getLogger(__name__)


def extract_suggestions(response_text: str) -> list[dict[str, Any]]:
    """Extract actionable suggestions from agent response text.

    Looks for patterns like:
    - [TASK] title text
    - [NOTE] title text
    """
    suggestions: list[dict[str, Any]] = []

    for line in response_text.split("\n"):
        line = line.strip()
        task_match = re.match(r"\[TASK\]\s*(.+)", line, re.IGNORECASE)
        if task_match:
            suggestions.append({
                "type": "task",
                "title": task_match.group(1).strip(),
            })
            continue

        note_match = re.match(r"\[NOTE\]\s*(.+)", line, re.IGNORECASE)
        if note_match:
            suggestions.append({
                "type": "note",
                "title": note_match.group(1).strip(),
            })

    return suggestions


async def execute_action(
    db: Database,
    subproject_id: str,
    action: dict[str, Any],
) -> dict[str, Any] | None:
    """Execute an approved action (create task or note)."""
    action_type = action.get("type")
    title = action.get("title", "")

    if not title:
        return None

    if action_type == "task":
        return await insert_task(
            db, new_id(), subproject_id, title,
            description=action.get("description", ""),
            source="agent",
        )
    elif action_type == "note":
        return await insert_note(
            db, new_id(), subproject_id, title,
            content=action.get("content", ""),
            source="agent",
        )

    return None
