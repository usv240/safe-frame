# ClickHouse Agent Skills review

The official ClickHouse Agent Skills are vendored at
[`.claude/skills/clickhouse-best-practices`](../.claude/skills/clickhouse-best-practices)
(`clickhouse-best-practices` v0.4.0, Apache-2.0, 33 rules) and were applied to
Safe Frame's schema and its catalogue query.

This records what each applicable rule said, what was measured, and what changed.
Four rules were checked and deliberately **not** applied, each with the
measurement that justified declining it — including both Materialized View
rules, one of which is 158x faster than what ships and is still not enabled, for
a reason stated in full below. A review where every rule "passed" would not be
worth publishing.

The table at the end accounts for all 31 rules, so a reader can confirm none was
quietly skipped.

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
rather than obeyed. The sweep evaluates each rule over its own qualifying set and
`UNION ALL`s the two. The single-scan alternative was built and benchmarked:
filter once with the union of both predicates, then fan each surviving row out to
the rules it satisfies with
`ARRAY JOIN arrayFilter((name, keep) -> keep, ['general_flash','red_flash'], [...])`,
windowed `PARTITION BY asset_id, rule`.

Five runs of each against the live cluster, re-measured against the current sweep
after the darker-image condition was added, `system` statistics read from the same
response as the rows:

| | rows read | median | min | max |
|---|---|---|---|---|
| two passes, `UNION ALL` (shipped) | 10,263,552 | **834 ms** | 756 ms | 939 ms |
| one pass, `ARRAY JOIN` fan-out | 9,600,000 | 1,064 ms | 989 ms | 1,353 ms |

Identical 44-row results from both. The single-scan form is **27% slower**.

The interesting part is the rows-read column, and it is not what the rule
predicts. "Two passes" over a 9.6M-row table should read 19.2M rows. It reads
10.26M. The second pass — the red predicate — reads only about 664,000 rows,
because ClickHouse keeps per-granule min/max for every column and can skip a
granule outright when no row in it can satisfy `red_delta >= 0.20`. The red
cohort is a small, clustered fraction of the corpus, so roughly 93% of the second
scan never happens.

So the premise the rule is defending against does not hold here: the extra scan
is nearly free, while unnesting a two-element array for every row that survives
the combined filter is not. The rule is sound advice and the measurement still
contradicted it, so the two-pass form ships.

This also keeps the two rules independent by construction rather than by a
`PARTITION BY ..., rule` clause somebody could later drop, which matters more
than the milliseconds: if one rule's transitions ever padded the other's window,
the sweep would report violations that neither rule actually supports.


### `query-mv-refreshable` (HIGH) — applicable, built, measured, deliberately not enabled

> Use refreshable MVs for complex joins and batch workflows.

The sweep is a fixed, expensive query that people would reload all day. That is
exactly the shape this rule is for, so it was built rather than argued about.
`sql/007_refreshable_regressions.sql` is the view, and one refresh takes about a
second.

| reading | rows read | median |
|---|---:|---:|
| the refreshable view | 44 | **5.9 ms** |
| `sql/006` evaluated live | 10,263,552 | 932 ms |

Identical 44-row output. About **158x faster**, and the rule is plainly right for
a production dashboard.

It is not enabled on the deployed cluster, and the reason is a product
constraint rather than a technical one. Safe Frame's landing page claims that
nothing on it is a pre-computed answer: press the button and the criteria are
evaluated in front of you, with the elapsed time reported. Serving that button
from a view refreshed five minutes ago would make the demonstration a lookup and
the claim false. Five minutes of staleness is fine for an operations dashboard
and wrong for "this was computed just now".

The DDL ships so a real deployment can create it in one statement. The
demonstration keeps paying the 932ms on purpose.

### `query-mv-incremental` (HIGH) — measured as not applicable to this criterion

> Incremental MVs apply the view's query to new data blocks at insert time.

The obvious shape is a target table of qualifying transitions per
`(asset_id, rule, second)`, maintained at insert time, with the sweep reading
that instead of the raw table. A violating 1000 ms window overlaps at most two
one-second buckets, so `count(s) + count(s+1) > 6` is a sound necessary
condition and would be a cheap pre-filter.

It does not work here, and the measurement says why:

```
total second buckets                     383,958
buckets surviving count(s)+count(s+1) > 6 380,758
                                            99.2%
```

The pre-filter eliminates **0.8%** of the search space. Normal content in this
corpus runs at about 4.2 qualifying transitions per second — deliberately just
under the criterion — so two adjacent seconds sum to roughly 8 or 9 and clear a
threshold of 6 almost everywhere. The criterion is a *rolling* window over data
that is dense just below the limit, which is the case a bucketed pre-aggregation
cannot help with.

A rolling window also cannot be maintained incrementally in the first place: an
incremental MV sees one insert block at a time and a window can span blocks, so
the exact answer is not expressible as a per-block aggregate regardless of
selectivity.

Declined on the measurement, not on the difficulty.

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


## Every remaining rule, and where it landed

The rules above are the ones that changed something or that a measurement
settled. This table accounts for the rest, so a reader can check that none was
simply skipped. 31 rules; the ten written up above are marked *(above)*.

