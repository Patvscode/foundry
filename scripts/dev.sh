#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Check prerequisites
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3.11+ is required"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js 18+ is required"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "❌ git is required"; exit 1; }

# Check venv exists
if [ ! -d "backend/.venv" ]; then
    echo "❌ Backend venv not found. Run 'make dev-setup' first."
    exit 1
fi

if [ ! -d "frontend/node_modules" ]; then
    echo "❌ Frontend deps not found. Run 'make dev-setup' first."
    exit 1
fi

echo "⚡ Starting Foundry dev environment..."
echo "   Backend:  http://127.0.0.1:8121"
echo "   Frontend: http://localhost:5173"
echo ""

# Start backend and frontend in parallel
trap 'kill 0' EXIT
cd backend && .venv/bin/uvicorn foundry.main:app --host 127.0.0.1 --port 8121 --reload &
cd frontend && npm run dev &
wait
