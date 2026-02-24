#!/usr/bin/env bash
set -euo pipefail

OWNER_REPO="${AIT_REPO:-<owner>/ai-toolset}"
VERSION="latest"
PREFIX="$HOME/.local/bin"
TOOLS=()

usage() {
  cat <<USAGE
Usage: install.sh [--version vX.Y.Z] [--prefix /path] tool [tool...]

Tools:
  gmail gdrive gcal xai memory resend sendgrid
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      VERSION="$2"
      shift 2
      ;;
    --prefix)
      PREFIX="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      TOOLS+=("$1")
      shift
      ;;
  esac
done

if [[ ${#TOOLS[@]} -eq 0 ]]; then
  usage
  exit 1
fi

OS=$(uname | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
case "$ARCH" in
  x86_64|amd64) ARCH="x86_64" ;;
  arm64|aarch64) ARCH="arm64" ;;
  *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

mkdir -p "$PREFIX"

if [[ "$VERSION" == "latest" ]]; then
  RELEASE_API="https://api.github.com/repos/${OWNER_REPO}/releases/latest"
else
  RELEASE_API="https://api.github.com/repos/${OWNER_REPO}/releases/tags/${VERSION}"
fi

release_json=$(curl -fsSL "$RELEASE_API")

for tool in "${TOOLS[@]}"; do
  case "$tool" in
    gmail) binary="ait-gmail" ;;
    gdrive) binary="ait-gdrive" ;;
    gcal) binary="ait-gcal" ;;
    xai) binary="ait-xai" ;;
    memory) binary="ait-memory" ;;
    resend) binary="ait-resend" ;;
    sendgrid) binary="ait-sendgrid" ;;
    *) echo "Unknown tool: $tool"; exit 1 ;;
  esac

  asset_name="${binary}-${OS}-${ARCH}"
  if [[ "$OS" == "windows" ]]; then
    asset_name+=".exe"
  fi

  url=$(printf '%s' "$release_json" | awk -v n="$asset_name" '
    $0 ~ "\"browser_download_url\"" && $0 ~ n {
      gsub(/[\",]/, "", $2);
      print $2;
      exit
    }
  ')

  if [[ -z "$url" ]]; then
    echo "Asset not found for $asset_name"
    exit 1
  fi

  target="$PREFIX/$binary"
  echo "Downloading $asset_name"
  curl -fsSL "$url" -o "$target"
  chmod +x "$target"
  echo "Installed $target"
done
