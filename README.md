# clauralux

A Python project bootstrapped with modern tooling:

- **uv** - Fast dependency and environment management
- **pytest** - Testing framework with coverage
- **ruff** - Lightning-fast linting and formatting
- **mypy** - Static type checking
- **pre-commit** - Automated checks before commits
- **GitHub Actions** - Continuous integration

## Prerequisites

- Python 3.12+
- uv (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`)

## Quickstart

```bash
# Create virtual environment and install dependencies
uv venv .venv
uv sync --group dev

# Install pre-commit hooks
uv run pre-commit install

# Run all checks
make check
```

## Development

### Common Commands

```bash
make format     # Auto-format code with ruff
make lint       # Run ruff linter
make type       # Type check with mypy
make test       # Run test suite
make check      # Run all checks (CI equivalent)
```

### Running Tests

```bash
# Run all tests with coverage
uv run pytest

# Run specific test file
uv run pytest tests/test_core.py

# Run with verbose output
uv run pytest -v
```

## Project Structure

```
src/clauralux/          # Source code
tests/                  # Test files
.github/workflows/      # CI configuration
.claude/                # Claude Code configuration
```

## Working with Claude Code

This repository includes a `.claude/CLAUDE.md` file with project-specific instructions for Claude Code, including:
- Commit message guidelines
- When to update CHANGELOG.md
- Testing requirements
- Code style preferences

## License

MIT - see LICENSE file for details
