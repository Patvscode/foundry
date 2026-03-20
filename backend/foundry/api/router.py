from __future__ import annotations

from fastapi import APIRouter

from foundry.api import projects, resources, subprojects, system

router = APIRouter()
router.include_router(system.router)
router.include_router(projects.router)
router.include_router(resources.router)
router.include_router(subprojects.router)
