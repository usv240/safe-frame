# Judge path

## Stage-one viability

- Track: ClickHouse.
- Public web product: <https://safe-frame-regression-109051079423.us-central1.run.app>.
- Google runtime: `/health` performs a real Vertex AI generation with Gemini 2.5 Flash;
  `/v1/explain` runs a Google ADK `LlmAgent` on Vertex.
- Mandatory partner runtime: every catalogue read and every verdict goes through the
  official `ClickHouse/mcp-clickhouse` server in read-only stdio mode against a live
  self-hosted ClickHouse 26.3 LTS cluster. `/v1/integrations/clickhouse/evidence`
  shows the advertised tools and a live query.
- Repository and detected Apache-2.0 licence: <https://github.com/usv240/safe-frame>.
- Public video and final Devpost confirmation remain release actions; they are not
  represented as complete.

## Ninety-second test

1. Open `/`. The four counters are read live from ClickHouse through official MCP.
2. Press **Sweep the catalogue**. Both published rules are evaluated across
   9,600,000 transition rows in one pass, and the master/rendition isolation happens
   inside the same query. The header reports how many rows were scanned, how many
   were returned, and the ClickHouse time.
3. Read the **Rule** column. `General flash` is the luminance rule. `Red flash` is a
   saturated-red alternation whose luminance change stays *under* the general-flash
   floor — a luminance-only checker passes those renditions. The two rules are
   attributed to different transforms, so the table shows which conversion did what.
4. Look at the evidence chart. Both tracks come from one query over one table on a
   shared scale: the approved master stays under the criterion for its whole runtime,
   and the rendition crosses it in one second. Pick a **red flash** row and note that
   its general-flash track never moves — that is the case a luminance-only check
   passes. The same numbers are available as a table under the chart.
5. Scroll to **Systemic cause** and press *Profile every transform*. Four encoder
   profiles account for every finding and three transforms introduce nothing — so
   this is a small number of upstream fixes rather than 44 renditions to patch.
   Note that the two rules cluster on *different* profiles.
6. Scroll to **The agent's mission** and press *Run the triage agent*. It takes
   about twenty seconds because it really is running four ClickHouse queries. The
   numbered trace beside the brief is recorded from the run: confirm four distinct
   tools, and that `decision_source` stays `clickhouse_sql` and `requires_human`
   stays `true`.
7. Open `/health`; all four runtime checks should be true.

## Verifying the verdict is not theatre

| Claim | Check it here |
|---|---|
| The sweep is computed, not looked up | `sql/006_catalogue_regression.sql` is the query that runs; `/v1/catalogue/sweep` returns its timing |
| SQL agrees with the reference detector | `tests/test_sql_parity.py` runs both over identical randomized rows for both rules; `tests/test_clickhouse_mcp.py` guards the thresholds without a cluster |
| Inherited violations are not counted | `sql/005_catalogue_generator.sql` seeds control cohorts whose *master* already flashes; the sweep must exclude them |
| The model cannot decide | `/v1/explain` returns `decision_source: clickhouse_sql`; if MCP or the SQL fails, the API returns 502 rather than a guess |
| Every surface agrees | `/v1/catalogue/regressions?parent_asset=…&child_asset=…` returns the same verdict as the row you clicked |

## Four equal judging criteria

| Criterion | Inspect this | What it proves |
|---|---|---|
| Technological Implementation | The sweep, the transform profile, then the triage agent; `docs/CLICKHOUSE-SKILLS-REVIEW.md` for all 31 official rules with measurements | Two rules windowed independently in one pass, presentation-time lineage, live SQL isolation, a genuinely multi-step ADK agent whose four tools are all read-only MCP queries, fail-closed behaviour |
| Design | `/` in Plain mode, then Technical mode | One coherent non-flashing path from problem to evidence to root cause to action, for an editor and for an engineering judge. Verified at phone, laptop and desktop widths in both themes by `scripts/visual_check.py` |
| Potential Impact | The systemic-cause section, the red-flash rows, and `docs/IMPACT.md` | A rendition that introduced a risk its approved master never had, invisible to a luminance-only check and to any per-file QC that never compares versions. The finding is actionable rather than merely alarming: four profiles, two root causes, thirteen findings a luminance-only checker misses. `IMPACT.md` carries the sourced case *and* an explicit list of what has not been shown |
| Quality of Idea | `docs/PRIOR-ART.md` and `docs/CRITERIA.md` | Detection, repair, dimming and batch scale are conceded; the narrow public gap is lineage regression, and every threshold traces to a quoted WCAG 2.3.1 definition |

The catalogue is self-authored synthetic measurement, not footage, and contains no
flashing media. Safe Frame is not a certified device and makes no medical efficacy
claim.
