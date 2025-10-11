# 24 Hours of Lemons - Makefile (Docker-Only Development)
# All development happens in Docker containers matching Pi environment

.PHONY: help build dev shell test test-unit test-integration test-sim \
        run-drs run-telemetry format lint clean clean-all \
        deploy check-pi logs create-image flash-spare verify-spare

# Docker compose command
DC = docker-compose

# Docker run command for one-off tasks
DR = $(DC) run --rm dev

# Default target
help:
	@echo "🏁 24 Hours of Lemons - Available Commands"
	@echo ""
	@echo "🐳 Docker Development (REQUIRED):"
	@echo "  make build                Build Docker dev environment"
	@echo "  make dev                  Start development container (interactive)"
	@echo "  make shell                Same as 'make dev'"
	@echo ""
	@echo "🧪 Testing (in Docker):"
	@echo "  make test                 Run all tests"
	@echo "  make test-unit            Run unit tests only"
	@echo "  make test-sim             Run simulation tests only"
	@echo ""
	@echo "🎮 Run Apps (in Docker, dry-run mode):"
	@echo "  make run-drs              Run DRS app"
	@echo "  make run-telemetry        Run telemetry app"
	@echo ""
	@echo "✨ Code Quality (in Docker):"
	@echo "  make format               Format code with black"
	@echo "  make lint                 Lint code with ruff"
	@echo ""
	@echo "🚀 Trackside Deployment (to real Pi):"
	@echo "  make deploy HOST=<ip> CAR=<car>    Deploy to remote Pi"
	@echo "  make check-pi HOST=<ip>            Verify Pi is ready"
	@echo "  make logs HOST=<ip> APP=<app>      View remote logs"
	@echo ""
	@echo "💾 Golden Image (Spare SD Cards):"
	@echo "  make create-image          Backup current Pi to golden image"
	@echo "  make flash-spare SD=/dev/sdX    Flash golden image to SD card"
	@echo "  make verify-spare HOST=<ip>     Test spare SD card"
	@echo ""
	@echo "🧹 Cleanup:"
	@echo "  make clean                 Clean build artifacts"
	@echo "  make clean-all             Clean everything including Docker"

# ============================================================================
# Docker Setup
# ============================================================================

build:
	@echo "🐳 Building Docker development environment..."
	$(DC) build

dev: build
	@echo "🐳 Starting development container..."
	@echo "💡 You're now in a container matching the Pi environment"
	@echo "💡 Code changes sync automatically"
	@echo "💡 Exit with 'exit' or Ctrl+D"
	@echo ""
	$(DC) run --rm dev

shell: dev

# ============================================================================
# Testing (All in Docker)
# ============================================================================

test: build
	@echo "🧪 Running all tests in Docker..."
	$(DR) pytest -v

test-unit: build
	@echo "🧪 Running unit tests in Docker..."
	$(DR) pytest tests/unit/ -v

test-integration: build
	@echo "🧪 Running integration tests in Docker..."
	$(DR) pytest tests/integration/ -v

test-sim: build
	@echo "🏎️  Running live lap simulation in Docker..."
	@echo "📊 Dashboard will be at http://localhost:5000"
	@echo "🔧 DRS API will be at http://localhost:5001"
	@echo ""
	$(DC) run --rm --service-ports dev pytest tests/simulation/test_lap_simulation_live.py -v -s

# ============================================================================
# Run Apps (Dry-Run Mode in Docker)
# ============================================================================

run-drs: build
	@echo "🎮 Running DRS app in Docker (dry-run mode)..."
	@echo "💡 API will be at http://localhost:5001"
	@echo "💡 Press Ctrl+C to stop"
	@echo ""
	$(DC) run --rm --service-ports dev python -m apps.drs.main --dry-run

