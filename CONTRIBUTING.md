# Contributing to PLEIADES

Thanks for helping improve PLEIADES! This guide covers how to propose changes, report issues, and submit pull requests.

## How to contribute
- **Always start with an issue:** Search existing issues; if none, open a new one describing the problem/idea and expected outcome.
- **Branches come from issues:** Create a feature/fix branch only after an issue exists. Include the issue number in the branch name (e.g., `123-fix-login`) and link the issue in the PR.
- **Bugs:** Provide reproduction steps, expected vs. actual behavior, logs, and environment details.
- **Features:** Discuss scope/design in the issue before coding.
- **Documentation:** For docs in `README.rst`/`docs/`, prefer reStructuredText; small fixes via PR are welcome.

## Development environment
- Preferred: use **pixi** (ensures a consistent, isolated env without manual venvs).
  - Install pixi: `curl -fsSL https://pixi.sh/install.sh | bash`
  - Install project env: `pixi install`
  - Activate (shell): `pixi shell`
  - Run tools via pixi: `pixi run <task>` (e.g., `pixi run test`)
- If pixi is unavailable, you may use a Python virtual environment:
  `python -m venv .venv && source .venv/bin/activate && pip install -e .[dev]`
- Use the Python version(s) specified in `pyproject.toml`/`environment` settings for this project.

## Development workflow
1. Create/confirm an issue for your change.
2. Branch from the default branch after the issue is filed: `git checkout -b <issue>-short-title`.
3. Keep changes focused; add tests/docs for behavior changes.
4. Run formatters/linters and the full test suite locally before opening a PR.
5. Rebase on `main` (or the default branch) before requesting review.

## Code style & quality
- Match existing style and patterns.
- Format and lint (adjust to repo conventions):
  - Python: `pixi run fmt` / `pixi run lint` (or `ruff format . && ruff check .` if no tasks defined).
  - Type checking (if applicable): `pixi run typecheck` (or `mypy .`).
- Tests: `pixi run test` (or `pytest` if no task).
- Add/adjust tests for new or changed behavior; avoid reducing coverage.

## Commits & PRs
- Commits: small, clear, and descriptive (e.g., `fix: handle empty input`).
- PR description: what changed, why, how it was tested, and any follow-ups.
- Link related issues (e.g., `Closes #123`). Note breaking changes clearly.

## Security
- Don’t open public issues for security concerns. Email the maintainers directly with security concerns.

## Code of Conduct
- Please follow the project’s Code of Conduct (see `CODE_OF_CONDUCT.md` if available).
