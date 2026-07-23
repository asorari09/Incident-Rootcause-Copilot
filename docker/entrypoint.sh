#!/bin/sh
set -eu

mkdir -p /app/data/chroma /app/data/outbox

if [ ! -f /app/data/chroma/chroma.sqlite3 ]; then
  echo "IR-Copilot: building local runbook index on first boot..."
  if ! python -m ir_copilot.rag.indexer; then
    echo "IR-Copilot: runbook index unavailable; API will start and retry can be run later." >&2
  fi
fi

exec "$@"
