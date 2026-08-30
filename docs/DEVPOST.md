# Devpost submission text

Paste-ready copy for each required field. Track: **ClickHouse**.

---

## Elevator pitch (200 char limit)

Find the rendition that introduced a photosensitivity risk its approved master never had — across a whole catalogue, in one ClickHouse query.

---

## Inspiration

A film is approved once. Then it becomes dozens of derived assets: frame-rate
conversions, tone-maps, downscales, social crops, ad-break inserts, burnt-in
subtitles. Photosensitivity QC is mature — Harding-style analysers test
luminance flashes, red flashes and spatial patterns, and standard encoding
practice puts the quality gate at ingest, before transcode, because a defective
master multiplies across the whole delivery ladder.

That reasoning is right, and that gate does its job. But it runs *before* the
transforms. And a per-file check run *after* a transform has no memory of the
parent, so it cannot tell you whether a violation is new. The version an
audience actually watches can carry a risk that the approved master never had,
and nothing in the normal pipeline is asking that question.

Photosensitive epilepsy affects roughly 1 in 4,000 people. In 1997 a single
broadcast sent 685 children to hospital in Japan. The obligation is real too —
Ofcom Rule 2.12, WCAG 2.3.1. So we built the one check we could not find:
did *this transformation* introduce a violation that was absent from the
approved parent?

## What it does

Safe Frame is a master-to-rendition photosensitivity **regression** pre-check.

- It aligns an approved master and every rendition on **presentation time**,
  never frame index — a 24→60 fps conversion renumbers every frame but preserves
  pts, so frame index is not a valid lineage key.
- It evaluates the published criteria across every transition measurement in the
  catalogue **inside ClickHouse in a single pass**, and isolates child-only
  violations in the same query.
- It attributes each regression to the transform that produced it.
- It draws the two tracks — approved master and shipped rendition — on one
  shared scale, so "the master stayed under the criterion for its whole runtime
  and the rendition did not" is read off measurements rather than asserted.
- A **multi-step** Google ADK agent on Gemini turns the findings into a QC brief,
  but **cannot decide anything**. It has four tools, every one a live ClickHouse
  query through the official MCP server, and it sequences them itself: survey the
  sweep, profile every transform to find the systemic cause, size the luminance
  blind spot, then inspect the single pair it ranks first. The tool-call sequence
  is returned with the brief so it can be checked rather than trusted.

On the live corpus (400 titles, 3,200 renditions, 9,600,000 transition rows) the
sweep returns 44 renditions that introduced a violation — 31 general flash, 13
red flash — in about two seconds end to end, of which roughly 0.8s is the
ClickHouse query itself. It correctly excludes every control cohort: titles whose
*master* already violated, and a bright-on-bright cohort that the published
darker-image condition does not apply to.

## We scored it against a ground truth it cannot see

A synthetic corpus invites one fair objection: bursts were planted, then found.

So the planted set is recovered independently — from the generator's own
`sipHash64` decisions, by a query that reads **no measurement column at all**
(`sql/008_ground_truth.sql`) — and compared against what the criteria returned.

| | |
|---|---|
| planted | 44 |
| found | 44 |
| false negatives | 0 |
| false positives | 0 |
| precision / recall | 1.000 / 1.000 |
| decoys correctly rejected | 55 of 55 |

The decoys carry the result. 42 are renditions with a genuine burst that is *not*
a regression, because the approved master has the same burst at the same
presentation time. 13 are a bright-on-bright cohort that clears the delta, area
and rate floors and sits above the published 0.80 darker-image ceiling. Recall
alone could be bought by flagging everything; precision is measured against
those.

Two tests defend the independence: the ground-truth query may not name a
measurement column, and the detector may not contain `sipHash64`. Otherwise
someone simplifying this later turns it into a tautology that still prints 1.000.

This establishes something narrow and worth stating exactly: the implementation
does what the published criteria say, at catalogue scale, including on cases
built to fool it. It says nothing about real footage.

## Findings become an action

44 failures is not an operational answer. The next query is the one that matters:
of every transform in the catalogue, how many renditions did it produce and how
many did it break?

| Transform | Renditions | Regressed | Rule |
|---|---|---|---|
| `60fps_interp` | 400 | 16 (4.00%) | general flash |
| `adbreak_insert` | 400 | 15 (3.75%) | general flash |
| `subtitle_burnin` | 400 | 7 (1.75%) | red flash |
| `social_crop_v` | 400 | 6 (1.50%) | red flash |
| three others | 1,200 | 0 | — |

Four profiles out of eight account for everything, and the two rules cluster on
*different* profiles — the frame-rate and ad-break paths introduce luminance
flashes, the crop and subtitle paths introduce saturated-red ones. Two root
causes, two owners, a handful of upstream fixes instead of 44 patches. And 13 of
the 44 come from profiles whose only failure mode is red flash, so a
luminance-only checker passes every one of them.

