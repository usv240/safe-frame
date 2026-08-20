CREATE TABLE IF NOT EXISTS violations
(
    asset_id LowCardinality(String),
    lineage_id LowCardinality(String),
    parent_id LowCardinality(String),
    transform LowCardinality(String),
    rule LowCardinality(String),
    window_start_ms UInt32,
    window_end_ms UInt32,
    transitions UInt16,
    peak_changed_area_fraction Float32,
    observed_at DateTime64(3, 'UTC') DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(observed_at)
ORDER BY (lineage_id, asset_id, rule, window_start_ms);
