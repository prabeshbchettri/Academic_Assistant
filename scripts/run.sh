#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

if ! command -v uv &> /dev/null; then
    echo "uv is required but not installed. Please install uv (https://github.com/astral-sh/uv)."
    exit 1
fi

echo "Launching Academic Assistant Desktop Application..."
uv run python -m app.main "$@"
