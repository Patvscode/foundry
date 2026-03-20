"""In-process DB-backed job runner. Polls the jobs table for queued work."""

from __future__ import annotations

import asyncio
import logging
import os

from foundry.config import FoundrySettings

from foundry.storage.database import Database
from foundry.storage.queries import get_queued_jobs, mark_stale_jobs, update_job

logger = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL = 2.0  # seconds


class JobRunner:
    """Async job runner that processes queued jobs from the DB."""

    def __init__(self, db: Database, settings: FoundrySettings) -> None:
        self.db = db
        self.settings = settings
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        """Start the runner. Mark any leftover running jobs as stale."""
        await mark_stale_jobs(self.db)

        if self.settings.jobs.disabled:
            logger.info("Job runner disabled via config (jobs.disabled=true)")
            return

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Job runner started")

    async def stop(self) -> None:
        """Stop the runner gracefully. Finishes current job if any."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Job runner stopped")

    async def _poll_loop(self) -> None:
        """Main loop: poll for queued jobs, run one at a time."""
        while self._running:
            try:
                jobs = await get_queued_jobs(self.db, limit=1)
                if jobs:
                    await self._process_job(jobs[0])
                else:
                    await asyncio.sleep(self.settings.jobs.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in job runner poll loop")
                await asyncio.sleep(self.settings.jobs.poll_interval)

    async def _process_job(self, job: dict) -> None:
        """Process a single job."""
        job_id = job["id"]
        job_type = job["type"]
        resource_id = job.get("result")  # We store resource_id in the result field at creation

        logger.info("Processing job %s (type=%s)", job_id, job_type)
        await update_job(self.db, job_id, status="running", pid=os.getpid())

        try:
            if job_type == "ingestion" and resource_id:
                from foundry.ingestion.pipeline import run_pipeline
                await run_pipeline(resource_id, self.db, self.settings)
                await update_job(self.db, job_id, status="completed")
            else:
                await update_job(self.db, job_id, status="failed", error=f"Unknown job type: {job_type}")
        except Exception as e:
            logger.exception("Job %s failed", job_id)
            await update_job(self.db, job_id, status="failed", error=str(e))
