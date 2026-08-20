#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
  apt-get update
  apt-get install -y ca-certificates curl docker.io docker-compose-v2
fi

systemctl enable --now docker
install -d -m 0750 /opt/safe-frame-clickhouse
docker compose --project-directory /opt/safe-frame-clickhouse \
  -f /opt/safe-frame-clickhouse/docker-compose.yml up -d
