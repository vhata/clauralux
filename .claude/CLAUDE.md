# Claude Code Instructions for clauralux

This file contains project-specific instructions for Claude Code when working in this repository.

## Commit Guidelines

### Commit Frequency
- Make small, focused commits regularly rather than large, monolithic commits
- Each commit should represent a single logical change
- Commit after completing each distinct task or fix

### Commit Message Format
Use descriptive commit messages that explain both what changed and why:

```
Short summary (50 chars or less)

More detailed explanation if needed. Wrap at 72 characters.
Explain the problem this commit solves and why this approach was taken.

- Bullet points are fine for listing multiple changes
- Reference issue numbers if applicable (#123)
```

Examples of good commit messages:
- `Add input validation for email field` (not just "fix bug")
- `Refactor user authentication to use JWT tokens` (not just "refactor auth")
- `Optimize database queries in user search` (not just "performance")

### What to Commit
- Always run `make format` and `make check` before committing
- Ensure all tests pass
- Ensure type checking passes (mypy)
- Pre-commit hooks will enforce these automatically

## CHANGELOG.md Maintenance

### When to Update CHANGELOG.md
Update CHANGELOG.md for changes that affect users or developers of this project:

**Always update for:**
- New features or functionality
- Bug fixes
- Breaking changes
- Deprecations
- Security fixes
- Performance improvements
- Dependency updates (major versions)

**Don't update for:**
- Refactoring that doesn't change behavior
- Code formatting
- Documentation typos
- Internal test changes
- Build configuration tweaks

### How to Update CHANGELOG.md
1. Add entries under `## [Unreleased]` section
2. Use the appropriate category:
   - `### Added` - New features
   - `### Changed` - Changes in existing functionality
   - `### Deprecated` - Soon-to-be removed features
   - `### Removed` - Removed features
   - `### Fixed` - Bug fixes
   - `### Security` - Security fixes

3. Write clear, user-focused descriptions
4. Update CHANGELOG.md in the same commit as the change

Example:
```markdown
## [Unreleased]

### Added
- Email validation for user registration form
- Support for Python 3.13

### Fixed
- Handle edge case where empty strings caused crashes in parser
```

## Testing Requirements
- Write tests for new functionality
- Update tests when changing existing functionality
- Aim for >80% code coverage
- Run `make test` before committing

## Code Style
- Follow PEP 8 (enforced by ruff)
- Use type hints for all function signatures (enforced by mypy)
- Write docstrings for public functions and classes
- Keep functions focused and small

## Review Before Committing
Before each commit, verify:
1. [ ] Code is formatted (`make format`)
2. [ ] Linting passes (`make lint`)
3. [ ] Type checking passes (`make type`)
4. [ ] Tests pass (`make test`)
5. [ ] CHANGELOG.md updated if appropriate
6. [ ] Commit message is descriptive
