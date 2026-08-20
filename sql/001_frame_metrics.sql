CREATE TABLE IF NOT EXISTS frame_metrics
(
    asset_id LowCardinality(String),
    lineage_id LowCardinality(String),
    parent_id LowCardinality(String),
    transform LowCardinality(String),
    frame_idx UInt32,
    pts_ms UInt32,
    tile_x UInt8,
    tile_y UInt8,
    luma Float32,
    red_sat Float32,
    pattern_score Float32,
    area_frac Float32
)
ENGINE = MergeTree
ORDER BY (lineage_id, asset_id, pts_ms, tile_y, tile_x);
