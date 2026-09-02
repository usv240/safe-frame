/*
  What the corpus generator planted, derived without reference to the detector.

  The obvious objection to a synthetic demonstration is that it is circular:
  data was generated with bursts in it, and then the bursts were found. This
  query exists to make that objection answerable rather than rhetorical.

  `sql/005_catalogue_generator.sql` decides where to plant a regression using
  `sipHash64` over the title index and the transform name. Those decisions are
  deterministic and are made *before* any measurement exists, so the planted set
  can be recovered from the same hashes without evaluating a single criterion.
  Nothing here reads `luma_delta`, `red_delta`, `luma_min`,
  `changed_area_fraction` or `direction`. It reads only which assets exist and
  recomputes the coin flips.

  Comparing this against `sql/006_catalogue_regression.sql` is therefore a real
  measurement: an expected set and an observed set produced by independent
  means. `/v1/evaluation` reports the confusion matrix.

  The catalogue holds two cohorts and this covers both.

    title_NNNN     authored by sql/005: SQL decided what each measurement
                   should be and wrote it. Planted with sipHash64.
    measured_NNNN  measured by scripts/seed_measured_corpus.py: constructed RGB
                   frames pushed through safe_frame.ingest.frames_to_transitions,
                   so every value is the output of relative_luminance and
                   red_flash_mask over real pixel arrays rather than a chosen
                   number. Planted with plain arithmetic over the title index,
                   because reproducing sipHash64 in Python is awkward and the
                   point is recoverability, not which function does the
                   deciding.

  Three categories matter:

    expect_general    a luminance burst was planted in this rendition and NOT
                      in its master, so the sweep must return it
    expect_red        a saturated-red burst was planted the same way
    decoys            renditions that carry a burst which is NOT a regression,
                      and which the sweep must therefore NOT return:
                        - inherited: the master has the same burst at the same
                          presentation time, so the rendition introduced nothing
                        - bright: a full-amplitude luminance alternation where
                          both states sit above the published 0.80 darker-image
                          ceiling, so the general-flash test does not apply

  The decoys are the part that makes the measurement worth anything. Recall
  alone is easy to score by flagging everything; the decoys are what precision
  is measured against.

  One trap worth recording, because it produced a plausible and completely wrong
  answer for a while. `title_index` in the generator is a UInt64 (it comes from
  `intDiv` over `number`). Recovering it here with `toUInt32OrZero` produces a
  UInt32, and `sipHash64` hashes the two widths differently --
  `sipHash64(toUInt32(17), '60fps_interp') % 100` is 65 while
  `sipHash64(toUInt64(17), ...)` is 2. The cast below is load-bearing: without
  it this query returns a different random subset of the same size, and the
  comparison reports near-total disagreement while looking entirely legitimate.
*/
WITH assets AS
(
    SELECT DISTINCT
        lineage_id,
        asset_id,
        transform,
        startsWith(lineage_id, 'measured_') AS measured,
        -- must be UInt64 to match the generator's hash inputs; see above
        toUInt64(toUInt32OrZero(substring(lineage_id, if(measured, 10, 7)))) AS title_index
    FROM transitions
    WHERE transform != 'master'
),
planted AS
(
    SELECT
        lineage_id,
        asset_id,
        transform,
        measured,
        -- authored cohort: sipHash64, as sql/005 decided it
        -- measured cohort: plain arithmetic, as scripts/seed_measured_corpus.py did
        if(measured, (title_index % 11) = 3,
                     (sipHash64(title_index, 'inherited') % 100) < 1) AS lineage_burst,
        if(measured, (title_index % 13) = 5,
                     (sipHash64(title_index, 'red_inherited') % 100) < 1) AS lineage_red,
        transform IN ('60fps_interp', 'adbreak_insert')
            AND if(measured, (title_index % 4) = 0,
                             (sipHash64(title_index, transform) % 100) < 4)
            AND NOT lineage_burst AS expect_general,
        transform IN ('social_crop_v', 'subtitle_burnin')
            AND if(measured, (title_index % 5) = 1,
                             (sipHash64(title_index, transform, 'red') % 100) < 3)
            AND NOT lineage_red AS expect_red,
        transform = 'hdr10_passthrough'
            AND if(measured, (title_index % 6) = 2,
                             (sipHash64(title_index, 'bright') % 100) < 3) AS bright_decoy
    FROM assets
)
SELECT
    asset_id,
    transform,
    measured,
    expect_general,
    expect_red,
    bright_decoy,
    (lineage_burst OR lineage_red) AS inherited_decoy
FROM planted
WHERE expect_general OR expect_red OR bright_decoy OR lineage_burst OR lineage_red
ORDER BY asset_id;
