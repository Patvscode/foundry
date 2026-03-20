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


def _slugify(name: str) -> str:
    """Turn a name into a filesystem-safe slug."""
    import re
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = slug.strip("-")
    return slug[:80] or "subproject"


def create_subproject_workspace(
    project_path: str,
    subproject_id: str,
    name: str,
    description: str = "",
    dependencies: list[str] | None = None,
    setup_steps: list[str] | None = None,
) -> Path:
    """Create a subproject directory inside a project workspace. Returns the path."""
    project_dir = Path(project_path)
    slug = _slugify(name)

    # Avoid collisions by appending short ID suffix if slug dir exists
    subproject_dir = project_dir / slug
    if subproject_dir.exists():
        subproject_dir = project_dir / f"{slug}-{subproject_id[:8]}"

    subproject_dir.mkdir(parents=True, exist_ok=True)

    # Metadata dir
    (subproject_dir / ".foundry").mkdir(exist_ok=True)

    # README with useful content from the proposal
    readme_lines = [f"# {name}\n"]
    if description:
        readme_lines.append(f"\n{description}\n")
    if dependencies:
        readme_lines.append("\n## Dependencies\n")
        for dep in dependencies:
            readme_lines.append(f"- {dep}\n")
    if setup_steps:
        readme_lines.append("\n## Setup Steps\n")
        for i, step in enumerate(setup_steps, 1):
            readme_lines.append(f"{i}. {step}\n")
    readme_lines.append(
        "\n---\n*Created by [Foundry](https://github.com/Patvscode/foundry)*\n"
    )

    readme = subproject_dir / "README.md"
    if not readme.exists():
        readme.write_text("".join(readme_lines), encoding="utf-8")

    logger.info("Created subproject workspace: %s", subproject_dir)
    return subproject_dir
