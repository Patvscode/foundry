"""Build context payloads for agent chat from workspace state."""

from __future__ import annotations

from typing import Any

from foundry.storage.database import Database
from foundry.storage.queries import (
    get_project,
    get_resource,
    get_extraction_result,
    get_provenance_for_target,
    get_subproject,
    list_notes_for_subproject,
    list_resources_for_project,
    list_subprojects_for_project,
    list_tasks_for_subproject,
)


async def build_context(
    db: Database,
    project_id: str | None = None,
    resource_id: str | None = None,
    subproject_id: str | None = None,
) -> str:
    """Build a context string describing the current workspace state for the LLM."""
    parts: list[str] = [
        "You are an assistant inside Foundry, a research-to-projects workspace.",
        "Answer based on the context below. Be concise and actionable.",
        "",
        "Current context:",
    ]

    # Project context
    if project_id:
        project = await get_project(db, project_id)
        if project:
            subprojects = await list_subprojects_for_project(db, project_id)
            resources = await list_resources_for_project(db, project_id)
            parts.append(f"- Project: \"{project['name']}\"")
            parts.append(f"  - {len(subprojects)} subprojects, {len(resources)} resources")
            if project.get("description"):
                parts.append(f"  - Description: {project['description']}")

    # Resource context
    if resource_id:
        resource = await get_resource(db, resource_id)
        if resource:
            parts.append(f"- Resource: \"{resource.get('title', resource.get('url', 'Unknown'))}\"")
            parts.append(f"  - URL: {resource.get('url', 'N/A')}")
            parts.append(f"  - Status: {resource.get('pipeline_status', 'unknown')}")

            extraction = await get_extraction_result(db, resource_id)
            if extraction:
                if extraction.get("summary"):
                    summary = extraction["summary"][:500]
                    parts.append(f"  - Summary: {summary}")
                concepts = extraction.get("key_concepts", [])
                if concepts:
                    parts.append(f"  - Key concepts: {', '.join(concepts[:10])}")
                questions = extraction.get("open_questions", [])
                if questions:
                    parts.append(f"  - Open questions: {'; '.join(questions[:5])}")

    # Subproject context
    if subproject_id:
        subproject = await get_subproject(db, subproject_id)
        if subproject:
            parts.append(f"- Subproject: \"{subproject['name']}\" ({subproject.get('type', 'unknown')})")
            parts.append(f"  - Complexity: {subproject.get('complexity', 'unknown')}")
            parts.append(f"  - Status: {subproject.get('status', 'unknown')}")

            deps = subproject.get("dependencies", [])
            if deps:
                parts.append(f"  - Dependencies: {', '.join(deps)}")

            steps = subproject.get("setup_steps", [])
            if steps:
                parts.append(f"  - Setup steps: {'; '.join(steps)}")

            tasks = await list_tasks_for_subproject(db, subproject_id)
            if tasks:
                done = sum(1 for t in tasks if t.get("status") == "done")
                parts.append(f"  - Tasks: {len(tasks)} ({done} done, {len(tasks) - done} todo)")
                todo_titles = [t["title"] for t in tasks if t.get("status") == "todo"][:5]
                if todo_titles:
                    parts.append(f"  - Open tasks: {'; '.join(todo_titles)}")

            notes = await list_notes_for_subproject(db, subproject_id)
            if notes:
                parts.append(f"  - Notes: {len(notes)}")

            provenance = await get_provenance_for_target(db, "subproject", subproject_id)
            for prov in provenance:
                parts.append(f"  - Source: {prov.get('resource_url', 'unknown')} (confidence: {int(prov.get('confidence', 0) * 100)}%)")
                if prov.get("context"):
                    parts.append(f"    Context: \"{prov['context']}\"")

    if len(parts) <= 4:
        parts.append("- No specific context. Answer general questions about Foundry.")

    return "\n".join(parts)


async def build_fallback_response(
    db: Database,
    subproject_id: str | None = None,
    resource_id: str | None = None,
) -> str:
    """Build a data-driven response when no LLM is available."""
    parts = ["⚠ No LLM provider available. Here's what I can tell you from the stored data:\n"]

    if subproject_id:
        subproject = await get_subproject(db, subproject_id)
        if subproject:
            parts.append(f"**{subproject['name']}** ({subproject.get('type', 'unknown')}, {subproject.get('complexity', 'unknown')} complexity)")
            deps = subproject.get("dependencies", [])
            if deps:
                parts.append(f"- Dependencies: {', '.join(deps)}")
            steps = subproject.get("setup_steps", [])
            if steps:
                parts.append("- Setup steps:")
                for i, s in enumerate(steps, 1):
                    parts.append(f"  {i}. {s}")

            tasks = await list_tasks_for_subproject(db, subproject_id)
            if tasks:
                done = sum(1 for t in tasks if t.get("status") == "done")
                parts.append(f"- Tasks: {len(tasks)} total ({done} completed)")
                todo = [t["title"] for t in tasks if t.get("status") == "todo"][:5]
                if todo:
                    parts.append("- Open tasks: " + "; ".join(todo))

            provenance = await get_provenance_for_target(db, "subproject", subproject_id)
            for prov in provenance:
                parts.append(f"- Source: {prov.get('resource_url', 'unknown')}")

    if resource_id:
        extraction = await get_extraction_result(db, resource_id)
        if extraction and extraction.get("summary"):
            parts.append(f"\nResource summary: {extraction['summary'][:300]}")

    if len(parts) <= 1:
        parts.append("No context data available. Try selecting a project, resource, or subproject first.")

    return "\n".join(parts)
