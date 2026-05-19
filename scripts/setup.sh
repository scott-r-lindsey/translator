#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  cat >&2 <<'EOF'
uv is required to set up this project.

Install uv, then rerun:
  ./scripts/setup.sh
EOF
  exit 1
fi

uv sync --dev
git config core.hooksPath .githooks

printf '%s\n' "Dependencies installed and Git hooks enabled from .githooks"