| Rule | Status |
|---|---|
| `agent-connect-mcp` | **Followed.** The product connects only through the official `mcp-clickhouse` server, started read-only over stdio. `safe_frame/clickhouse_mcp.py`. |
| `agent-discovery-schema` | **Followed.** `/v1/integrations/clickhouse/evidence` calls `list_tables`/`list_databases` alongside `run_query`, and the page shows what the server advertised. |
| `agent-query-safety` | *(above)* |
| `insert-async-small-batches` | **Not applicable.** Ingest is one batch per scan through `clickhouse-connect`, not a stream of small writes. Async inserts would add latency to a request that already waits on the batch. |
| `insert-batch-size` | **Followed by construction.** The catalogue is generated server-side by a single `INSERT ... SELECT FROM numbers_mt`, so ClickHouse chooses the block size. `/v1/scan` writes one batch per request, at most a few rows. |
| `insert-format-native` | **Followed.** `clickhouse-connect`'s `insert()` uses the native protocol; no CSV or JSON parsing on the write path. |
| `insert-mutation-avoid-delete` | **Followed.** Nothing issues `ALTER TABLE ... DELETE`. The catalogue is rebuilt with `TRUNCATE` plus a deterministic regenerate, which is a partition drop rather than a mutation. |
| `insert-mutation-avoid-update` | **Followed.** Nothing issues `ALTER TABLE ... UPDATE`. `violations` is a `ReplacingMergeTree` keyed on `(lineage_id, asset_id, rule, window_start_ms)`, so a re-scan supersedes rather than mutates. |
| `insert-optimize-avoid-final` | *(above)* |
| `query-index-skipping-indices` | *(above)* — and see the granule-skipping measurement under `query-join-consider-alternatives`, which is the same mechanism arriving without an explicit index. |
| `query-join-choose-algorithm` | **Not applicable.** The sweep has no join left in it; the isolation step is a partition window. The only join is the per-pair `LEFT ANTI JOIN` over at most a handful of rows, where the algorithm cannot matter. |
| `query-join-consider-alternatives` | *(above, twice — applied once, declined once)* |
| `query-join-filter-before` | **Followed.** Both sides of the per-pair anti-join are filtered to two `asset_id` values inside their CTEs before the join. |
| `query-join-null-handling` | **Relevant and acted on.** The transform-risk query's `LEFT JOIN` fills misses with an empty `LowCardinality(String)` rather than NULL, so `countDistinct` counted a regression that clean transforms did not have. Fixed with `countDistinctIf(..., asset_id != '')`. |
| `query-join-use-any` | **Not applicable.** No join here wants first-match semantics; the anti-join needs every parent row considered. |
| `query-mv-incremental` | *(above)* |
| `query-mv-refreshable` | *(above)* |
| `schema-json-when-to-use` | **Not applicable.** Every column is a known scalar. There is no semi-structured payload, so the JSON type would cost storage and clarity for nothing. |
| `schema-partition-lifecycle` | **Not applicable.** There is no TTL or drop-by-age requirement; the corpus is a fixed reproducible set. |
| `schema-partition-low-cardinality` | **Followed by not partitioning.** See `schema-partition-start-without`. |
| `schema-partition-query-tradeoffs` | **Considered.** Partitioning by `lineage_id` would give 400 partitions over 9.6M rows, roughly 24k rows each — far below the guidance's floor, and the sweep reads every title anyway, so it would add parts without removing work. |
| `schema-partition-start-without` | *(above)* |
| `schema-pk-cardinality-order` | *(above)* |
| `schema-pk-filter-on-orderby` | **Followed.** `ORDER BY (lineage_id, asset_id, pts_ms)`; the per-pair query filters on `asset_id` and the timeline groups on `pts_ms`, both inside the key. |
| `schema-pk-plan-before-creation` | **Followed.** The key was chosen for the parent/child alignment the product exists to do, before the table was created; `sql/004` records the reasoning in the file. |
| `schema-pk-prioritize-filters` | **Followed.** `lineage_id` and `asset_id` lead the key because every query filters or groups on them. |
| `schema-types-avoid-nullable` | **Followed.** No column in either table is `Nullable`; absence is represented by an empty `LowCardinality(String)` for `parent_id` on masters. |
| `schema-types-enum` | *(above)* |
| `schema-types-lowcardinality` | *(above)* |
| `schema-types-minimize-bitwidth` | **Partly followed, one deliberate exception.** `pts_ms` is `UInt32`, `transitions` `UInt16`, `direction` `Enum8`. All five measurement columns are `Float32` rather than `Float64`, which is the narrower choice; going narrower still (a fixed-point `UInt16`) would save 2 bytes per column and put rounding between the Python detector and the SQL, which the parity tests would then have to tolerate. Not worth it. |
| `schema-types-native-types` | **Followed.** Times are numeric `pts_ms` because presentation time is a media offset, not a wall-clock instant; `observed_at` on `violations` is a real `DateTime64(3, 'UTC')`. |

## Limitations

These skills are development-time guidance for a coding agent, not a runtime
dependency, and using them is optional under the hackathon rules. The measurements
above come from a single self-hosted ClickHouse 26.3 node on GCP with noisy timing;
the interleaved medians are trustworthy to roughly ±10%, which is why a 6 ms
difference was read as noise rather than a result.