## Two rules, and why the second one matters

Published guidance is not one rule. Safe Frame implements two of the three
tests, with every threshold quoted from WCAG 2.3.1:

| Test | Threshold | Published definition |
|---|---|---|
| General flash | `luma_delta >= 0.10` | "a pair of opposing changes in relative luminance of 10% or more" |
| Red flash | `red_delta >= 0.20`, **no luminance floor** | "any pair of opposing transitions involving a saturated red" |
| Affected area | `>= 0.25` | more than "25% of any 10 degree visual field on the screen" |
| Rate | more than 6 opposing transitions in 1000 ms | "no more than three flashes within any one-second period" |
| Spatial pattern | **not implemented** | named explicitly rather than left implied |

The red rule carries no luminance floor on purpose, and that is the most
consequential decision in the detector. WCAG gives saturated red its own test
because people are more sensitive to red flashing than to other colours. A
saturated red alternating with a colour of matched relative luminance moves
`luma_delta` almost not at all — so gating the red rule on luminance would
recreate the exact blind spot the separate test exists to close. Our test suite
demonstrates this from pixels: measured luminance swing stays under 0.01 while
saturated red swings past 0.9, the general rule stays silent, and the red rule
fires.

The two rules are also windowed **independently**. Four red-qualifying and four
luminance-qualifying transitions in one second is eight transitions, but neither
rule reaches seven on its own, so nothing is reported. Combining them would
invent a violation that neither published test supports.

## How we built it

**Google Cloud**
- **Google ADK** (`google-adk`) — real `LlmAgent` + `Runner`; every tool either
  is bound to a validated asset pair or runs a fixed ClickHouse query through MCP.
- **Gemini 2.5 Flash on Vertex AI** (`google-genai`) — orchestration and
  narration only; it never produces a verdict.
- **Cloud Run** — the public app, on a dedicated `safe-frame-runtime` identity.
- **Secret Manager** — two database passwords, nothing else.

**ClickHouse (partner track)**
- Every catalogue read and every verdict goes through the **official
  `ClickHouse/mcp-clickhouse` server** in read-only stdio mode, against a
  self-hosted **ClickHouse 26.3 LTS** cluster on a dedicated GCP VM behind HTTPS.
- The MCP child process receives *only* ClickHouse credentials and is forced
  read-only; it cannot reach Google credentials.
- Separate database identities: a SELECT-only user for MCP, a distinct user for
  ingest.
- One long-lived MCP session, warmed at startup, so a visitor's first sweep
  measures the query rather than a subprocess handshake.
- The official **ClickHouse Agent Skills** were applied to the schema and the
  catalogue query; findings and three measured declines are written up in
  `docs/CLICKHOUSE-SKILLS-REVIEW.md`.

**The agent**
Two ADK agents on Gemini 2.5 Flash. `RegressionExplainer` is single-step, bound
to one validated pair. `QcTriageAgent` is the multi-step one described above.
Neither can reach a verdict; both end by handing the decision to a human.

**The decision boundary**
`/v1/scan` computes violations, persists them, then asks ClickHouse through
official MCP to execute the published child-minus-parent anti-join. If MCP fails
or the SQL result cannot be parsed, the API returns **502**. It never
substitutes a Gemini verdict or a local guess.

## Data sources

The public catalogue is **self-authored synthetic measurement**, generated
server-side by `sql/005_catalogue_generator.sql` and deterministic under
`sipHash64`, so it reproduces byte-identically. It contains no footage, no
music, no third-party logos and no found datasets. It carries deliberate control
cohorts whose *master* already violates — the sweep must exclude those, or the
anti-join would look correct while doing nothing.

There is no flashing media anywhere in the product or the demo.

## Challenges we ran into

**Two data planes silently disagreeing.** The catalogue sweep evaluated criteria
live over the transitions table, while the per-pair endpoints and the agent read
a `violations` table the catalogue never populated. Clicking a flagged rendition
and asking the agent returned "no photosensitivity events were detected" — for a
row the sweep had just reported. The fix was to make the per-pair query evaluate
the criteria over transitions and union that with the persisted rows *before* the
anti-join, so no two surfaces can disagree about one pair.

**A parity claim that was true but empty.** Our randomized SQL-vs-Python parity
tests agreed 40 times out of 40 — because the fixtures never produced a
violation at all. Agreement about nothing is not evidence. We changed the
fixture generator to draw transition spacing per case and added a guard test
that fails if either rule stops firing.

**A CRITICAL vendor rule that benchmarking contradicted.** ClickHouse's own
guidance says to avoid repeated scans. Evaluating both rules in one pass —
filter once, then fan each surviving row out to the rules it satisfies with
`ARRAY JOIN arrayFilter(...)` — halves the rows read. We built it, measured it
five times against the two-pass `UNION ALL` form, and it was **56% slower**
(median 1,096 ms vs 703 ms), because unnesting an array per surviving row costs
more than a second scan whose predicate is very selective. We shipped the form
the measurement favoured and wrote up the decline.

