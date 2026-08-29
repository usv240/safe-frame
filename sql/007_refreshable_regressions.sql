/*
  The production path for the catalogue sweep, and the reason the demo does not
  use it.

  `sql/006_catalogue_regression.sql` evaluates the published criteria across
  every transition in the catalogue on every call. Measured on the live cluster
  that is ~932ms and 10,263,552 rows read. For a dashboard that several people
  reload all day, re-deriving a fixed answer per request is the wrong shape, and
  ClickHouse's own guidance says so (`query-mv-refreshable`, impact HIGH).

  This is that view. Creating it and letting one refresh land:

      | reading                              | rows read  | median |
      |--------------------------------------|-----------:|-------:|
      | this view                            |         44 |  5.9ms |
      | sql/006 evaluated live               | 10,263,552 |  932ms |

      Identical 44-row output. About 158x faster.

  It is deliberately NOT enabled on the deployed cluster.

  Safe Frame's claim on its own landing page is that nothing there is a
  pre-computed answer -- press the button and the criteria are evaluated in
  front of you. Serving that button from a view refreshed five minutes ago would
  make the demonstration a lookup, and the claim false. Five minutes of
  staleness is entirely acceptable for an operations dashboard and entirely
  unacceptable for "this was computed just now, and here is how long it took".

  So the trade is stated rather than taken: a real deployment watching a live
  catalogue should create this and read from it, and accept that what it reads
  is up to one refresh interval old. A demonstration whose point is the
  computation should not.

  Requires CREATE privileges. The MCP user is SELECT-only by design and cannot
  create it; run this as the ingest identity.

  Note the refresh interval against the query cost: the guidance warns not to
  schedule a refresh faster than the query takes. At ~1s per refresh, five
  minutes is three orders of magnitude of headroom.
*/
CREATE MATERIALIZED VIEW IF NOT EXISTS safe_frame.catalogue_regressions_mv
REFRESH EVERY 5 MINUTE
ENGINE = MergeTree()
ORDER BY (lineage_id, asset_id, rule)
AS
/* the body is sql/006_catalogue_regression.sql, unchanged --
   keep them identical or the view stops meaning what the sweep means */
WITH
general_flash_qualifying AS
(
    SELECT lineage_id, asset_id, parent_id, transform, pts_ms,
           changed_area_fraction, toUInt8(direction) AS dir
    FROM transitions
    WHERE luma_delta >= 0.10
      AND luma_min < 0.80
      AND changed_area_fraction >= 0.25
      AND direction != 'flat'
),
general_flash_windowed AS
(
    SELECT
        lineage_id, asset_id, parent_id, transform,
        pts_ms AS win_start,
        count() OVER w AS win_transitions,
        max(changed_area_fraction) OVER w AS win_peak_area,
        min(dir) OVER w AS win_dir_min,
        max(dir) OVER w AS win_dir_max
    FROM general_flash_qualifying
    WINDOW w AS (
        PARTITION BY asset_id
        ORDER BY pts_ms
        RANGE BETWEEN CURRENT ROW AND 999 FOLLOWING
    )
),
general_flash_violations AS
(
    SELECT
        lineage_id, asset_id, parent_id, transform,
        'general_flash' AS rule,
        min(win_start) AS window_start_ms,
        min(win_start) + 1000 AS window_end_ms,
        argMin(win_transitions, win_start) AS transitions,
        argMin(win_peak_area, win_start) AS peak_changed_area_fraction
    FROM general_flash_windowed
    WHERE win_transitions > 6
      AND win_dir_min != win_dir_max
    GROUP BY lineage_id, asset_id, parent_id, transform
),
red_flash_qualifying AS
(
    SELECT lineage_id, asset_id, parent_id, transform, pts_ms,
           changed_area_fraction, toUInt8(direction) AS dir
    FROM transitions
    WHERE red_delta >= 0.20
      AND changed_area_fraction >= 0.25
      AND direction != 'flat'
),
red_flash_windowed AS
(
    SELECT
        lineage_id, asset_id, parent_id, transform,
        pts_ms AS win_start,
        count() OVER w AS win_transitions,
        max(changed_area_fraction) OVER w AS win_peak_area,
        min(dir) OVER w AS win_dir_min,
        max(dir) OVER w AS win_dir_max
    FROM red_flash_qualifying
    WINDOW w AS (
        PARTITION BY asset_id
        ORDER BY pts_ms
        RANGE BETWEEN CURRENT ROW AND 999 FOLLOWING
    )
),
red_flash_violations AS
(
    SELECT
        lineage_id, asset_id, parent_id, transform,
        'red_flash' AS rule,
        min(win_start) AS window_start_ms,
        min(win_start) + 1000 AS window_end_ms,
        argMin(win_transitions, win_start) AS transitions,
        argMin(win_peak_area, win_start) AS peak_changed_area_fraction
    FROM red_flash_windowed
    WHERE win_transitions > 6
      AND win_dir_min != win_dir_max
    GROUP BY lineage_id, asset_id, parent_id, transform
),
violations AS
(
    SELECT * FROM general_flash_violations
    UNION ALL
    SELECT * FROM red_flash_violations
)
SELECT
    lineage_id,
    asset_id,
    parent_id,
    transform,
    rule,
    window_start_ms,
    window_end_ms,
    transitions,
    round(peak_changed_area_fraction, 4) AS peak_changed_area_fraction
FROM
(
    SELECT
        *,
        minIf(window_start_ms, transform = 'master') OVER lineage AS master_ws,
        countIf(transform = 'master') OVER lineage AS master_hits
    FROM violations
    WINDOW lineage AS (PARTITION BY lineage_id, rule)
)
WHERE transform != 'master'
  AND (master_hits = 0 OR abs(toInt64(window_start_ms) - toInt64(master_ws)) > 100)
ORDER BY lineage_id, asset_id, rule;
