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

if [ ! -f .env ] && [ -f .env.dist ]; then
  cp .env.dist .env
  printf '%s\n' "Created .env from .env.dist"
fi

uv sync --dev
./scripts/download-models.sh
git config core.hooksPath .githooks

printf '%s\n' "Dependencies installed, models available, and Git hooks enabled from .githooks"
