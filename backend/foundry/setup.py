"""Setup and doctor utilities for Foundry installation."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import click


TOML_TEMPLATE = """\
# Foundry configuration
# See: https://github.com/Patvscode/foundry

[server]
host = "127.0.0.1"
port = 8120

[storage]
data_dir = "~/.foundry"

[agent]
default_provider = "{provider}"
default_model = "{model}"
can_read = true
can_search = true
can_explain = true
can_propose = true
can_write = false
can_execute = false

[agent.providers.ollama]
base_url = "http://localhost:11434"

[ingestion]
max_concurrent = 3
cache_dir = "~/.foundry/cache"

[jobs]
disabled = false

[logging]
level = "INFO"
"""


def run_setup() -> None:
    """Interactive setup flow."""
    click.echo("=== Foundry Setup ===\n")

    # 1. Data directory
    data_dir = Path("~/.foundry").expanduser()
    if data_dir.exists():
        click.echo(f"✅ Data directory exists: {data_dir}")
    else:
        data_dir.mkdir(parents=True, exist_ok=True)
        click.echo(f"✅ Created data directory: {data_dir}")

    # Subdirectories
    for sub in ["cache", "logs", "workspaces"]:
        (data_dir / sub).mkdir(exist_ok=True)

    # 2. Config file
    config_path = data_dir / "config.toml"
    if config_path.exists():
        click.echo(f"✅ Config exists: {config_path}")
    else:
        # Probe for providers
        provider, model = _detect_best_provider()
        config_content = TOML_TEMPLATE.format(provider=provider, model=model)
        config_path.write_text(config_content)
        click.echo(f"✅ Created config: {config_path} (provider={provider}, model={model})")

    # 3. Dependencies
    click.echo("\n--- Dependency Check ---")
    _check_dep("git", "git --version")
    _check_dep("Python 3.11+", f"{sys.executable} --version")
    _check_dep("Node.js", "node --version")
    _check_dep("npm", "npm --version")
    _check_dep("ffmpeg (optional)", "ffmpeg -version")
    _check_dep("yt-dlp (optional)", "yt-dlp --version")

    # 4. Provider status
    click.echo("\n--- Provider Check ---")
    _check_provider_ollama()
    _check_provider_llama_cpp()

    click.echo("\n✅ Setup complete!")
    click.echo(f"Config: {config_path}")
    click.echo("Start Foundry: cd ~/foundry/backend && .venv/bin/python -m foundry.cli start --foreground")
    click.echo("Or: ./dev.sh")


def run_doctor() -> None:
    """Validate installation."""
    click.echo("=== Foundry Doctor ===\n")
    issues = 0

    # Data dir
    data_dir = Path("~/.foundry").expanduser()
    if data_dir.exists():
        click.echo(f"✅ Data directory: {data_dir}")
    else:
        click.echo(f"❌ Data directory missing: {data_dir}")
        issues += 1

    # Config
    config_path = data_dir / "config.toml"
    if config_path.exists():
        click.echo(f"✅ Config file: {config_path}")
    else:
        click.echo(f"⚠️  No config file (will use defaults): {config_path}")

    # Database
    db_path = data_dir / "foundry.db"
    if db_path.exists():
        size_mb = db_path.stat().st_size / 1e6
        click.echo(f"✅ Database: {db_path} ({size_mb:.1f} MB)")
    else:
        click.echo(f"⚠️  No database yet (created on first start): {db_path}")

    # Cache
    cache_dir = data_dir / "cache"
    if cache_dir.exists():
        click.echo(f"✅ Cache directory: {cache_dir}")
    else:
        click.echo(f"⚠️  No cache directory: {cache_dir}")

    # Disk
    usage = shutil.disk_usage(data_dir)
    free_gb = usage.free / 1e9
    click.echo(f"{'✅' if free_gb > 1 else '⚠️'}  Disk free: {free_gb:.1f} GB")

    # Git
    _check_dep("git", "git --version")

    # Provider
    click.echo("\n--- Provider Status ---")
    _check_provider_ollama()
    _check_provider_llama_cpp()

    if issues:
        click.echo(f"\n⚠️  {issues} issue(s) found. Run 'foundry setup' to fix.")
    else:
        click.echo("\n✅ Everything looks good!")


def _detect_best_provider() -> tuple[str, str]:
    """Detect the best available provider for config generation."""
    import httpx
    # Try Ollama
    try:
        resp = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        if resp.status_code < 400:
            models = resp.json().get("models", [])
            if models:
                return "ollama", models[0]["name"]
            return "ollama", ""
    except Exception:
        pass
    return "none", ""


def _check_dep(name: str, cmd: str) -> None:
    try:
        result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=5)
        version = result.stdout.strip().split("\n")[0][:60]
        click.echo(f"  ✅ {name}: {version}")
    except (FileNotFoundError, subprocess.SubprocessError):
        click.echo(f"  ❌ {name}: not found")


def _check_provider_ollama() -> None:
    import httpx
    try:
        resp = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        if resp.status_code < 400:
            models = resp.json().get("models", [])
            click.echo(f"  ✅ Ollama: {len(models)} models")
            for m in models[:3]:
                click.echo(f"      {m['name']}")
        else:
            click.echo("  ❌ Ollama: error response")
    except Exception:
        click.echo("  ❌ Ollama: not reachable (http://localhost:11434)")


def _check_provider_llama_cpp() -> None:
    import httpx
    try:
        resp = httpx.get("http://localhost:18080/v1/models", timeout=2.0)
        if resp.status_code < 400:
            click.echo("  ✅ llama.cpp: connected (http://localhost:18080)")
        else:
            click.echo("  ❌ llama.cpp: error response")
    except Exception:
        click.echo("  ❌ llama.cpp: not reachable")
