---
name: ait-memory
description: Use when users need local memory storage and retrieval in ai-toolset CLI, including DB initialization, memory store/get/search, entity operations, stats, forget, and compact workflows with semantic or keyword search.
---

# AIT Memory

Use this skill for offline memory features and fixes.

## Scope

- `packages/ait-memory/src/ait_memory/cli.py`
- `packages/ait-memory/src/ait_memory/db.py`
- `packages/ait-memory/src/ait_memory/embeddings.py`
- `packages/ait-memory/src/ait_memory/entities.py`
- `packages/ait-memory/src/ait_memory/importance.py`
- `packages/ait-memory/src/ait_memory/commands/*.py`
- `tests/test_memory/`

## Command Playbook

```bash
ait-memory init

ait-memory store --text "Project alpha due Friday" --source user
cat /tmp/note.txt | ait-memory store --stdin --source gmail --source-ref msg_123

ait-memory get <memory_id>
ait-memory get --entity "project alpha"
ait-memory get --recent --limit 10

ait-memory search "project alpha deadline" --hybrid
ait-memory search "invoice" --keyword --source gmail --limit 20

ait-memory entities list --sort importance
ait-memory entities get "project alpha"
ait-memory entities relationships "project alpha"

ait-memory stats
ait-memory compact --prune-below 0.1
ait-memory forget <memory_id> --confirm
```

## Guardrails

- Ensure DB is initialized before read/write operations.
- Keep destructive `forget` behind explicit confirmation.
- Preserve search-mode behavior: semantic, keyword, and hybrid.
