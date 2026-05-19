#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."
uv run pytest \
  --cov=translator \
  --cov-report=term-missing \
  --cov-report=html:htmlcov

printf '\nCoverage HTML report: file://%s/htmlcov/index.html\n' "$(pwd)"
