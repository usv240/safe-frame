# Safe Frame implementation status

Updated: 2026-08-28

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
- [x] Public Cloud Run revision `safe-frame-regression-00013-7sf`
- [x] Live acceptance re-verified against the deployed revision: sweep, per-pair
      verdict and ADK explanation agree on both a general-flash and a red-flash
      pair; all four controls behave (`docs/LIVE-ACCEPTANCE.json`)
- [x] Measurement stage from decoded frames (`safe_frame/ingest.py`), including a
      matched-luminance red alternation the luminance rule provably cannot see
- [x] Catalogue corpus at scale: 9,600,000 transition rows, 3,200 renditions, 400 titles
- [x] Published criteria evaluated inside ClickHouse in one pass (`sql/006_catalogue_regression.sql`)
- [x] Catalogue sweep isolates 44 introduced regressions (31 general flash, 13 red
      flash) and excludes every inherited one, for both rules
- [x] Two published rules implemented and windowed independently: general flash
      and red flash (no luminance floor), both evaluated in one sweep
- [x] SQL/Python parity suite: 43 cases agree exactly with the reference
      detector across both rules, with a guard test that fails if the fixtures
      stop producing violations
- [x] Persistent official mcp-clickhouse session, warmed at startup (sweep 1.7s end to end over 9.6M rows)
- [x] Official ClickHouse Agent Skills applied to schema and catalogue query;
      findings and three measured declines in docs/CLICKHOUSE-SKILLS-REVIEW.md,
      including a CRITICAL rule that benchmarking contradicted
- [x] Every surface agrees about a pair: the sweep, `/v1/catalogue/regressions`
      and the ADK agent's evidence all read one union of the catalogue and
      persisted planes
- [x] Dead scaffolding removed; every tracked module is reachable from the
      running product or its tests

## Release tasks

- [ ] Complete desktop/mobile visual QA when browser control is available
- [ ] Record and publish the under-three-minute demo
- [ ] Complete Devpost submission
- [ ] Obtain qualified external review before making any stronger efficacy claim

Machine-readable proof is captured in `docs/LIVE-ACCEPTANCE.json`. It contains no credentials.
