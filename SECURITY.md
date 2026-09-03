# Security

Report vulnerabilities privately through GitHub security advisories for
`usv240/safe-frame`.

- The public app never displays or plays flashing media; it uses static charts
  and numerical fixtures.
- The live verdict is deterministic SQL. Gemini cannot change it.
- Ingestion and MCP use distinct credentials. The MCP user has SELECT only on
  `safe_frame.*`, and the MCP server also forces write/drop access off. That is
  the credential the public request path uses for every read.
- **The ingest user is not least-privileged, and that is a known gap.** It was
  created with broad grants, table DDL, and also role and user administration
  and the external-source engines, where INSERT and SELECT on `safe_frame.*`
  plus table DDL for regenerating the corpus would be sufficient. It is used by
  the application only to insert violation rows. The credential is held in
  Secret Manager, mounted into the runtime, and never returned by the API, but
  if it did leak the holder could do considerably more than insert. Tightening
  it needs care not to revoke the grant option that would be required to restore
  it, so it is recorded here rather than changed close to a deadline.
- The MCP subprocess receives only ClickHouse connection variables; Google and
  ingest credentials are excluded.
- Secrets are mounted from Google Secret Manager and never returned by the API.
- Only HTTPS reaches the ClickHouse VM; native database ports are not public.

This contest deployment processes synthetic metrics only. A real studio rollout
must add authenticated uploads, malware scanning, tenant isolation, retention
policy, operator authorization, and certification workflow.

## Public API exposure

The API is intentionally open: judging requires the product to be testable
without an account. The exposure that creates is bounded rather than accepted.

- The MCP path is read-only. The child process is started with
  `CLICKHOUSE_ALLOW_WRITE_ACCESS=false` and `CLICKHOUSE_ALLOW_DROP=false`,
  receives only ClickHouse credentials, and authenticates as a SELECT-only
  database user. It cannot reach Google credentials.
- The only public write is `/v1/scan`, which persists violations for the pair it
  is given. Identifiers belonging to the published catalogue are refused, so an
  anonymous caller cannot write onto an approved master and suppress a real
  child-only finding. `/v1/samples` issues a unique lineage per request so
  callers cannot collide with each other.
- Endpoints that spend model tokens or write are rate limited per client. This
  is in-process and therefore per-instance: it exists to stop runaway loops
  exhausting quota, and is not an access-control mechanism.
- Asset identifiers are validated against `^[A-Za-z0-9_-]{1,80}$` before they
  reach any SQL string.
