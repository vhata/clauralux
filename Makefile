.PHONY: help sync format lint type test check precommit

help:
	@echo "Available targets:"
	@echo "  sync       - Install/update dependencies"
	@echo "  precommit  - Install pre-commit hooks"
	@echo "  format     - Format code with ruff"
	@echo "  lint       - Lint code with ruff"
	@echo "  type       - Type check with mypy"
	@echo "  test       - Run test suite"
	@echo "  check      - Run all checks (format, lint, type, test)"

sync:
	uv sync --group dev

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
