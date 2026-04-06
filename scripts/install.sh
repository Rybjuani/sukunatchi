#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${HOME}/.local/bin"
TARGET_PATH="${TARGET_DIR}/sukunatchi"

mkdir -p "$TARGET_DIR"
ln -sfn "${ROOT_DIR}/run.sh" "$TARGET_PATH"

echo "Installed: ${TARGET_PATH}"
