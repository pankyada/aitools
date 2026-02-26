---
name: ait-xai
description: Use when users need xAI API operations in ai-toolset CLI, including API key setup/status, chat completions, interactive chat, image generation, and video generation with prompt/file/stdin support.
---

# AIT XAI

Use this skill for implementing and operating `ait-xai`.

## Scope

- `packages/ait-xai/src/ait_xai/cli.py`
- `packages/ait-xai/src/ait_xai/client.py`
- `packages/ait-xai/src/ait_xai/commands/*.py`
- `packages/ait-xai/src/ait_xai/models.py`
- `tests/test_xai/`

## Command Playbook

```bash
ait-xai auth set-key
ait-xai auth set-key --env
ait-xai auth status

ait-xai chat --prompt "Summarize this"
ait-xai chat --stdin --system "Extract action items"
ait-xai chat --prompt-file /tmp/input.txt --json-mode
ait-xai chat --interactive

ait-xai models --type image

ait-xai image "A modern office in morning light" --num 1
ait-xai video "A drone shot over mountains" --duration 8
```

## Guardrails

- Keep prompt-source resolution strict: one of `--prompt`, `--prompt-file`, or `--stdin`.
- Preserve compatibility with tool piping patterns and JSON-first output.
