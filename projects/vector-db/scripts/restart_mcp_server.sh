#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname "$0")" && pwd)
PROJECT_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd)

docker compose -f "$PROJECT_DIR/docker-compose.mcp.yml" up -d
"$PROJECT_DIR/.venv/bin/python" "$SCRIPT_DIR/wait_for_mcp_ready.py" --url "http://127.0.0.1:8765/ready" --timeout 120
