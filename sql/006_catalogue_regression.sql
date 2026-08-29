/*
  Catalogue-wide child-only photosensitivity regression sweep.

  This is the published-criteria evaluation itself, not a read of a
  pre-computed answer. It applies exactly the rules implemented by
  `safe_frame.detector`:

      general_flash   luma_delta >= 0.10
                  AND luma_min   <  0.80   -- the darker image, per the standard
                  AND changed_area_fraction >= 0.25
                  AND direction != 'flat'

      red_flash       red_delta  >= 0.20
                  AND changed_area_fraction >= 0.25
                  AND direction != 'flat'

      a window violates when
          more than 6 qualifying transitions start within 1000 ms
      AND both 'up' and 'down' directions are present in that window

  The red rule carries NO luminance floor. A saturated-red alternation can hold
  luminance nearly flat and still be the higher-risk sequence, so a detector
  that only implements general flash passes it.

  Each rule is windowed over its own qualifying set, so one rule's transitions
  can never pad the other's count -- eight transitions in a second, four of each
  kind, is not a violation of either rule. The isolation step is likewise keyed
  on rule: a master that already flashed in luminance does not excuse a
  rendition that introduced a red flash.

  `tests/test_sql_parity.py` runs the reference Python implementation and this
  SQL over identical rows for both rules and asserts they agree, so the SQL is a
  faithful implementation rather than a second opinion.

  Alignment is on presentation time, never frame index: a 24 -> 60 fps
  conversion renumbers every frame but preserves pts.

  Steps, per rule
    1. qualifying   filter transitions to those that count toward that rule
    2. windowed     for each qualifying transition, count the qualifying
                    transitions starting within the next 1000 ms. 'flat' is
                    already excluded, so direction is only up(1)/down(2) and
                    min != max is exactly "both directions present"
    3. violations   first qualifying window per asset, so a continuous burst
                    reports one canonical window like the reference detector
  then, over both rules
    4. isolate      a rendition regression is a violation whose master has no
                    violation of the SAME rule within 100 ms

  Two measured shape decisions, both recorded in docs/CLICKHOUSE-SKILLS-REVIEW.md:

  * Step 4 uses a partition window rather than a self anti-join, so the
    violations set is built once instead of twice. Measured on the single-rule
    sweep at 9.6M vs 19.2M rows read and 791ms vs 2,274ms, identical results.
    Not re-measured since; the shape of the win is unchanged.

  * Step 1-3 deliberately run once per rule and UNION, against the
    `query-join-consider-alternatives` guidance. The single-scan alternative --
    filter once, then fan out to matching rules with ARRAY JOIN + arrayFilter --
    was built and measured against this exact query and is *slower*: median
    1,064ms vs 834ms over five runs, identical 44-row results.

    The rows-read column is the interesting part. Two passes over 9.6M rows
    should read 19.2M; it reads 10.26M, because per-granule min/max lets
    ClickHouse skip about 93% of the second scan -- no granule in most of the
    table can satisfy `red_delta >= 0.20`. The extra scan is nearly free, and
    unnesting a two-element array per surviving row is not.
*/
WITH
general_flash_qualifying AS
(
    SELECT lineage_id, asset_id, parent_id, transform, pts_ms,
           changed_area_fraction, toUInt8(direction) AS dir
    FROM transitions
    WHERE luma_delta >= 0.10
      -- "where the relative luminance of the darker image is below 0.80":
      -- a swing between two bright images is not a general flash
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
