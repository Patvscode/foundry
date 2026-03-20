# Foundry

**Research-to-Projects Workspace**

Feed Foundry a URL, paper, or article. It extracts the distinct buildable projects described inside, lets you review and accept them, and organizes each into a real workspace with tasks, notes, and provenance tracking.

> Open by default. Reliable by choice. Dangerous only by consent.

## What It Does

1. **Create a project** — name it and start adding resources
2. **Add a resource** — paste a URL (web article, docs page, blog post)
3. **Automatic analysis** — Foundry extracts text, analyzes it with an LLM, and discovers distinct sub-projects
4. **Review proposals** — accept, reject, or edit discovered projects before they're created
5. **Workspace per subproject** — each accepted project gets a directory, README, tasks, and notes
6. **Track provenance** — every subproject links back to the source that inspired it

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **git**

### Setup

```bash
git clone https://github.com/Patvscode/foundry.git
cd foundry

# Install backend + frontend dependencies
make dev-setup

# Start both servers (backend :8121 + frontend :5173)
make dev
```

Open **http://localhost:5173** in your browser.

### Production Mode

```bash
make build    # Build frontend, install backend
cd backend && .venv/bin/uvicorn foundry.main:app --host 127.0.0.1 --port 8120
```

Open **http://localhost:8120** (backend serves the built frontend).

## LLM Provider

Foundry uses an LLM for resource analysis and project discovery. Two modes:

### With Ollama (recommended)

Install [Ollama](https://ollama.com) and pull a model:

```bash
ollama pull qwen3:14b   # or any model you prefer
```

Foundry auto-detects Ollama at `http://localhost:11434`. Configure in `~/.foundry/config.toml`:

```toml
[agent]
default_provider = "ollama"
default_model = "qwen3:14b"
```

### Without Ollama (fallback mode)

If no LLM is available, Foundry uses a **placeholder provider** that:
- Extracts and caches the webpage content normally
- Returns synthetic analysis results (clearly labeled with ⚠ warnings)
- Generates a single "Review this resource" proposal

This lets you explore the full UI and workflow without any LLM setup.

## Configuration

Config lives at `~/.foundry/config.toml` (created on first run). Key settings:

```toml
[server]
host = "127.0.0.1"       # localhost-only by default
port = 8120

[agent]
default_provider = "ollama"    # ollama | none
default_model = ""             # auto-detected if empty

[jobs]
disabled = false               # true to disable background job processing
```

See `backend/foundry/default_config.toml` for all available options.

## Data

All data lives in `~/.foundry/`:
- `foundry.db` — SQLite database (metadata, state, relationships)
- `workspaces/` — project and subproject directories
- `cache/` — cached extracted content
- `logs/` — application logs

## Running Tests

```bash
cd backend
.venv/bin/pytest -v
```

## Tech Stack

- **Backend:** Python / FastAPI / SQLite (WAL) / aiosqlite
- **Frontend:** React 19 / TypeScript / Vite / Tailwind CSS / TanStack Router+Query / Zustand
- **LLM:** Provider-abstracted (Ollama, with fallback)

## Status

🚧 MVP — core product loop works. Not yet ready for general use.

## License

MIT
