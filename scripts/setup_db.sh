#!/usr/bin/env bash
# ============================================================================
# setup_db.sh — Initialize Texlink Analytics database
# Usage: ./scripts/setup_db.sh
# ============================================================================
set -euo pipefail

echo "==> Loading environment variables..."
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo "==> Creating schema..."
psql "$DATABASE_URL" -f src/database/schema.sql

echo "==> Creating indexes..."
psql "$DATABASE_URL" -f src/database/indexes.sql

echo "==> Creating functions and triggers..."
psql "$DATABASE_URL" -f src/database/functions.sql

echo "==> Loading seed data..."
python -m src.seeds.seed_loader

echo "==> Running analytics models..."
python -m src.models.run_all

echo "==> Done. Database is ready."
