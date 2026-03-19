from __future__ import annotations

from fastapi import APIRouter

from foundry.api import projects, system

router = APIRouter()
router.include_router(system.router)
router.include_router(projects.router)
