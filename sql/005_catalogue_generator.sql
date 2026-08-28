/*
  Self-authored synthetic distribution catalogue, generated server-side.

  This is NOT real footage and is not presented as such. It is a reproducible
  stand-in for the shape and volume of a studio delivery catalogue, so that the
  published-criteria evaluation and the parent/child anti-join are exercised at
  realistic scale instead of on a single constructed pair.

  Shape
    400 titles x 8 renditions            = 3,200 assets
    120 seconds at 25 transitions/second = 3,000 rows per asset
    total                                = 9,600,000 transition rows

  Ground truth, deterministic by sipHash64 so the corpus is reproducible:

    baseline          One qualifying transition every 6th sample (~4.2/second).
                      Below the >6-per-second criterion, so clean content never
                      trips the rule.

    introduced burst  ~4% of titles get a saturated 1-second burst in their
                      `60fps_interp` and/or `adbreak_insert` rendition only.
                      The approved master stays clean, so these ARE child-only
                      regressions and must be returned by the anti-join.

    inherited burst   ~1% of titles get the burst in the MASTER, propagated to
                      every rendition at the same presentation time. These are
                      NOT regressions -- the rendition introduced nothing -- and
                      the anti-join must exclude them. Without this control the
                      anti-join would look correct while doing nothing.

  Re-running is safe: the INSERT is deterministic in the row index, so
  TRUNCATE + re-run reproduces byte-identical content.
*/

INSERT INTO transitions
SELECT
    asset_id,
    lineage_id,
    parent_id,
    transform,
    pts_ms,
    luma_delta,
    red_delta,
    changed_area_fraction,
    direction
FROM
(
    WITH
        -- decompose the flat row index into (title, rendition, sample)
        number AS idx,
        intDiv(idx, 3000) AS asset_index,
        toUInt32(idx % 3000) AS seq,
        intDiv(asset_index, 8) AS title_index,
        toUInt8(asset_index % 8) AS transform_index,
        ['master', 'sdr_tonemap', '1080p_downscale', '60fps_interp',
         'social_crop_v', 'adbreak_insert', 'subtitle_burnin', 'hdr10_passthrough'] AS transform_names,
        transform_names[transform_index + 1] AS transform,
        concat('title_', leftPad(toString(title_index), 4, '0')) AS lineage_id,
        concat(lineage_id, '__', transform) AS asset_id,
        if(transform = 'master', '', concat(lineage_id, '__master')) AS parent_id,
        toUInt32(seq * 40) AS pts_ms,

        -- which second, if any, carries a burst for this lineage
        (sipHash64(title_index, 'inherited') % 100) < 1 AS lineage_burst,
        toUInt32(30 + (sipHash64(title_index, 'when') % 60)) AS burst_second,
        transform IN ('60fps_interp', 'adbreak_insert') AS burst_capable,
        (sipHash64(title_index, transform) % 100) < 4 AS introduced_burst,
        (lineage_burst OR (burst_capable AND introduced_burst)) AS asset_has_burst,
        intDiv(pts_ms, 1000) = burst_second AS in_burst_window,
        asset_has_burst AND in_burst_window AS bursting,

        -- deterministic per-sample noise
        sipHash64(title_index, transform_index, seq) AS h,
        (h % 10000) / 10000.0 AS r,

        -- baseline: one qualifying transition every 6th sample (~4.2/second),
        -- which sits below the >6-per-second criterion
        (seq % 6) = 0 AS qualifying_baseline
    SELECT
        asset_id,
        lineage_id,
        parent_id,
        transform,
        pts_ms,
        toFloat32(multiIf(
            bursting,            0.34 + (r * 0.22),
            qualifying_baseline, 0.12 + (r * 0.30),
                                 r * 0.09)) AS luma_delta,
        toFloat32(multiIf(
            bursting,            0.05 + (r * 0.10),
            qualifying_baseline, 0.02 + (r * 0.08),
                                 r * 0.03)) AS red_delta,
        toFloat32(multiIf(
            bursting,            0.52 + (r * 0.30),
            qualifying_baseline, 0.28 + (r * 0.38),
                                 r * 0.22)) AS changed_area_fraction,
        multiIf(
            bursting OR qualifying_baseline, if((seq % 2) = 0, 'up', 'down'),
            (h % 3) = 0,                     'flat',
            if((seq % 2) = 0, 'up', 'down')) AS direction
    FROM numbers_mt(9600000)
);
