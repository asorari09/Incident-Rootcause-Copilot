#!/bin/sh
set -eu

mkdir -p /app/data/chroma /app/data/outbox

# Free-tier hosts (Render) should skip MiniLM/Chroma boot indexing by default to
# avoid OOM and long cold starts. Opt in with ENABLE_RUNBOOK_INDEX=true.
if [ "${ENABLE_RUNBOOK_INDEX:-false}" = "true" ] && [ ! -f /app/data/chroma/chroma.sqlite3 ]; then
  echo "IR-Copilot: building local runbook index on first boot..."
  if ! python -m ir_copilot.rag.indexer; then
    echo "IR-Copilot: runbook index unavailable; API will start without it." >&2
  fi
else
  echo "IR-Copilot: skipping runbook index at boot (set ENABLE_RUNBOOK_INDEX=true to build)."
fi

# Render and similar platforms inject PORT.
if [ "$#" -eq 0 ] || [ "$1" = "uvicorn" ]; then
  exec uvicorn ir_copilot.main:app --host 0.0.0.0 --port "${PORT:-8000}"
fi

exec "$@"
