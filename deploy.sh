#!/usr/bin/env bash
# PropEdge AI — Railway deploy script
# Run after: railway login
#
# Usage: bash deploy.sh [backend|frontend|all]
#   bash deploy.sh           → deploys both
#   bash deploy.sh backend   → deploys backend only
#   bash deploy.sh frontend  → deploys frontend only

set -euo pipefail

BACKEND_SERVICE="7fbd4bd6-8647-4e0f-9d6e-94a6ebf1872f"
FRONTEND_SERVICE="8d0a446e-abfc-4a2a-9fa3-5d1e881d8628"
PROJECT_ID="5e577c4f-10a9-4cdf-9be2-dd1327049b95"
ENVIRONMENT_ID="ce0e364c-4d61-4348-901d-4511eb2c2112"
BACKEND_URL="https://backend-production-fe8e6.up.railway.app"

DEPLOY_TARGET="${1:-all}"

export RAILWAY_PROJECT_ID="$PROJECT_ID"
export RAILWAY_ENVIRONMENT_ID="$ENVIRONMENT_ID"

# ── Helpers ────────────────────────────────────────────────────────────────────

green()  { echo -e "\033[32m$*\033[0m"; }
yellow() { echo -e "\033[33m$*\033[0m"; }
red()    { echo -e "\033[31m$*\033[0m"; }

check_auth() {
  if ! railway whoami &>/dev/null; then
    red "❌  Not authenticated. Run: railway login"
    exit 1
  fi
  green "✓  Railway auth OK ($(railway whoami))"
}

deploy_backend() {
  yellow "→  Deploying backend..."
  railway up --service "$BACKEND_SERVICE" --detach --dir backend
  green "✓  Backend deploy queued"
}

deploy_frontend() {
  yellow "→  Deploying frontend..."
  railway up --service "$FRONTEND_SERVICE" --detach --dir frontend
  green "✓  Frontend deploy queued"
}

trigger_refresh() {
  yellow "→  Waiting 45s for services to start, then triggering data refresh..."
  sleep 45
  if curl -sf -X POST "$BACKEND_URL/api/v1/props/refresh" > /dev/null; then
    green "✓  Data refresh triggered"
  else
    yellow "⚠  Refresh trigger failed (service may still be starting)"
  fi
}

# ── Main ───────────────────────────────────────────────────────────────────────

check_auth

case "$DEPLOY_TARGET" in
  backend)
    deploy_backend
    trigger_refresh
    ;;
  frontend)
    deploy_frontend
    ;;
  all|*)
    deploy_backend
    deploy_frontend
    trigger_refresh
    ;;
esac

green ""
green "✅  Deploy complete!"
green "   Frontend: https://frontend-production-299a.up.railway.app"
green "   Backend:  $BACKEND_URL"
green "   API docs: $BACKEND_URL/docs"
green ""
yellow "Run 'railway logs --service $BACKEND_SERVICE' to watch backend logs"
