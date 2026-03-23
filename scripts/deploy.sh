#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
elif docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
else
  echo "Docker Compose not found" >&2
  exit 1
fi

if [[ ! -f ".env" ]]; then
  echo ".env file not found in $ROOT_DIR" >&2
  exit 1
fi

echo "[1/5] Pulling latest code"
git pull --ff-only

echo "[2/5] Installing mini app dependencies"
cd "$ROOT_DIR/miniapp"
npm ci

echo "[3/5] Building mini app"
npm run build:check

echo "[4/5] Rebuilding containers"
cd "$ROOT_DIR"
$COMPOSE_CMD down --remove-orphans || true
$COMPOSE_CMD up -d --build

echo "[5/5] Current container status"
$COMPOSE_CMD ps
