# Deployment

Cloud Run hosts FastAPI, Google ADK, Gemini on Vertex AI, the official
`mcp-clickhouse` package, and direct ingest. A dedicated GCP VM runs ClickHouse
26.3 LTS and Caddy from `clickhouse/docker-compose.yml`.

The VM firewall exposes only TCP 80/443. Caddy obtains and renews TLS for the
sslip.io hostname and proxies to ClickHouse's internal HTTP port. Native ports
8123, 9000, and 9009 are not published.

Cloud Run's `safe-frame-runtime` identity requires Vertex access and accessor
permission on exactly two secrets: the SELECT-only MCP password and ingest
password. The ClickHouse VM identity has no project roles.

Rebuild the VM by copying `clickhouse/`, providing an untracked `.env` containing
`SAFE_FRAME_DOMAIN` and `CLICKHOUSE_INGEST_PASSWORD`, then running
`clickhouse/bootstrap.sh`. Recreate the `safe_frame_mcp` user with SELECT on
`safe_frame.*` and rotate both Secret Manager versions after recovery.
