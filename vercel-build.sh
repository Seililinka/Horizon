#!/usr/bin/env bash
set -euo pipefail
# Run at build time, not in a time-limited HTTP function.
if ! command -v uv >/dev/null 2>&1; then
  python3 -m venv .ailina-build-tools
  .ailina-build-tools/bin/python -m pip install --quiet uv==0.11.26
  export PATH="$PWD/.ailina-build-tools/bin:$PATH"
fi
uv sync --frozen
uv pip install --python .venv/bin/python bleach==6.2.0
uv run --no-sync python -m scripts.ailina_vercel
