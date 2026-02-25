#!/usr/bin/env bash
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required"
  exit 1
fi

for pkg in packages/ait-core packages/ait-xai packages/ait-gmail packages/ait-gdrive packages/ait-gcal packages/ait-memory packages/ait-resend packages/ait-sendgrid packages/ait-social; do
  echo "Building ${pkg}"
  (cd "$pkg" && uv build)
done
