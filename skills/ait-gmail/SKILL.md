---
name: ait-gmail
description: Use when users need Gmail operations through ai-toolset CLI, including Google auth, read/list/get/search/thread, send compose/reply/forward, delete/trash/permanent/bulk, and mailbox analysis commands.
---

# AIT Gmail

Use this skill for implementing, fixing, or operating `ait-gmail`.

## Scope

- `packages/ait-gmail/src/ait_gmail/cli.py`
- `packages/ait-gmail/src/ait_gmail/client.py`
- `packages/ait-gmail/src/ait_gmail/commands/*.py`
- `packages/ait-gmail/src/ait_gmail/models.py`
- `packages/ait-gmail/src/ait_gmail/scopes.py`
- `tests/test_gmail/`

## Command Playbook

```bash
ait-gmail auth login
ait-gmail auth login --full
ait-gmail auth status

ait-gmail read list --unread --max 20
ait-gmail read get <message_id>
ait-gmail read search "from:alice@example.com newer_than:7d"
ait-gmail read thread <thread_id>

ait-gmail send compose --to user@example.com --subject "Status" --body "Done"
ait-gmail send reply <message_id> --body "Thanks"
ait-gmail send forward <message_id> --to team@example.com

ait-gmail delete trash <message_id>
ait-gmail delete permanent <message_id> --confirm
ait-gmail delete bulk --query "older_than:365d" --dry-run

ait-gmail analyze summary --days 7
ait-gmail analyze stats --days 30
```

## Guardrails

- Use read scopes by default; require explicit full scopes for write operations.
- Enforce confirmation for destructive actions.
- Keep default output machine-readable (`-o json`).
