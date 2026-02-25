---
name: ait-gdrive
description: "Use when users need Google Drive automation through ai-toolset CLI: auth, list/read/search, create file/folder, update content or metadata, delete with confirmation, and storage/duplicate/shared/large-file analysis."
---

# AIT GDrive

Use this skill for `ait-gdrive` operations and code changes.

## Scope

- `packages/ait-gdrive/src/ait_gdrive/cli.py`
- `packages/ait-gdrive/src/ait_gdrive/client.py`
- `packages/ait-gdrive/src/ait_gdrive/commands/*.py`
- `packages/ait-gdrive/src/ait_gdrive/models.py`
- `packages/ait-gdrive/src/ait_gdrive/scopes.py`
- `tests/test_gdrive/`

## Command Playbook

```bash
ait-gdrive auth login
ait-gdrive auth login --full
ait-gdrive auth status

ait-gdrive list "Projects/2026" --max 200
ait-gdrive read "Projects/2026/report.docx" --save-to /tmp/report.docx
ait-gdrive search "quarterly report" --max 50

ait-gdrive create file ./notes.txt --parent "Projects/2026"
ait-gdrive create folder "Drafts" --parent "Projects/2026"
ait-gdrive update "Projects/2026/notes.txt" --file ./notes_v2.txt
ait-gdrive update "Projects/2026/notes.txt" --rename notes-final.txt

ait-gdrive delete "Projects/2026/old.txt" --confirm
ait-gdrive delete <file_id> --permanent --confirm

ait-gdrive analyze storage
ait-gdrive analyze duplicates
ait-gdrive analyze large --top 20 --min-size 10MB
```

## Guardrails

- Accept both ID and path input and keep path resolution deterministic.
- Preserve export behavior for Google-native document types.
