#!/usr/bin/env bash
# ============================================================================
# run_models.sh — Execute all analytics SQL models
# Usage: ./scripts/run_models.sh
# ============================================================================
set -euo pipefail

echo "==> Loading environment variables..."
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo "==> Running staging + intermediate + mart models..."
python -m src.models.run_all

echo "==> Done. All views created."
