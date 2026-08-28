/*
  Catalogue-scale transition measurements.

  One row per measured transition, per asset. `frame_metrics` holds raw
  per-tile samples; this table holds the transition-level reduction that the
  published-criteria window query actually evaluates.

  Every rendition of a title shares its `lineage_id`, so the parent/child
  anti-join can run across the whole catalogue in a single query rather than
  one file at a time.
*/
CREATE TABLE IF NOT EXISTS transitions
(
    asset_id LowCardinality(String),
    lineage_id LowCardinality(String),
    parent_id LowCardinality(String),
    transform LowCardinality(String),
    pts_ms UInt32,
    luma_delta Float32,
    red_delta Float32,
    changed_area_fraction Float32,
    direction Enum8('flat' = 0, 'up' = 1, 'down' = 2)
)
ENGINE = MergeTree
ORDER BY (lineage_id, asset_id, pts_ms);
