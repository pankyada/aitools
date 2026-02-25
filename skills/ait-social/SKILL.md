---
name: ait-social
description: Use when users need social publishing workflows in ai-toolset CLI across instagram, facebook, twitter, linkedin, and tiktok, including token setup/status, profile lookup, and post creation.
---

# AIT Social

Use this skill for `ait-social` provider integrations and command flows.

## Scope

- `packages/ait-social/src/ait_social/cli.py`
- `packages/ait-social/src/ait_social/commands.py`
- `packages/ait-social/src/ait_social/provider_factory.py`
- `packages/ait-social/src/ait_social/providers/*.py`
- `packages/ait-social/src/ait_social/models.py`
- `tests/test_social/`

## Command Playbook

```bash
ait-social platforms list

ait-social auth set-token --platform twitter
ait-social auth set-token --platform linkedin --env
ait-social auth status
ait-social auth status --platform instagram

ait-social profile get --platform twitter
ait-social profile get --platform facebook --account-id <page_id>

ait-social post create --platform twitter --text "Shipping v1 today"
ait-social post create --platform linkedin --text "Release update" --visibility PUBLIC
ait-social post create --platform instagram --account-id <ig_id> --media-url https://... --text "Caption"
```

## Guardrails

- Keep provider-specific fields in `--extra-json` and validate JSON object shape.
- Maintain normalized errors from provider adapters.
