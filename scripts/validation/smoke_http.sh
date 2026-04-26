#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${1:-http://localhost:8000}"

echo "[v40] liveness"
curl -fsS "$BASE_URL/api/v1/ops/live/" >/dev/null

echo "[v40] public status"
curl -fsS "$BASE_URL/api/v1/ops/status/" >/dev/null

echo "[v40] OpenAPI schema"
curl -fsS "$BASE_URL/api/schema/" >/dev/null

echo "[v40] public HTTP smoke checks passed"
