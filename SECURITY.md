# Security

Report vulnerabilities privately through GitHub security advisories for
`usv240/safe-frame`.

- The public app never displays or plays flashing media; it uses static charts
  and numerical fixtures.
- The live verdict is deterministic SQL. Gemini cannot change it.
- Ingestion and MCP use distinct credentials. The MCP user has SELECT only, and
  the MCP server also forces write/drop access off.
- The MCP subprocess receives only ClickHouse connection variables; Google and
  ingest credentials are excluded.
- Secrets are mounted from Google Secret Manager and never returned by the API.
- Only HTTPS reaches the ClickHouse VM; native database ports are not public.

This contest deployment processes synthetic metrics only. A real studio rollout
must add authenticated uploads, malware scanning, tenant isolation, retention
policy, operator authorization, and certification workflow.
