.PHONY: install lint typecheck test run demo clean help

# Default target
.DEFAULT_GOAL := help

# Poetry executable
POETRY := poetry

# Python executable via Poetry
PYTHON := $(POETRY) run python

# CLI executable
MTM := $(POETRY) run mtm

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)=== Meeting-to-Modules Makefile ===$(NC)"
	@echo ""
	@echo "Available targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""

install: ## Install dependencies using Poetry
	@echo "$(YELLOW)Installing dependencies...$(NC)"
	$(POETRY) install
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

lint: ## Run linting with Ruff
	@echo "$(YELLOW)Running linter...$(NC)"
	$(POETRY) run ruff check .
	@echo "$(GREEN)✓ Linting complete$(NC)"

lint-fix: ## Run linting with Ruff and auto-fix
	@echo "$(YELLOW)Running linter with auto-fix...$(NC)"
	$(POETRY) run ruff check --fix .
	@echo "$(GREEN)✓ Linting complete$(NC)"

format: ## Format code with Ruff
	@echo "$(YELLOW)Formatting code...$(NC)"
	$(POETRY) run ruff format .
	@echo "$(GREEN)✓ Code formatted$(NC)"

format-check: ## Check code formatting with Ruff
	@echo "$(YELLOW)Checking code formatting...$(NC)"
	$(POETRY) run ruff format --check .
	@echo "$(GREEN)✓ Format check complete$(NC)"

typecheck: ## Run type checking with MyPy
	@echo "$(YELLOW)Running type checker...$(NC)"
	$(POETRY) run mypy src/mtm
	@echo "$(GREEN)✓ Type checking complete$(NC)"

test: ## Run tests with pytest
	@echo "$(YELLOW)Running tests...$(NC)"
	$(POETRY) run pytest -v
	@echo "$(GREEN)✓ Tests complete$(NC)"

test-cov: ## Run tests with coverage
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	$(POETRY) run pytest --cov=src/mtm --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Tests with coverage complete$(NC)"
	@echo "$(BLUE)Coverage report: htmlcov/index.html$(NC)"

test-integration: ## Run integration tests
	@echo "$(YELLOW)Running integration tests...$(NC)"
	$(POETRY) run pytest tests/integration/ -v
	@echo "$(GREEN)✓ Integration tests complete$(NC)"

test-unit: ## Run unit tests
	@echo "$(YELLOW)Running unit tests...$(NC)"
	$(POETRY) run pytest tests/unit/ -v
	@echo "$(GREEN)✓ Unit tests complete$(NC)"

run: ## Run the CLI (shows help)
	@echo "$(YELLOW)Running MTM CLI...$(NC)"
	$(MTM) --help

demo: ## Run demo script and verify
	@echo "$(BLUE)=== Running Demo ===$(NC)"
	@echo ""
	@if [ ! -f scripts/demo.sh ]; then \
		echo "$(YELLOW)Error: scripts/demo.sh not found$(NC)"; \
		exit 1; \
	fi
	@chmod +x scripts/demo.sh 2>/dev/null || true
	@bash scripts/demo.sh
	@echo ""
	@echo "$(BLUE)=== Running Verification ===$(NC)"
	@echo ""
	$(MTM) verify
	@echo ""
	@echo "$(GREEN)=== Demo Complete ===$(NC)"

clean: ## Clean generated files and caches
	@echo "$(YELLOW)Cleaning generated files...$(NC)"
	@rm -rf outputs/*
	@rm -rf .pytest_cache
	@rm -rf .mypy_cache
	@rm -rf .ruff_cache
	@rm -rf htmlcov
	@rm -rf .coverage
	@rm -rf coverage.xml
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Clean complete$(NC)"

clean-all: clean ## Clean everything including database and logs
	@echo "$(YELLOW)Cleaning database and logs...$(NC)"
	@rm -rf outputs/mtm.db
	@rm -rf outputs/logs/*
	@echo "$(GREEN)✓ Deep clean complete$(NC)"

ci: lint format-check typecheck test ## Run all CI checks (lint, format, typecheck, test)
	@echo "$(GREEN)✓ All CI checks passed$(NC)"

pre-commit: lint-fix format typecheck ## Run pre-commit checks (lint-fix, format, typecheck)
	@echo "$(GREEN)✓ Pre-commit checks complete$(NC)"

