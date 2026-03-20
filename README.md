# Foundry

Research-to-projects workspace. Feed it URLs, papers, repos, and videos → extracts buildable projects → organizes into workspaces with tasks, notes, provenance, and agent assist.

## What It Does

- **Ingest** resources: webpages, PDFs, YouTube videos
- **Analyze** content using local LLMs (Ollama, llama.cpp) or API providers
- **Discover** buildable projects, components, and systems from research
- **Organize** into subproject workspaces with tasks, notes, and provenance
- **Execute** bounded shell commands in workspace context (install, test, build)
- **Search** across everything with full-text search (Cmd+K)
- **Chat** with a context-aware agent about projects and resources

## Quick Start

```bash
# Clone
git clone https://github.com/Patvscode/foundry.git
cd foundry

# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Frontend
cd ../frontend
npm install
npm run build

# Setup (creates config, checks deps)
cd ../backend
python -m foundry.cli setup

# Start
python -m foundry.cli start --foreground
# Or: ./dev.sh for development mode with hot reload

# Open: http://localhost:8120
```

## Configuration

Config file: `~/.foundry/config.toml` (created by `foundry setup`)

### Local Model Setup

Foundry works best with a local LLM. Options:

**Ollama (recommended for most setups):**
```bash
ollama serve                    # Start Ollama
ollama pull qwen3.5:4b          # Pull a model
```
Then in `~/.foundry/config.toml`:
```toml
[agent]
default_provider = "ollama"
default_model = "qwen3.5:4b"
```

**llama.cpp (for larger models):**
If you have a llama.cpp server running on port 18080, Foundry detects it automatically.

**API providers:**
```toml
[agent]
default_provider = "openai"

[agent.providers.openai]
api_key = "sk-..."
```

**Fallback mode (no model needed):**
```toml
[agent]
default_provider = "none"
```
Uses synthetic placeholders — you can still create projects, add resources, and organize manually.

### Check Provider Status

```bash
python -m foundry.cli providers   # Show available providers
python -m foundry.cli doctor      # Full system check
```

Or in the UI: Settings → LLM Providers

## Shell / Build / Test / Install

Foundry supports bounded execution inside subproject workspaces:

| Action | What it does |
|--------|-------------|
| `install` | Runs ecosystem-appropriate install (pip/npm/cargo) |
| `test` | Runs ecosystem-appropriate tests (pytest/npm test) |
| `build` | Runs ecosystem-appropriate build |
| `shell` | Custom command (user-specified) |

**Safety boundaries:**
- Execution is **disabled by default** — set `agent.can_execute = true` in config
- Commands run **only inside subproject workspace directories**
- All executions are **logged** with full stdout/stderr
- **Timeout enforced** (default 60s, max 300s)
- No background/daemon processes
- No access outside the workspace directory

Enable in config:
```toml
[agent]
can_execute = true
```

## Search

- **Cmd+K** (or Ctrl+K) opens the command palette
- Searches across: projects, resources, subprojects, tasks, notes
- Quick actions: navigate, create project

## Architecture

```
foundry/
├── backend/          # FastAPI + Python 3.11+
│   └── foundry/
│       ├── api/      # REST endpoints
│       ├── ingestion/# Pipeline, handlers (webpage/PDF/YouTube), coordinator
│       ├── execution/# Workspace-scoped shell execution
│       ├── search/   # FTS5 search engine
│       ├── agents/   # LLM provider abstraction
│       ├── storage/  # SQLite + migrations
│       └── workspace/# Filesystem management
└── frontend/         # React 19 + Vite + TypeScript + Tailwind
```

## Ingestion Pipeline

Resources go through: **extract → analyze → discover**

- **Webpage:** trafilatura text extraction
- **PDF:** pypdfium2 text extraction (local + remote)
- **YouTube:** yt-dlp metadata + VTT transcript

Optional **coordinated mode** (bounded multi-worker, disabled by default):
```bash
FOUNDRY_INGESTION_COORDINATED=1 python -m foundry.cli start --foreground
```

Single-model sequential path always works as fallback.

## Startup / Shutdown

```bash
# Start (foreground)
python -m foundry.cli start --foreground

# Start (background)
python -m foundry.cli start

# Stop
python -m foundry.cli stop

# Status
python -m foundry.cli status

# Health check
python -m foundry.cli health
```

**Access:** By default binds to `127.0.0.1:8120` (local only).
To expose on your network (e.g., Tailscale): set `server.host = "0.0.0.0"` in config.

## Running Tests

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/ -v
```

## Limitations

- **Image-only PDFs** are not supported (no OCR yet)
- **YouTube private/restricted videos** may fail
- **Search index** rebuilds on startup — not incrementally updated for all entity types yet
- **Execution** is intentionally restricted to workspace directories
- **No authentication** — designed for local/trusted-network use
- **No mobile layout** yet

## License

MIT
