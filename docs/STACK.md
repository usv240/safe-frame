# The stack, and what each part actually does

`/v1/stack` reports this live, with a status per component. This document is the
long version: why each piece is here, how it is used, and the measurements
behind the choices. Every number below was measured against the deployment, and
where a measurement contradicted a reasonable assumption, that is recorded too.

Live status legend, used identically here and on the page:

| status | meaning |
|---|---|
| live | a round trip to a remote system completed just now |
| active | in use in the process serving the request |
| applied | built or verified the project, not in the request path |

---

## ClickHouse, the partner track

### The cluster

ClickHouse **26.3 LTS**, self-hosted on a dedicated GCP VM, reachable only over
HTTPS through Caddy. Native database ports are not exposed. Two database users:
a SELECT-only user for everything the MCP server does, and a separate ingest
user for the two write paths.

The version on the page is not a constant. `/v1/stack` executes `SELECT
version()` through MCP and parses what comes back, which is why it reads
`26.3.20.7` rather than the marketing name.

### What it is asked to do

The published flash criteria are not a lookup, they are the query. Both WCAG
2.3.1 tests are implemented as SQL in
[`sql/006_catalogue_regression.sql`](../sql/006_catalogue_regression.sql) and
evaluated across the whole catalogue in one pass:

1. **general flash**: `luma_delta >= 0.10 AND luma_min < 0.80 AND changed_area_fraction >= 0.25`
2. **red flash**: `red_delta >= 0.20 AND changed_area_fraction >= 0.25`, with **no
   luminance condition at all**, because a saturated-red alternation can hold
   luminance nearly flat and still be the higher-risk sequence
3. each rule gets its **own** 1000 ms window, so one rule's qualifying
   transitions can never pad the other's count
4. a violation is more than six qualifying transitions inside the window with
   both directions present
5. a *regression* is a child violation with no parent violation of the **same
   rule** within 100 ms

Step 5 is the product. Everything else is a flash detector.

### Schema and query decisions, with numbers

**Alignment is on presentation time, never frame index.** A 24 to 60 fps
conversion renumbers every frame while preserving `pts_ms`, so frame index is
not a lineage key. The window is
`RANGE BETWEEN CURRENT ROW AND 999 FOLLOWING` over `pts_ms`.

**MergeTree ordered by `(lineage_id, asset_id, pts_ms)`**, with 400, then 3,200,
then 3,000 distinct values. All four string columns are `LowCardinality`, well
under the 10,000 guidance, and `direction` is an `Enum8`.

**Isolation by partition window rather than a self anti-join.** The obvious
shape is a `LEFT ANTI JOIN` of the violations CTE against itself, which builds
the violations set twice. A `minIf(...) OVER (PARTITION BY lineage_id, rule)`
builds it once:

| shape | rows read | time |
|---|---|---|
| self anti-join | 19.2M | 2,274 ms |
| partition window (shipped) | 9.6M | 791 ms |

**A CRITICAL vendor rule, declined with measurements.** ClickHouse's own Agent
Skills say to avoid scanning a table twice when one pass will do. The
single-scan alternative, `ARRAY JOIN` with `arrayFilter` to fan a row out to the
rules it satisfies, was built and measured against the shipped two-pass UNION
over five runs each:

| shape | rows read | median |
|---|---|---|
| two passes, UNION (shipped) | 10,263,552 | 834 ms |
| one pass, ARRAY JOIN | 9,600,000 | 1,064 ms |

Identical output; the "better" shape is **27 percent slower**. The rows-read
column explains it: two passes over 9.6M rows should read 19.2M and read 10.26M,
because per-granule min/max lets ClickHouse skip about 93 percent of the second
scan. No granule in most of the table can satisfy `red_delta >= 0.20`. The extra
scan is nearly free; unnesting a two-element array per surviving row is not.

**A refreshable materialised view measured 158x faster and is deliberately not
enabled.** [`sql/007_refreshable_regressions.sql`](../sql/007_refreshable_regressions.sql)
exists and works. It is off because a judge pressing *Sweep the catalogue*
should watch the criteria being evaluated, not watch a cached answer being read.
Shipping the cache would make the demo faster and the claim weaker.

All 31 official ClickHouse Agent Skills rules were worked through, with four
measured declines, in
[`docs/CLICKHOUSE-SKILLS-REVIEW.md`](CLICKHOUSE-SKILLS-REVIEW.md).

### The official MCP server

`ClickHouse/mcp-clickhouse` **0.3.0**, started as a read-only stdio subprocess
with `CLICKHOUSE_ALLOW_WRITE_ACCESS=false` and `CLICKHOUSE_ALLOW_DROP=false`.
Every catalogue read, every live verdict and every agent tool call goes through
it. The subprocess is handed ClickHouse variables and nothing else, so it cannot
reach Google credentials.

**One long-lived session per event loop.** Spawning the server per request costs
4 to 8 seconds of subprocess and handshake while the query underneath runs in
under a second. The session is owned by a single task and fed over a queue,
because the MCP client builds on anyio task groups and a session entered in one
task and used from another raises cancel-scope errors.

The cache is keyed on the running event loop, not only the configuration. That
was a real defect: a worker's queue, lock and task belong to the loop that made
them, and the service runs one loop forever so it never showed, but any second
loop got `RuntimeError: Event loop is closed`. It surfaced the first time the
parity suite was run as a suite.

---

## Google Cloud

### Gemini 2.5 Flash on Vertex AI

Two agents, both of which must retrieve evidence through MCP and neither of
which can decide anything.

