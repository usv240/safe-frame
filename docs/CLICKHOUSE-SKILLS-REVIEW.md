# ClickHouse Agent Skills review

The official ClickHouse Agent Skills are vendored at
[`.claude/skills/clickhouse-best-practices`](../.claude/skills/clickhouse-best-practices)
(`clickhouse-best-practices` v0.4.0, Apache-2.0, 33 rules) and were applied to
Safe Frame's schema and its catalogue query.

This records what each applicable rule said, what was measured, and what changed.
Three rules were checked and deliberately **not** applied, with the measurement
that justified declining them. A review where every rule "passed" would not be worth
publishing.

Reviewed: 2026-08-28, against `sql/004_transitions.sql` and
`sql/006_catalogue_regression.sql`.

---

## Applied

### `query-join-consider-alternatives` (CRITICAL)

> Repeated JOINs add overhead; shift work away from query time.

The catalogue sweep originally isolated child-only violations with a
`LEFT ANTI JOIN` of the violations CTE against itself. Because ClickHouse inlines
CTEs rather than materialising them, the 9.6M-row table was read **twice**.

Replaced with a partition window (`minIf(...) OVER (PARTITION BY lineage_id, rule)`),
which is sound here because each asset yields at most one canonical window and each
lineage has exactly one master.

| | rows read | elapsed |
|---|---|---|
| self anti-join | 19,200,000 | 2,274 ms |
| partition window | 9,600,000 | 791 ms |

Identical 31-row result, verified byte-for-byte against the anti-join output.

### `schema-types-enum` (compliant as built)

`direction` is `Enum8('flat', 'up', 'down')` rather than a String. This also makes
the criteria cheaper: because `'flat'` is filtered out first, "both directions
present" reduces to `min(dir) != max(dir)` over the window.

### `schema-types-lowcardinality` (compliant as built)

All four string columns are `LowCardinality` and all are well under the 10,000
threshold the rule sets: `transform` 8, `lineage_id` 400, `parent_id` 401,
`asset_id` 3,200 distinct values.

### `agent-query-safety` (compliant as built)

Reads go through the official `mcp-clickhouse` server with
`CLICKHOUSE_ALLOW_WRITE_ACCESS=false` and `CLICKHOUSE_ALLOW_DROP=false`, using a
SELECT-only database user distinct from the ingest user. Failures surface as HTTP
502 rather than a fallback result.

---

## Checked and deliberately not applied

### `query-join-consider-alternatives`, declined the second time (CRITICAL)

> Repeated JOINs add overhead; shift work away from query time.

Adding the red-flash rule made this rule point the other way, so it was measured
rather than obeyed. The sweep now evaluates each rule over its own qualifying
set and `UNION ALL`s the two, which scans the 9.6M-row table twice. The
single-scan alternative was built and benchmarked: filter once with the union of
both predicates, then fan each surviving row out to the rules it satisfies with
`ARRAY JOIN arrayFilter((name, keep) -> keep, ['general_flash','red_flash'], [...])`,
windowed `PARTITION BY asset_id, rule`.

Five runs of each against the live cluster, `system` statistics from the same
response as the rows:

| | rows read | median | min | max |
|---|---|---|---|---|
| two passes, `UNION ALL` (shipped) | 19,200,000 | **703 ms** | 672 ms | 851 ms |
| one pass, `ARRAY JOIN` fan-out | 9,600,000 | 1,096 ms | 1,006 ms | 1,141 ms |

Byte-identical 31-row results from both. Halving the rows read made the query
**56% slower**: the red predicate is selective enough that its extra scan is
nearly free, while unnesting a two-element array for every row that survives the
combined filter is not. The rule is sound advice and the measurement still
contradicted it here, so the two-pass form ships.

This also keeps the two rules independent by construction rather than by a
`PARTITION BY ..., rule` clause somebody could later drop, which matters more
than the milliseconds: if one rule's transitions ever padded the other's window,
the sweep would report violations that neither rule actually supports.

### `schema-pk-cardinality-order` (CRITICAL) — declined, no measurable benefit

The rule says order the sorting key from low to high cardinality. Ours is
`ORDER BY (lineage_id, asset_id, pts_ms)` — 400, then 3,200, then 3,000 distinct.

`EXPLAIN PLAN` showed ClickHouse inserting `Sorting (Sorting for window 'PARTITION BY
asset_id ORDER BY pts_ms')` — the table's existing order was not being reused for the
window. That suggested a sorting key matching the window key exactly might remove the
sort.

So it was measured rather than assumed. A copy of the table with
`ORDER BY (asset_id, pts_ms)` was built and the sweep run against both, interleaved
six times each to control for drift on a shared host:

| sorting key | min | median | mean | max |
|---|---|---|---|---|
| `(lineage_id, asset_id, pts_ms)` | 671 ms | **686 ms** | 843 ms | 1335 ms |
| `(asset_id, pts_ms)` | 647 ms | **680 ms** | 682 ms | 724 ms |

A 6 ms median difference is noise. The alternative was more *consistent* (tighter
max), but not faster, and the current key additionally keeps a lineage contiguous,
which the per-pair `/v1/scan` path filters on. Not worth a migration. The experiment
table was dropped.

### `query-index-skipping-indices` — not applicable

A `minmax` skip index on `luma_delta` would let granules be skipped where no value
clears the 0.10 floor. It would do nothing here: the generator places a qualifying
transition every 6th sample, so every 8192-row granule contains qualifying rows and
none can be skipped. Adding the index would cost storage and skip nothing.

### `insert-optimize-avoid-final` — not a finding

`regression_sql` reads `FROM safe_frame.violations FINAL`. The rule is about
`OPTIMIZE TABLE ... FINAL`, and states explicitly that the `FINAL` *modifier* in a
SELECT against a `ReplacingMergeTree` "may be necessary for deduplicated results and
is generally fine to use". `violations` is a `ReplacingMergeTree`, so this stays.

### `schema-partition-start-without` — compliant

`transitions` has no `PARTITION BY`. The rule advises starting without partitioning
absent a data-lifecycle requirement, and there is none: the corpus is regenerated
rather than aged out.

---

## Limitations

These skills are development-time guidance for a coding agent, not a runtime
dependency, and using them is optional under the hackathon rules. The measurements
above come from a single self-hosted ClickHouse 26.3 node on GCP with noisy timing;
the interleaved medians are trustworthy to roughly ±10%, which is why a 6 ms
difference was read as noise rather than a result.
