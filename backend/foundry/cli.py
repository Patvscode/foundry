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


@main.command()
def setup() -> None:
    """Interactive setup: create config, directories, check dependencies."""
    from foundry.setup import run_setup
    run_setup()


@main.command()
def doctor() -> None:
    """Validate Foundry installation and configuration."""
    from foundry.setup import run_doctor
    run_doctor()


@main.command()
def providers() -> None:
    """Show available LLM providers and their status."""
    import asyncio
    asyncio.run(_show_providers())


async def _show_providers() -> None:
    settings = get_settings()
    base_url = f"http://{settings.server.host}:{settings.server.port}"

    # Try the running server first
    try:
        response = httpx.get(f"{base_url}/api/system/providers", timeout=3.0)
        if response.status_code < 400:
            data = response.json()
            click.echo(f"Mode: {data.get('mode', 'unknown')}")
            click.echo(f"Active provider: {data.get('active_provider', 'none')}")
            click.echo(f"Active model: {data.get('active_model', 'none')}")
            click.echo(f"Recommended: {data.get('recommended', 'fallback')}")
            click.echo()
            for p in data.get("providers", []):
                status_icon = "✅" if p["status"] in ("connected", "always_available", "configured") else "❌"
                click.echo(f"  {status_icon} {p['name']} ({p['id']}): {p['status']}")
                if p.get("models"):
                    for m in p["models"][:5]:
                        name = m["name"] if isinstance(m, dict) else m
                        click.echo(f"      model: {name}")
            click.echo()
            click.echo(data.get("setup_hint", ""))
            return
    except Exception:
        pass

    # Offline fallback: probe directly
    click.echo("(Server not running — probing providers directly)")
    click.echo()

    # Ollama
    try:
        resp = httpx.get(f"{settings.agent.providers.ollama.base_url}/api/tags", timeout=3.0)
        if resp.status_code < 400:
            models = resp.json().get("models", [])
            click.echo(f"  ✅ Ollama: {len(models)} models available")
            for m in models[:5]:
                click.echo(f"      {m['name']}")
        else:
            click.echo("  ❌ Ollama: reachable but returned error")
    except Exception:
        click.echo("  ❌ Ollama: not reachable")

    # llama.cpp
    try:
        resp = httpx.get("http://localhost:18080/v1/models", timeout=3.0)
        if resp.status_code < 400:
            click.echo("  ✅ llama.cpp: connected")
        else:
            click.echo("  ❌ llama.cpp: not reachable")
    except Exception:
        click.echo("  ❌ llama.cpp: not reachable")

    # API keys
    if settings.agent.providers.openai.api_key:
        click.echo("  ✅ OpenAI: API key configured")
    else:
        click.echo("  ❌ OpenAI: no API key")

    if settings.agent.providers.anthropic.api_key:
        click.echo("  ✅ Anthropic: API key configured")
    else:
        click.echo("  ❌ Anthropic: no API key")


if __name__ == "__main__":
    main()
