# AI Toolset

Monorepo for modular CLI tools:

- `ait-core`
- `ait-xai`
- `ait-gmail`
- `ait-gdrive`
- `ait-gcal`
- `ait-memory`
- `ait-resend`
- `ait-sendgrid`
- `ait-social`

## Development

```bash
uv sync --all-packages
uv run ruff check .
uv run pytest tests/
```

## Release Automation

- Every commit pushed to `main` now creates a GitHub prerelease automatically.
- The release tag is `main-<short-sha>` and includes built package artifacts and `SHA256SUMS`.
- Tagged releases (`v*`) continue to use `.github/workflows/release.yml` for versioned release flow.

## Branching Policy

- Do all work in a feature branch (for example, `codex/<task-name>`).
- Merge to `main` only when the change is complete and reviewed.
- `main` is protected to require pull-request-based changes.
