from __future__ import annotations

from fastapi import APIRouter

from foundry.api import agent_chat, files, notes, projects, resources, subprojects, system, tasks

router = APIRouter()
router.include_router(system.router)
router.include_router(projects.router)
router.include_router(resources.router)
router.include_router(subprojects.router)
router.include_router(files.router)
router.include_router(tasks.router)
router.include_router(notes.router)
router.include_router(agent_chat.router)
