# Safe Frame implementation status

Updated: 2026-08-20

## Complete

- [x] Independent public repository and detected Apache-2.0 license
- [x] Direct changed-area measurement validated against tile cancellation
- [x] Deterministic pass/fail boundary tests
- [x] Presentation-time lineage anti-join with transform attribution
- [x] Dedicated ClickHouse 26.3 LTS cluster on GCP behind HTTPS
- [x] Separate ingest and SELECT-only MCP database users
- [x] Official `mcp-clickhouse` runtime, forced read-only
- [x] Live verdict fails closed if MCP/SQL fails
- [x] Real Google ADK + Gemini Vertex explanation path
- [x] Light-default, opt-in dark, non-flashing public web product
- [x] Self-authored constructed judge sample
- [x] Public Cloud Run revision `safe-frame-regression-00008-q4v`
- [x] Live acceptance: official MCP anti-join returned one regression and ADK explanation completed

## Release tasks

- [ ] Complete desktop/mobile visual QA when browser control is available
- [ ] Record and publish the under-three-minute demo
- [ ] Complete Devpost submission
- [ ] Obtain qualified external review before making any stronger efficacy claim

Machine-readable proof is captured in `docs/LIVE-ACCEPTANCE.json`. It contains no credentials.
