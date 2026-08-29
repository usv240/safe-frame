# Safe Frame

Safe Frame is a master-to-rendition photosensitivity regression pre-check. It
asks a deliberately narrow question: did a transformation introduce a violation
that was absent from the approved parent?

Public app: <https://safe-frame-regression-109051079423.us-central1.run.app>

Start with [`JUDGING.md`](JUDGING.md) for the shortest verified judge path,
[`docs/CRITERIA.md`](docs/CRITERIA.md) for where every threshold came from,
[`docs/IMPACT.md`](docs/IMPACT.md) for who this is for and what has *not* been
shown, and [`submission-evidence.json`](submission-evidence.json) for
machine-readable proof.

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

## Two rules, windowed independently

Published guidance is not one rule, and the thresholds are not ours to pick.
Every one traces to WCAG 2.3.1 — see [`docs/CRITERIA.md`](docs/CRITERIA.md) for
the quoted definitions. Safe Frame implements two of the three tests:

- **general flash** — luminance alternation at or above a 0.10 delta.
- **red flash** — saturated-red alternation at or above a 0.20 red delta, with
  **no luminance floor at all**. A red/blue alternation can hold luminance
  almost flat and still be the higher-risk sequence, so gating it on luminance
  would reproduce the exact blind spot the rule exists to close.

Each rule gets its own 1000 ms window, so one rule's qualifying transitions can
never pad the other's count, and the anti-join is keyed on `rule` — a master
that already flashed in luminance does not excuse a rendition that introduced a
red flash. Both rules are evaluated in ClickHouse in a single pass over the
catalogue.

## From pixels to a verdict

`safe_frame.ingest.frames_to_transitions` measures decoded frames into the
transition rows everything downstream evaluates. For each consecutive pair it
records two things separately, because the criteria test them independently:
how large the change is *where it happened* (averaged over the pixels that
actually moved) and how much of the screen moved at all. Averaging over the
whole frame would conflate the two and let a partial-screen flash slip under
the delta floor.

Presentation time comes from the frame rate, never the frame index, so a 24 to
60 fps conversion still aligns against its master. Decoding a container into
frames is out of scope on purpose: that is commodity ffmpeg work, and its codec
dependencies do not belong in the request path of a service whose job is
arithmetic.

`tests/test_ingest.py` runs constructed frame sequences end to end, including a
saturated-red alternation at matched BT.709 luminance where the luminance rule
measures a swing below 0.01 and stays silent while the red rule fires.

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
anti-join. The same anti-join backs `/v1/catalogue/regressions` and the evidence
the ADK agent reads, so no two surfaces can disagree about one pair. If MCP fails or the SQL count cannot be parsed, the live API returns
502. It never substitutes a Gemini verdict or a local guess.

Useful judge endpoints:

- `/` — the catalogue sweep, no flashing media
- `/health` — cached live Vertex and MCP/ClickHouse round-trips
- `/v1/catalogue/shape` — size of the corpus, read live
- `/v1/catalogue/sweep` — both rules evaluated across the whole catalogue
- `/v1/catalogue/regressions` — SQL/MCP verdict for one asset pair
- `/v1/samples` — self-authored exact pass/fail metric pair
- `/v1/scan` — submit raw transition metrics for a parent/child pair
- `/v1/integrations/clickhouse/evidence` — advertised MCP tools and live query
- `/v1/explain` — ADK explanation grounded in MCP evidence
- `/docs` — complete OpenAPI surface

## Verification

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m uvicorn safe_frame.main:app --reload
```

```powershell
python -m pip install playwright
python -m playwright install chromium
python scripts/visual_check.py --offline
```

`scripts/visual_check.py` drives a real browser against the page. `--offline`
serves the web directory with no backend, so every fetch fails, and requires
that initialisation completes with zero page errors, the toggles respond, and a
failing sweep reports failing closed; it then stubs the endpoints and drives the
whole evidence path. It exists because a script that throws at init detaches
every listener while every assertion about page *content* still passes, and that
has happened twice. `--url` drives the judge path against a deployment and fails
on horizontal overflow or console errors at phone, laptop and desktop widths in
both themes.

`tests/test_sql_parity.py` runs the reference Python detector and the ClickHouse
criteria SQL over identical randomized rows and requires exact agreement on both
rules. It executes real SQL, so it is skipped unless `MCP_CLICKHOUSE_COMMAND` and
the ClickHouse connection variables point at a reachable cluster; the structural
guards in `tests/test_clickhouse_mcp.py` catch threshold drift without one.

The fixtures are self-authored synthetic measurements with known boundaries.
They are engineering evidence, not clinical validation or certification. See
`docs/PRIOR-ART.md`, `docs/LIMITATIONS.md`, and `docs/LIVE-ACCEPTANCE.json`.

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
