"""Workspace filesystem operations. Creates and manages project directories."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def create_project_workspace(project_id: str, name: str, data_dir: str) -> Path:
    """Create the workspace directory for a project. Returns the absolute path."""
    workspaces_root = Path(data_dir) / "workspaces"
    workspaces_root.mkdir(parents=True, exist_ok=True)

    project_dir = workspaces_root / project_id
    project_dir.mkdir(exist_ok=True)

    # Foundry metadata directory
    foundry_dir = project_dir / ".foundry"
    foundry_dir.mkdir(exist_ok=True)
    (foundry_dir / "resources").mkdir(exist_ok=True)
    (foundry_dir / "history").mkdir(exist_ok=True)

    # Initial README
    readme = project_dir / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# {name}\n\n"
            f"Created by [Foundry](https://github.com/Patvscode/foundry).\n",
            encoding="utf-8",
        )

    # Git init for checkpoint support
    git_dir = project_dir / ".git"
    if not git_dir.exists():
        try:
            subprocess.run(
                ["git", "init", "--quiet"],
                cwd=project_dir,
                capture_output=True,
                timeout=10,
            )
            # Initial commit so checkpoints have a base
            subprocess.run(
                ["git", "add", "-A"],
                cwd=project_dir,
                capture_output=True,
                timeout=10,
            )
            subprocess.run(
                ["git", "commit", "-m", "foundry: project created", "--quiet", "--allow-empty"],
                cwd=project_dir,
                capture_output=True,
                timeout=10,
            )
            logger.info("Initialized git repo for project %s", project_id)
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("Could not init git repo for project %s (git may not be available)", project_id)

    return project_dir
