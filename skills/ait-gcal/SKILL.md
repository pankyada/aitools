---
name: ait-gcal
description: Use when users need Google Calendar workflows through ai-toolset CLI, including auth, calendar listing, and event list/get/create/delete with RFC3339 time handling and confirmation for destructive actions.
---

# AIT GCal

Use this skill for `ait-gcal` features and maintenance.

## Scope

- `packages/ait-gcal/src/ait_gcal/cli.py`
- `packages/ait-gcal/src/ait_gcal/client.py`
- `packages/ait-gcal/src/ait_gcal/commands/*.py`
- `packages/ait-gcal/src/ait_gcal/models.py`
- `packages/ait-gcal/src/ait_gcal/scopes.py`
- `tests/test_gcal/`

## Command Playbook

```bash
ait-gcal auth login
ait-gcal auth login --full
ait-gcal auth status

ait-gcal calendars list --max 100

ait-gcal events list --calendar primary --max 20
ait-gcal events list --from "2026-03-01T00:00:00Z" --to "2026-03-31T23:59:59Z"
ait-gcal events get <event_id> --calendar primary

ait-gcal events create \
  --summary "Team Sync" \
  --start "2026-03-01T09:00:00Z" \
  --end "2026-03-01T09:30:00Z" \
  --calendar primary

ait-gcal events delete <event_id> --calendar primary --confirm
```

## Guardrails

- Parse and validate RFC3339 datetime values before API calls.
- Require `--confirm` for delete flows.
