#!/usr/bin/env bash
# Fast local bring-up for Strava MCP Connector (HTTP + OAuth).
# Loads .env, starts streamable-http MCP, prints URLs + callback reminder.
# Usage: from server/ → ./scripts/dev_up.sh
#        or: /workspace/strava-mcp-connector/server/scripts/dev_up.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_DIR="$(cd "${SERVER_DIR}/.." && pwd)"
cd "${SERVER_DIR}"

ENV_FILE=""
if [[ -f "${SERVER_DIR}/.env" ]]; then
  ENV_FILE="${SERVER_DIR}/.env"
elif [[ -f "${HOME}/.strava-mcp-connector.env" ]]; then
  ENV_FILE="${HOME}/.strava-mcp-connector.env"
elif [[ -f "${REPO_DIR}/.env.example" ]]; then
  echo "No .env found. Copy the template first:"
  echo "  cp ${REPO_DIR}/.env.example ${SERVER_DIR}/.env"
  echo "  # then set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET (never commit)"
  exit 1
else
  echo "No .env or .env.example found under ${REPO_DIR}"
  exit 1
fi

# shellcheck disable=SC1090
set -a
# shellcheck source=/dev/null
source "${ENV_FILE}"
set +a

HOST="${STRAVA_MCP_HOST:-127.0.0.1}"
PORT="${STRAVA_MCP_PORT:-8000}"
PATH_MCP="${STRAVA_MCP_PATH:-/mcp}"
BASE_URL="${STRAVA_MCP_BASE_URL:-http://localhost:${PORT}}"

# Prefer localhost in printed callback hints (Strava Authorization Callback Domain)
PRINT_BASE="${BASE_URL}"
MCP_URL="http://${HOST}:${PORT}${PATH_MCP}"
# Cursor clients typically use 127.0.0.1
CURSOR_MCP_URL="http://127.0.0.1:${PORT}${PATH_MCP}"
SETTINGS_OPEN="${PRINT_BASE%/}/oauth/strava/open?settings=1"
CALLBACK="${PRINT_BASE%/}/oauth/strava/callback"
START_HELP="${PRINT_BASE%/}/oauth/strava/start"

echo "=============================================="
echo " Strava MCP Connector — dev_up"
echo "=============================================="
echo " env file:     ${ENV_FILE}"
echo " Client ID:    ${STRAVA_CLIENT_ID:-<missing — set STRAVA_CLIENT_ID>}"
if [[ -n "${STRAVA_CLIENT_SECRET:-}" ]]; then
  echo " Client Secret: <set, not printed>"
else
  echo " Client Secret: <missing — set STRAVA_CLIENT_SECRET>"
fi
echo ""
echo " MCP URL (Cursor):  ${CURSOR_MCP_URL}"
echo " MCP URL (bind):    ${MCP_URL}"
echo " Open API settings: ${SETTINGS_OPEN}"
echo " OAuth help page:   ${START_HELP}"
echo " OAuth callback:    ${CALLBACK}"
echo ""
echo " Strava Authorization Callback Domain:  localhost"
echo "   (or your hosted hostname if BASE_URL is not local)"
echo ""
echo " Fast path: point Cursor MCP Connect at ${CURSOR_MCP_URL}"
echo " Prefer host OAuth over pixel-driving Chromium."
echo " Password/captcha → request_box_help on the bot desktop."
echo "=============================================="
echo ""

if [[ -z "${STRAVA_CLIENT_ID:-}" || -z "${STRAVA_CLIENT_SECRET:-}" ]]; then
  echo "WARNING: STRAVA_CLIENT_ID / STRAVA_CLIENT_SECRET missing in env."
  echo "OAuth will fail until they are set. Continuing to start HTTP anyway..."
  echo ""
fi

# Activate venv if present
if [[ -f "${SERVER_DIR}/.venv/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "${SERVER_DIR}/.venv/bin/activate"
fi

export STRAVA_MCP_TRANSPORT="${STRAVA_MCP_TRANSPORT:-http}"
export STRAVA_MCP_HOST="${HOST}"
export STRAVA_MCP_PORT="${PORT}"
export STRAVA_MCP_PATH="${PATH_MCP}"
export STRAVA_MCP_BASE_URL="${BASE_URL}"

if command -v strava-mcp-connector >/dev/null 2>&1; then
  exec strava-mcp-connector --transport http
elif command -v mcp-strava-connector >/dev/null 2>&1; then
  exec mcp-strava-connector --transport http
else
  echo "strava-mcp-connector not on PATH. Install editable first:"
  echo "  cd ${SERVER_DIR} && uv pip install -e .   # or: pip install -e ."
  exit 1
fi
