---
name: ait-core
description: Use when working on ai-toolset shared foundations including config loading, output envelope formatting, shared errors/exit codes, token and API key storage, HTTP retry, and Google device-code OAuth internals.
---

# AIT Core

Use this skill when changes touch shared behavior across multiple tools.

## Scope

- `packages/ait-core/src/ait_core/config/settings.py`
- `packages/ait-core/src/ait_core/output/formatter.py`
- `packages/ait-core/src/ait_core/errors.py`
- `packages/ait-core/src/ait_core/auth/google_auth.py`
- `packages/ait-core/src/ait_core/auth/token_store.py`
- `packages/ait-core/src/ait_core/auth/api_key_store.py`
- `packages/ait-core/src/ait_core/http/retry.py`

## Workflow

1. Keep response envelope stable: `success`, `data`, `metadata`, `error`.
2. Preserve `OutputMode` compatibility across `json`, `rich`, and `plain`.
3. Keep exit code semantics aligned with `ExitCode` and `ToolsetError`.
4. For auth/key storage, avoid plaintext persistence and prefer existing encrypted stores.
5. For settings/schema changes, update tests in `tests/test_core/`.

## Fast Checks

```bash
uv run pytest tests/test_core -x
uv run ruff check packages/ait-core tests/test_core
```

## Notes

- Prefer additive, backward-compatible config changes.
- Shared changes should not introduce tool-specific assumptions.
