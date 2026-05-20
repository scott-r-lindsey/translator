#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

# Runtime can be pinned offline after models are cached, but this script needs
# network access when a configured model is missing.
if [ "${TRANSLATOR_DOWNLOAD_OFFLINE:-false}" != "true" ]; then
  unset HF_HUB_OFFLINE
  unset TRANSFORMERS_OFFLINE
fi

uv run python -m translator.model_cache
