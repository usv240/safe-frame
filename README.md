# Safe Frame

Safe Frame is a master-to-rendition photosensitivity regression pre-check. It
asks a deliberately narrow question: did a transformation introduce a violation
that was absent from the approved parent?

Public app: <https://safe-frame-regression-109051079423.us-central1.run.app>

Start with [`JUDGING.md`](JUDGING.md) for the shortest verified judge path and
[`submission-evidence.json`](submission-evidence.json) for machine-readable proof.

It is **not a certified, broadcaster-approved, or medical diagnostic device**.
The deterministic detector and ClickHouse SQL are an open pre-check against
published criteria. Gemini may explain database evidence; it cannot decide pass
or fail.

## Why this is different

Detection, repair, viewer-side dimming, and networked batch analysis already
exist. Our documented search found file-level and networked batch analysers and
an explicitly no-reference enterprise QC product, but did not find documented
master-to-rendition photosensitivity regression analysis. This is a documented
gap, not proof that no private integration exists.

Safe Frame aligns an approved master and every rendition on presentation time,
then uses a ClickHouse anti-join to isolate violations present only in the child
and attribute them to the conversion. Frame index is never used for lineage
alignment because frame-rate conversion makes it invalid.

## Runtime architecture

- The deterministic detector measures affected area directly, before lossy tile
  aggregation. A constructed checkerboard test proves why this matters.
- Writes use `clickhouse-connect` with a dedicated ingest identity.
- **Every catalogue read and live verdict uses the official
  `ClickHouse/mcp-clickhouse` server in read-only stdio mode.** The child process
  receives only ClickHouse credentials; it cannot access Google credentials.
- The deployed ClickHouse 26.3 LTS cluster is self-hosted on a dedicated GCP VM,
  exposed only through HTTPS, and uses a separate SELECT-only MCP user.
- `RegressionExplainer` is a real Google ADK agent using Gemini 2.5 Flash on
  Vertex AI. It must retrieve evidence through MCP and always requires human QC.
- Cloud Run uses a dedicated `safe-frame-runtime` identity and Secret Manager.

## Decision boundary

`POST /v1/scan` computes the parent and child violations, persists them, and then
asks ClickHouse—through official MCP—to execute the published child-minus-parent
anti-join. If MCP fails or the SQL count cannot be parsed, the live API returns
502. It never substitutes a Gemini verdict or a local guess.

Useful judge endpoints:

- `/` — one-click constructed boundary proof, no flashing media
- `/health` — cached live Vertex and MCP/ClickHouse round-trips
- `/v1/samples` — self-authored exact pass/fail metric pair
- `/v1/integrations/clickhouse/evidence` — advertised MCP tools and live query
- `/v1/catalogue/regressions` — SQL/MCP verdict for an asset pair
- `/v1/explain` — ADK explanation grounded in MCP evidence
- `/docs` — complete OpenAPI surface

## Verification

```powershell
python -m pip install -r requirements.txt pytest httpx
python -m pytest -q
python -m uvicorn safe_frame.main:app --reload
```

The fixtures are self-authored synthetic measurements with known boundaries.
They are engineering evidence, not clinical validation or certification. See
`docs/PRIOR-ART.md`, `docs/LIMITATIONS.md`, and `docs/LIVE-ACCEPTANCE.json`.

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
