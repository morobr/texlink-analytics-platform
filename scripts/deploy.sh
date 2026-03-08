#!/usr/bin/env bash
# ============================================================================
# deploy.sh — Deploy to Railway
# Usage: ./scripts/deploy.sh
# ============================================================================
set -euo pipefail

echo "==> Checking Railway CLI..."
railway --version

echo "==> Current project status:"
railway status

echo "==> Deploying..."
railway up

echo "==> Done. Check https://texlink-analytics-production.up.railway.app"
