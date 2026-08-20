/*
  Presentation time—not frame index—is the alignment key because renditions may
  use different frame rates. This is a child-minus-parent anti-join.
  `violations` is materialized by the published-criteria window query.
*/
WITH
parent AS
(
    SELECT lineage_id, asset_id, rule, window_start_ms
    FROM violations
    WHERE asset_id = {parent_asset:String}
),
child AS
(
    SELECT lineage_id, asset_id, parent_id, transform, rule, window_start_ms,
           transitions, peak_changed_area_fraction
    FROM violations
    WHERE asset_id = {child_asset:String}
)
SELECT child.*
FROM child
LEFT ANTI JOIN parent
    ON child.lineage_id = parent.lineage_id
   AND child.rule = parent.rule
   AND abs(toInt64(child.window_start_ms) - toInt64(parent.window_start_ms)) <= 100
ORDER BY child.window_start_ms;
