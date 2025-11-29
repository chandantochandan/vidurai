#!/usr/bin/env bash
set -euo pipefail

# Vidurai v2.0.0 – Docker Release Script
# REQUIREMENTS:
#   - Docker logged in: docker login
#   - Set REGISTRY (e.g., "docker.io") and NAMESPACE (e.g., "chandantochandan")

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

: "${REGISTRY:=docker.io}"
: "${NAMESPACE:=chandantochandan}"

echo "[vidurai] Building daemon image..."
docker build -f vidurai-daemon/Dockerfile -t vidurai-daemon:2.0.0 .

echo "[vidurai] Building proxy image..."
docker build -f vidurai-proxy/Dockerfile -t vidurai-proxy:2.0.0 .

DAEMON_TAG="${REGISTRY}/${NAMESPACE}/vidurai-daemon:2.0.0"
PROXY_TAG="${REGISTRY}/${NAMESPACE}/vidurai-proxy:2.0.0"

echo "[vidurai] Tagging images..."
docker tag vidurai-daemon:2.0.0 "$DAEMON_TAG"
docker tag vidurai-proxy:2.0.0 "$PROXY_TAG"

echo "[vidurai] Pushing daemon image to $DAEMON_TAG..."
docker push "$DAEMON_TAG"

echo "[vidurai] Pushing proxy image to $PROXY_TAG..."
docker push "$PROXY_TAG"

echo "[vidurai] Docker release complete."
