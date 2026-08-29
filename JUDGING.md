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
5. Press **Ask the ADK agent**. It must retrieve evidence through MCP; confirm
   `decision_source` stays `clickhouse_sql` and `requires_human` stays `true`.
6. Open `/health`; all four runtime checks should be true.

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
| Technological Implementation | The sweep, then MCP evidence, then an explanation | Two rules windowed independently in one pass, presentation-time lineage, live SQL isolation, request-bound ADK evidence, fail-closed behaviour |
| Design | `/` in Plain mode, then Technical mode | One coherent non-flashing path for an editor and for an engineering judge |
| Potential Impact | The red-flash rows and `docs/IMPACT.md` | A rendition that introduced a risk its approved master never had, invisible to a luminance-only check and to any per-file QC that never compares versions. `IMPACT.md` carries the sourced case *and* an explicit list of what has not been shown |
| Quality of Idea | `docs/PRIOR-ART.md` and `docs/CRITERIA.md` | Detection, repair, dimming and batch scale are conceded; the narrow public gap is lineage regression, and every threshold traces to a quoted WCAG 2.3.1 definition |

The catalogue is self-authored synthetic measurement, not footage, and contains no
flashing media. Safe Frame is not a certified device and makes no medical efficacy
claim.
