---
name: ait-sendgrid
description: Use when users need SendGrid operations in ai-toolset CLI, including API key auth, send email workflows, account lookup, and unsubscribe list retrieval.
---

# AIT SendGrid

Use this skill for `ait-sendgrid` development and operations.

## Scope

- `packages/ait-sendgrid/src/ait_sendgrid/cli.py`
- `packages/ait-sendgrid/src/ait_sendgrid/client.py`
- `packages/ait-sendgrid/src/ait_sendgrid/commands/*.py`
- `packages/ait-sendgrid/src/ait_sendgrid/models.py`
- `tests/test_sendgrid/`

## Command Playbook

```bash
ait-sendgrid auth set-key
ait-sendgrid auth set-key --env
ait-sendgrid auth status

ait-sendgrid send \
  --to user@example.com \
  --subject "Update" \
  --text "Hello" \
  --from me@domain.com

ait-sendgrid send --to user@example.com --subject "HTML" --html-file ./mail.html --from me@domain.com

ait-sendgrid account
ait-sendgrid unsubscribes --limit 20
```

## Guardrails

- Require either explicit `--from` or configured `sendgrid.default_from`.
- Keep output compatible with the shared response envelope.
