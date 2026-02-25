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
