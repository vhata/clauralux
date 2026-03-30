.PHONY: help run sync format lint type test check precommit build-rust

help:
	@echo "Available targets:"
	@echo "  run        - Launch Clauralux (pass ARGS for subcommands)"
	@echo "  sync       - Install/update dependencies"
	@echo "  build-rust - Build Rust engine extension"
	@echo "  precommit  - Install pre-commit hooks"
	@echo "  format     - Format code with ruff"
	@echo "  lint       - Lint code with ruff"
	@echo "  type       - Type check with mypy"
	@echo "  test       - Run test suite"
	@echo "  check      - Run all checks (format, lint, type, test)"

# Usage: make run  OR  make run ARGS="train --neural --from-scratch"
run:
	uv run clauralux $(ARGS)

sync:
	uv sync --group dev

build-rust:
	uv run maturin develop --release

precommit:
	uv run pre-commit install

format:
	uv run ruff format .

lint:
	uv run ruff check .

type:
	uv run mypy .

test:
	uv run pytest

check:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy .
	uv run pytest