- **`RegressionExplainer`** is single-step: one validated pair, one tool.
- **`QcTriageAgent`** is the multi-step one. Four tools over the same read-only
  transport: survey the sweep, profile every transform to find the systemic
  cause, size the luminance blind spot, then inspect the pair it ranks first.

The boundary is enforced in code, not asserted in prose. Every tool is a fixed
ClickHouse query, so the model cannot obtain a number except from SQL. The tool
sequence is recorded from the run and returned with the brief. Responses carry
`decision_source=clickhouse_sql` and `requires_human=true`. If the MCP path
fails, the API returns **502** rather than substituting a model answer.

The tool *order* is prescribed by the agent instruction. What the model actually
chooses is which finding to review first and how to explain it, and the page
says exactly that rather than overclaiming autonomy.

Flash rather than Pro: the agent step is 17 to 20 seconds, and Pro would push it
past the point where a three-minute demo can carry the wait.

### Agent Development Kit

`google-adk` **2.7.1**. `LlmAgent` plus `Runner`, with the four triage tools
declared as plain Python functions. Tool calls are read off the ADK event stream
as they happen, which is how the numbered trace is recorded rather than
reconstructed afterwards.

### Cloud Run, Secret Manager, Cloud Logging

- **Cloud Run** on a dedicated `safe-frame-runtime` identity, with a warm
  instance so the first sweep is not paying a cold start on top of an MCP
  handshake.
- **Secret Manager** holds the ClickHouse passwords and the API-key signing
  secret, mounted as secret references. Nothing is baked into the image.
- **Cloud Logging** receives a structured entry for every agent run and every
  fail-closed refusal, lifted into `jsonPayload`, recording which tools ran in
  what order. No submitted data and no model prose is ever logged. An agent that
  reaches conclusions from a database is only trustworthy if you can
  reconstruct which queries it ran.

---

## The application

### Measurement

`safe_frame/ingest.py` turns frames into transition rows, and it is the only
measurement implementation in the project. That is deliberate: the browser
decodes video but does not measure it, because a JavaScript implementation of
the published maths would be a third copy of one safety rule to keep in step.

Three corrections came out of auditing our own detector against the primary
texts, all of which were wrong before:

1. relative luminance was not linearised from sRGB before the BT.709
   coefficients
2. the general-flash darker-image condition (`luma_min < 0.80`) was missing
   entirely, which alone accounted for 13 false positives
3. saturated red used `R - max(G, B)` rather than the published
   `R/(R+G+B) >= 0.8` test, and red direction was taken from the luminance
   signal, recording a matched-luminance red alternation as flat

The step and the affected area are recorded separately, because the criteria
test them independently. Averaging over the whole frame would let a
partial-screen full-range flash slip under the delta floor while clearing the
area floor.

### Correctness

**83 tests.** The one that matters most is
[`tests/test_sql_parity.py`](../tests/test_sql_parity.py): it runs the reference
Python detector and the ClickHouse SQL over identical randomised rows and
requires exact agreement on both rules, through the real MCP transport. 46
cases, including the six-versus-seven boundary, the darker-image ceiling, and a
red alternation at matched luminance.

For most of this project's life those tests never ran. They need a cluster,
public CI had none, so all 45 skipped everywhere anyone could look, and under
that cover the parametrized case compared the SQL's first *row* against the
detector's whole result list. It could not have passed. CI now stands up a
throwaway ClickHouse, runs all 46 through the real `mcp-clickhouse` transport on
every commit in 68 seconds, and **fails if they skip**.

**The detector is scored against a ground truth that reads no measurement.**
[`sql/008_ground_truth.sql`](../sql/008_ground_truth.sql) recovers the planted
set from the generator's own `sipHash64` decisions, touching no `luma_delta`,
`red_delta`, `luma_min`, `changed_area_fraction` or `direction`. On the live
corpus: **66 planted, 66 found, precision and recall 1.000**, and all 86 decoys
correctly rejected. The decoys are what make the number worth anything, since
recall alone can be bought by flagging everything.

**Part of the corpus is measured, not authored.** 24 titles, 192 assets and
576,000 rows are constructed RGB frames pushed through the real measurement path
in 149 seconds. Scored separately, they agree with the authored cohort at 1.000,
which is what rules out the corpus doing the work.

### The page

Vanilla HTML, CSS and JavaScript. No framework, no build step, no runtime
dependency to break. Theme is a token swap with three states, and the visitor's
OS preference is honoured until they override it.

[`scripts/visual_check.py`](../scripts/visual_check.py) drives a real browser at
phone, laptop and desktop widths in both themes and fails on horizontal overflow
or any console error. `--offline` serves the page with no backend at all, so
every fetch fails, and requires that initialisation still completes. It exists
because a script that throws at init detaches every listener while every
assertion about page *content* still passes, and that happened twice.

Three defects it found that the Python suite could not: a `let` read from its
temporal dead zone during theme restore, a chart placeholder destroyed by the
draw that replaced it, and a phone card layout that overflowed by exactly its
own margin.

---

## What is not here

- No container decoding. Frames come from the browser or from the caller;
  ffmpeg's codec dependencies do not belong in the request path of a service
  whose job is arithmetic.
- No spatial-pattern rule. It is one of the three WCAG 2.3.1 tests and it is not
  implemented, which the criteria table states in place rather than omitting.
- No expert review. The implementation was audited against the primary texts
  because a qualified photosensitive-epilepsy or broadcast professional could
  not be obtained, and that is not equivalent.
