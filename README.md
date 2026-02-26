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

## Install from Releases

Install from GitHub release wheel assets (recommended current path):

```bash
TAG=v0.1.0
REPO=pankyada/aitools
mkdir -p /tmp/aitools

# Download all wheels from a release and install
gh release download "$TAG" -R "$REPO" -p '*.whl' -D /tmp/aitools
uv pip install /tmp/aitools/*.whl
```

Install a single tool wheel:

```bash
TAG=v0.1.0
REPO=pankyada/aitools
mkdir -p /tmp/aitools

gh release download "$TAG" -R "$REPO" -p 'ait_gmail-*.whl' -D /tmp/aitools
uv pip install /tmp/aitools/ait_gmail-*.whl
```

For main-branch prereleases, use tags like `v0.1.0-main-<short-sha>`.

Note: `install.sh` expects standalone binary assets on the GitHub Release page. The current binary workflow uploads build artifacts, so wheel-based install is the reliable release-install path.

## Release Automation

- Every commit pushed to `main` now creates a GitHub prerelease automatically.
- The release tag is `v<version>-main-<short-sha>` and includes built package artifacts and `SHA256SUMS`.
- Tagged releases (`v*`) continue to use `.github/workflows/release.yml` for versioned release flow.

## Versioning Policy

- Starting baseline version is `0.1.0`.
- All workspace packages and the root project use a unified semantic version.
- Adding a new tool package under `packages/` requires a major version bump.
- Adding a new skill under `skills/` requires a major version bump.
- CI enforces this policy via `scripts/check_version_policy.py`.

## Branching Policy

- Do all work in a feature branch (for example, `codex/<task-name>`).
- Merge to `main` only when the change is complete and reviewed.
- `main` is protected to require pull-request-based changes.