**We audited our own detector against the standard and found it wrong.**

We could not get review from a qualified photosensitive-epilepsy professional, so
we read the primary W3C texts and checked the implementation line by line. It
found three defects, all of which changed results:

- **Relative luminance was never linearised.** We applied the BT.709 coefficients
  directly to gamma-encoded sRGB. Every threshold is expressed against WCAG's
  definition, so the error propagated — including into the test fixture built
  from the same wrong assumption, which was therefore passing for the wrong reason.
- **The darker-image condition was missing entirely.** The general-flash test
  applies only "where the relative luminance of the darker image is below 0.80".
  On our catalogue the sweep returns **44** with that condition and **57**
  without it: thirteen false positives, every one a rendition the published test
  does not apply to.
- **Saturated red was a proxy**, not the published `R/(R+G+B) >= 0.8` test.
  Fixing it exposed a fourth bug: red-transition direction was taken from the
  luminance signal, so a red alternation at matched luminance recorded as `flat`
  and silently disqualified the exact case the red rule exists to catch.

The corpus now carries a bright-on-bright control cohort so the darker-image
condition cannot silently regress. `docs/CRITERIA.md` quotes every definition and
names the deviations that remain, so the audit can be checked rather than trusted.
It is not equivalent to expert review and does not establish efficacy.

## Accomplishments we're proud of

- A verdict path where **arithmetic owns the decision** and the model is
  structurally unable to override it, including a fail-closed 502.
- Two implementations of one safety rule — Python and ClickHouse SQL — held to
  exact agreement by tests that run through the same read-only MCP transport the
  product uses.
- Every threshold traceable to a quoted published definition, and the one rule we
  did not implement named on the product surface rather than hidden.
- Publishing our own defects rather than a clean bill of health, with the
  measured cost of each one.
- A product about visual safety that holds itself to the same standard: nothing
  on the page flashes, no animation loops, all motion disabled under
  `prefers-reduced-motion`, and the visitor's OS colour preference is honoured
  rather than overridden with an unrequested full-screen jump to white.

## What we learned

- **Frame index is not a lineage key.** Anything that changes frame rate
  invalidates it. Presentation time is the only alignment that survives the
  transforms this product exists to audit.
- **Measure the step and the extent separately.** Averaging luminance change
  over the whole frame conflates "how big was the change" with "how much of the
  screen changed," and would let a partial-screen full-range flash slip under a
  delta floor while clearing the area floor.
- **A benchmark beats a best practice.** Twice: once where ClickHouse's guidance
  was right and we gained 3× by following it, once where it was wrong for our
  shape and we could only know by measuring.
- **A green test suite can be decorative.** `pytest-asyncio` was never
  installed, so every parity test was skipped rather than run, and the suite
  stayed green while proving nothing. `required_plugins` now makes that failure
  loud.

## What's next

Container decoding in front of the measurement stage (ffmpeg/PyAV), the spatial
pattern rule, and — most importantly — review by a qualified broadcast
accessibility or photosensitive-epilepsy professional. We have not had one, and
`docs/IMPACT.md` says so explicitly alongside everything else we have not shown:
no clinical validation, no comparison against a certified analyser, no real
footage.

## Built with

`google-adk` · `google-genai` · Gemini 2.5 Flash · Vertex AI · Cloud Run ·
Secret Manager · ClickHouse 26.3 LTS · `mcp-clickhouse` (official MCP server) ·
`clickhouse-connect` · Model Context Protocol · FastAPI · Pydantic · NumPy ·
Caddy · Docker · GitHub Actions

## Try it out

- Hosted app: https://safe-frame-regression-109051079423.us-central1.run.app
- Repository: https://github.com/usv240/safe-frame
- Shortest judge path: [`JUDGING.md`](https://github.com/usv240/safe-frame/blob/main/JUDGING.md)
- Threshold provenance: [`docs/CRITERIA.md`](https://github.com/usv240/safe-frame/blob/main/docs/CRITERIA.md)
- The case and its limits: [`docs/IMPACT.md`](https://github.com/usv240/safe-frame/blob/main/docs/IMPACT.md)

---

## Field-by-field checklist

- [ ] Partner track selected: **ClickHouse**
- [ ] Hosted project URL
- [ ] Public repository URL
- [ ] Public video URL (YouTube/Vimeo, ≤3:00, English or subtitled)
- [ ] Text description (features, functionality, technologies, data sources,
      findings and learnings) — all covered above
- [ ] Team members added on Devpost
- [ ] Every link opened signed out and confirmed working
- [ ] Repo license shows Apache-2.0 in the About section
- [ ] Submitted before **2026-09-09, 2:00 PM PT**