run-telemetry: build
	@echo "📊 Running telemetry app in Docker (dry-run mode)..."
	@echo "💡 Dashboard will be at http://localhost:5000"
	@echo "💡 Press Ctrl+C to stop"
	@echo ""
	$(DC) run --rm --service-ports dev python -m apps.telemetry.main --dry-run

# ============================================================================
# Code Quality (in Docker)
# ============================================================================

format: build
	@echo "✨ Formatting code in Docker..."
	$(DR) black apps/ libs/ tests/

lint: build
	@echo "🔍 Linting code in Docker..."
	$(DR) ruff check apps/ libs/ tests/

# ============================================================================
# Cleanup
# ============================================================================

clean:
	@echo "🧹 Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf htmlcov/ .coverage reports/ 2>/dev/null || true
	@echo "✅ Cleanup complete"

clean-all: clean
	@echo "🧹 Removing Docker containers and images..."
	$(DC) down -v
	docker rmi 24-hours-of-lemons-systems_dev 2>/dev/null || true
	@echo "✅ Full cleanup complete"

# ============================================================================
# Trackside Deployment Commands
# ============================================================================

deploy:
	@if [ -z "$(HOST)" ]; then \
		echo "❌ Error: HOST not specified"; \
		echo "Usage: make deploy HOST=192.168.1.100 CAR=car1"; \
		exit 1; \
	fi
	@if [ -z "$(CAR)" ]; then \
		echo "❌ Error: CAR not specified"; \
		echo "Usage: make deploy HOST=192.168.1.100 CAR=car1"; \
		exit 1; \
	fi
	@echo "🚀 Deploying to $(HOST) with CAR_ID=$(CAR)..."
	bash scripts/remote-deploy.sh $(HOST) $(CAR)

check-pi:
	@if [ -z "$(HOST)" ]; then \
		echo "❌ Error: HOST not specified"; \
		echo "Usage: make check-pi HOST=192.168.1.100"; \
		exit 1; \
	fi
	@echo "🔍 Checking Pi at $(HOST)..."
	bash scripts/check-pi.sh $(HOST)

logs:
	@if [ -z "$(HOST)" ]; then \
		echo "❌ Error: HOST not specified"; \
		echo "Usage: make logs HOST=192.168.1.100 APP=drs"; \
		exit 1; \
	fi
	@if [ -z "$(APP)" ]; then \
		echo "❌ Error: APP not specified"; \
		echo "Usage: make logs HOST=192.168.1.100 APP=drs"; \
		echo "Available apps: drs, telemetry"; \
		exit 1; \
	fi
	@echo "📜 Fetching logs from $(HOST) for $(APP)..."
	ssh pi@$(HOST) "journalctl -u lemons@$(APP) -n 50 --no-pager"

# ============================================================================
# Golden Image Commands
# ============================================================================

create-image:
	@echo "💾 Creating golden image from running Pi..."
	@echo "This will create: golden-images/lemons-$(shell date +%Y%m%d-%H%M%S).img"
	bash scripts/create-image.sh

flash-spare:
	@if [ -z "$(SD)" ]; then \
		echo "❌ Error: SD device not specified"; \
		echo "Usage: make flash-spare SD=/dev/sdX"; \
		echo ""; \
		echo "⚠️  WARNING: This will ERASE the SD card!"; \
		echo "Find your SD card with: lsblk or diskutil list (macOS)"; \
		exit 1; \
	fi
	@echo "⚠️  WARNING: About to write golden image to $(SD)"
	@echo "This will ERASE all data on $(SD)!"
	@read -p "Continue? (yes/no): " confirm && [ "$$confirm" = "yes" ] || exit 1
	bash scripts/flash-image.sh $(SD)

verify-spare:
	@if [ -z "$(HOST)" ]; then \
		echo "❌ Error: HOST not specified"; \
		echo "Usage: make verify-spare HOST=192.168.1.100"; \
		exit 1; \
	fi
	@echo "✅ Verifying spare SD card at $(HOST)..."
	bash scripts/check-pi.sh $(HOST) verify
