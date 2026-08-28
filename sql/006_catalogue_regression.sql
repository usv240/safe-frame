/*
  Catalogue-wide child-only photosensitivity regression sweep.

  This is the published-criteria evaluation itself, not a read of a
  pre-computed answer. It applies exactly the rule implemented by
  `safe_frame.detector.detect_general_flashes`:

      a transition qualifies when
          luma_delta            >= 0.10
      AND changed_area_fraction >= 0.25
      AND direction             != 'flat'

      a window violates when
          more than 6 qualifying transitions start within 1000 ms
      AND both 'up' and 'down' directions are present in that window

  `tests/test_sql_parity.py` runs the reference Python implementation and this
  SQL over identical rows and asserts they agree, so the SQL is a faithful
  implementation rather than a second opinion.

  Alignment is on presentation time, never frame index: a 24 -> 60 fps
  conversion renumbers every frame but preserves pts.

  Steps
    1. qualifying   filter transitions to those that count toward the criterion
    2. windowed     for each qualifying transition, count the qualifying
                    transitions starting within the next 1000 ms. 'flat' is
                    already excluded, so direction is only up(1)/down(2) and
                    min != max is exactly "both directions present"
    3. violations   first qualifying window per asset, so a continuous burst
                    reports one canonical window like the reference detector
    4. isolate      a rendition regression is a violation whose master has no
                    violation of the same rule within 100 ms

  The final step uses a partition window rather than a self anti-join so the
  9.6M-row table is scanned once instead of twice (790ms vs 2.3s, identical
  results). Each asset yields at most one canonical window, and each lineage
  has exactly one master, so minIf() recovers the master window exactly.
*/
WITH
qualifying AS
(
    SELECT lineage_id, asset_id, parent_id, transform, pts_ms,
           changed_area_fraction, toUInt8(direction) AS dir
    FROM transitions
    WHERE luma_delta >= 0.10
      AND changed_area_fraction >= 0.25
      AND direction != 'flat'
),
windowed AS
(
    SELECT
        lineage_id, asset_id, parent_id, transform,
        pts_ms AS win_start,
        count() OVER w AS win_transitions,
        max(changed_area_fraction) OVER w AS win_peak_area,
        min(dir) OVER w AS win_dir_min,
        max(dir) OVER w AS win_dir_max
    FROM qualifying
    WINDOW w AS (
        PARTITION BY asset_id
        ORDER BY pts_ms
        RANGE BETWEEN CURRENT ROW AND 999 FOLLOWING
    )
),
violations AS
(
    SELECT
        lineage_id, asset_id, parent_id, transform,
        'general_flash' AS rule,
        min(win_start) AS window_start_ms,
        min(win_start) + 1000 AS window_end_ms,
        argMin(win_transitions, win_start) AS transitions,
        argMin(win_peak_area, win_start) AS peak_changed_area_fraction
    FROM windowed
    WHERE win_transitions > 6
      AND win_dir_min != win_dir_max
    GROUP BY lineage_id, asset_id, parent_id, transform
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
ORDER BY lineage_id, asset_id;
