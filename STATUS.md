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
- [x] Public Cloud Run revision `safe-frame-regression-00030-8tl`
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
- [x] SQL/Python parity suite: 45 cluster-backed cases agree exactly with the
      reference detector across both rules and the darker-image ceiling, plus a
      cluster-free guard that fails if the fixtures stop producing violations
- [x] Persistent official mcp-clickhouse session, warmed at startup (sweep about 1.9s end to end over 9.6M rows; ~0.8s of that is the ClickHouse query, the rest MCP transport and serialisation)
- [x] Official ClickHouse Agent Skills applied to schema and catalogue query;
      all 31 rules accounted for in docs/CLICKHOUSE-SKILLS-REVIEW.md, with four
      measured declines including a CRITICAL rule that benchmarking contradicted
      and a refreshable Materialized View that is 158x faster than what ships
      and still deliberately not enabled
- [x] Every surface agrees about a pair: the sweep, `/v1/catalogue/regressions`
      and the ADK agent's evidence all read one union of the catalogue and
      persisted planes
- [x] Dead scaffolding removed; every tracked module is reachable from the
      running product or its tests

- [x] Every threshold traced to a quoted WCAG 2.3.1 definition, and the one
      unimplemented rule named on the product surface (`docs/CRITERIA.md`)
- [x] Impact case argued from published sources, with an explicit list of what
      has *not* been shown (`docs/IMPACT.md`)
- [x] Evidence chart: master and rendition tracks from one query on one shared
      scale, series colours validated for colour-vision deficiency, table view
      and text alternative provided
- [x] Design system: fluid type and space scales, three-state theming, focus
      rings, skip link, keyboard-selectable rows, all motion disabled under
      `prefers-reduced-motion`

- [x] Multi-step ADK agent (`QcTriageAgent`): four read-only MCP tools it
      sequences itself, with the tool-call trace recorded and shown on the page
- [x] Systemic root-cause analysis: per-transform regression rates turn 44
      findings into four implicated encoder profiles and three clean ones
- [x] Impact stated on the product surface with sources, not only in the repo
- [x] Partner integration checkable from the page itself: transport, read-only
      status, advertised tools and a live query result
- [x] Runtime hops shown with the credential boundary marked
- [x] Audience named explicitly (distribution QC and encoding teams)
- [x] Findings can leave the page as a report carrying its own limitations

- [x] Standards audit against the primary W3C texts, with the three defects it
      found written up and the surviving deviations named (`docs/CRITERIA.md`)
- [x] Darker-image condition implemented; bright-on-bright control cohort added
      so it cannot silently regress (13 false positives removed)
- [x] Relative luminance linearised per the WCAG definition
- [x] Saturated red implemented as published, not as a proxy

- [x] Public API exposure bounded: catalogue identifiers refused as write
      targets, per-request sample lineages, rate limits on the endpoints that
      spend model tokens or write, and no cap on any read

- [x] Structured run telemetry: every agent run logs its tool sequence and
      decision source, every fail-closed refusal logs why, in Cloud Logging shape

- [x] Scored evaluation against an independently-derived ground truth:
      44 planted, 44 found, precision and recall 1.000, all 55 decoys rejected
      (`/v1/evaluation`, `sql/008_ground_truth.sql`)

## Release tasks

- [ ] Record and publish the under-three-minute demo — script ready in
      `docs/DEMO-SCRIPT.md`
- [ ] Complete Devpost submission — paste-ready copy in `docs/DEVPOST.md`
- [ ] Obtain qualified external review before making any stronger efficacy claim
      (not obtained; the standards audit in `docs/CRITERIA.md` is a checkable
      substitute, not an equivalent)

Machine-readable proof is captured in `docs/LIVE-ACCEPTANCE.json`. It contains no credentials.
