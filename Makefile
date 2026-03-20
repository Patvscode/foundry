.PHONY: dev dev-setup dev-backend dev-frontend build install test lint clean

# Development
dev-setup: backend-setup frontend-setup
	@echo "✅ Dev environment ready. Run 'make dev' to start."

dev:
	@bash scripts/dev.sh

dev-backend:
	cd backend && .venv/bin/uvicorn foundry.main:app --host 127.0.0.1 --port 8121 --reload

dev-frontend:
	cd frontend && npm run dev

# Setup
backend-setup:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

frontend-setup:
	cd frontend && npm install

# Production
build: backend-build frontend-build
	@echo "✅ Production build complete."

backend-build:
	cd backend && .venv/bin/pip install -e ".[all]"

frontend-build:
	cd frontend && npm ci && npm run build

install: build
	@mkdir -p ~/.foundry
	@if [ ! -f ~/.foundry/config.toml ]; then \
		cp backend/foundry/default_config.toml ~/.foundry/config.toml; \
		chmod 600 ~/.foundry/config.toml; \
		echo "📄 Created ~/.foundry/config.toml"; \
	fi
	@echo "✅ Foundry installed. Run: cd backend && .venv/bin/foundry start"

# Test & Lint
test:
	cd backend && .venv/bin/pytest -v

lint:
	cd backend && .venv/bin/ruff check foundry/
	cd frontend && npm run lint

# Clean
clean:
	rm -rf backend/.venv backend/*.egg-info
	rm -rf frontend/node_modules frontend/dist
	@echo "🧹 Cleaned build artifacts."
