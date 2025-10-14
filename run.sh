#!/bin/bash
set -euo pipefail

export PYTHONUNBUFFERED=1
export UVICORN_PORT=${UVICORN_PORT:-8000}

# Load environment variables from .env if present
if [ -f .env ]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' .env | xargs -d '\n' -I{} echo {})
fi

# Load OpenAI API key from .secrets/openai_api_key if not already set
if [ -z "${OPENAI_API_KEY:-}" ] && [ -f .secrets/openai_api_key ]; then
  export OPENAI_API_KEY="$(cat .secrets/openai_api_key)"
fi

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

uv sync
exec uv run uvicorn app.main:app --host 0.0.0.0 --port "$UVICORN_PORT" --reload

