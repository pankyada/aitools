---
name: ait-resend
description: Use when users need Resend email operations in ai-toolset CLI, including API key auth, sending transactional emails with text/html bodies, listing sent emails, and fetching email details.
---

# AIT Resend

Use this skill for `ait-resend` implementation and usage.

## Scope

- `packages/ait-resend/src/ait_resend/cli.py`
- `packages/ait-resend/src/ait_resend/client.py`
- `packages/ait-resend/src/ait_resend/commands/*.py`
- `packages/ait-resend/src/ait_resend/models.py`
- `tests/test_resend/`

## Command Playbook

```bash
ait-resend auth set-key
ait-resend auth set-key --env
ait-resend auth status

ait-resend send \
  --to user@example.com \
  --subject "Status" \
  --text "Build is complete" \
  --from me@domain.com

ait-resend send --to user@example.com --subject "HTML" --html-file ./mail.html --from me@domain.com

ait-resend list --limit 20
ait-resend get <email_id>
```

## Guardrails

- Require either explicit `--from` or configured `resend.default_from`.
- Validate body inputs so empty content is rejected.
