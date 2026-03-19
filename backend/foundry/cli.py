from __future__ import annotations

import importlib.metadata
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import click
import httpx

from foundry.config import FoundrySettings, get_settings, mask_secrets


def _get_version() -> str:
    try:
        return importlib.metadata.version("foundry")
    except importlib.metadata.PackageNotFoundError:
        return "0.1.0"


def _pid_file(settings: FoundrySettings) -> Path:
    return Path(settings.storage.data_dir) / "foundry.pid"


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


@click.group()
def main() -> None:
    """Foundry command-line interface."""


@main.command()
@click.option("--foreground", is_flag=True, help="Run uvicorn in foreground.")
def start(foreground: bool) -> None:
    settings = get_settings()
    pid_path = _pid_file(settings)

    if pid_path.exists():
        existing_pid = int(pid_path.read_text().strip())
        if _is_running(existing_pid):
            raise click.ClickException(f"Foundry already running with PID {existing_pid}")
        pid_path.unlink(missing_ok=True)

    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "foundry.main:app",
        "--host",
        settings.server.host,
        "--port",
        str(settings.server.port),
    ]

    if foreground:
        click.echo("Starting Foundry in foreground...")
        process = subprocess.Popen(command)
        pid_path.write_text(str(process.pid))
        process.wait()
        pid_path.unlink(missing_ok=True)
        return

    logs_dir = Path(settings.storage.data_dir) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stdout_file = (logs_dir / "server.out").open("a", encoding="utf-8")
    stderr_file = (logs_dir / "server.err").open("a", encoding="utf-8")

    process = subprocess.Popen(
        command,
        stdout=stdout_file,
        stderr=stderr_file,
        start_new_session=True,
    )
    pid_path.write_text(str(process.pid))
    click.echo(f"Foundry started with PID {process.pid}")


@main.command()
def stop() -> None:
    settings = get_settings()
    pid_path = _pid_file(settings)

    if not pid_path.exists():
        raise click.ClickException("Foundry is not running (no PID file found)")

    pid = int(pid_path.read_text().strip())
    if not _is_running(pid):
        pid_path.unlink(missing_ok=True)
        raise click.ClickException("PID file exists but process is not running")

    os.kill(pid, signal.SIGTERM)
    for _ in range(30):
        if not _is_running(pid):
            break
        time.sleep(0.1)

    pid_path.unlink(missing_ok=True)
    click.echo(f"Stopped Foundry process {pid}")


@main.command()
def status() -> None:
    settings = get_settings()
    pid_path = _pid_file(settings)

    running = False
    pid: int | None = None
    if pid_path.exists():
        pid = int(pid_path.read_text().strip())
        running = _is_running(pid)

    click.echo(f"running: {running}")
    if pid is not None:
        click.echo(f"pid: {pid}")

    base_url = f"http://{settings.server.host}:{settings.server.port}"
    try:
        response = httpx.get(f"{base_url}/api/system/health", timeout=2.0)
        click.echo(f"health_http: {response.status_code}")
    except httpx.HTTPError:
        click.echo("health_http: unreachable")


@main.command()
def health() -> None:
    settings = get_settings()
    base_url = f"http://{settings.server.host}:{settings.server.port}"
    try:
        response = httpx.get(f"{base_url}/api/system/health", timeout=3.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise click.ClickException(f"Health check failed: {exc}") from exc

    payload: dict[str, Any] = response.json()
    click.echo(json.dumps(payload, indent=2, sort_keys=True))


@main.command()
def version() -> None:
    click.echo(_get_version())


@main.group()
def config() -> None:
    """Configuration utilities."""


@config.command("show")
def config_show() -> None:
    settings = get_settings()
    payload = mask_secrets(settings.model_dump())
    click.echo(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
