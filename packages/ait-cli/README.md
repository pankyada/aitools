# ait-cli

Unified umbrella CLI for the AI Toolset monorepo.

## Overview

`ait` is the single entry-point that ties together all tool packages
(`ait-gmail`, `ait-gdrive`, `ait-gcal`, `ait-xai`, `ait-memory`,
`ait-resend`, `ait-sendgrid`, `ait-social`, `ait-stripe`) into one
cohesive command-line interface.

Tool sub-commands are discovered at runtime via the `ait.tools` entry-point
group, so installing any `ait-*` package automatically makes its commands
available under `ait <tool> <command>`.

## Installation

```bash
# Install the full toolset
pip install ai-toolset

# Or install just the tools you need alongside ait-cli
pip install ait-cli ait-gmail ait-gdrive
```

## Usage

```
ait --help           # top-level help
ait init             # interactive first-run setup wizard
ait auth status      # show auth status for all configured tools
ait doctor           # run diagnostics
ait tools            # list discovered tool sub-commands

ait gmail list       # Gmail sub-commands (if ait-gmail installed)
ait gdrive ls        # Google Drive sub-commands (if ait-gdrive installed)
# … etc.
```

## Commands

| Command | Description |
|---|---|
| `ait init` | Interactive wizard to configure API keys and OAuth credentials |
| `ait auth status` | Dashboard showing auth status for every tool |
| `ait doctor` | Checks Python version, installed packages, API keys, and connectivity |
| `ait tools` | Lists all currently registered tool sub-commands |
| `ait --version` | Print the installed `ait-cli` version |
