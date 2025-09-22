#!/bin/bash
set -euo pipefail

export PYTHONUNBUFFERED=1
export UVICORN_PORT=${UVICORN_PORT:-8000}

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

uv sync
exec uv run uvicorn app.main:app --host 0.0.0.0 --port "$UVICORN_PORT" --reload

