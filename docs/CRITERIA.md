# Criteria provenance

Every threshold in Safe Frame's detector is a published one. This file records
where each came from, so a reader can check the implementation against the
standard rather than against our description of it.

The wording below is quoted from the W3C's *Understanding Success Criterion
2.3.1: Three Flashes or Below Threshold*, which defines the general-flash and
red-flash thresholds used across web and broadcast practice:
<https://www.w3.org/TR/UNDERSTANDING-WCAG20/seizure-does-not-violate.html>

## Implemented

| Test | Safe Frame | Published definition |
|---|---|---|
| General flash | `luma_delta >= 0.10` | "a pair of opposing changes in relative luminance of 10% or more of the maximum relative luminance" |
| Red flash | `red_delta >= 0.20`, **no luminance floor** | "any pair of opposing transitions involving a saturated red". WCAG notes people "are even more sensitive to red flashing than to other colors, so a special test is provided" |
| Affected area | `changed_area_fraction >= 0.25` | flashes occupying more than "25% of any 10 degree visual field on the screen" at typical viewing distance |
| Rate | more than 6 opposing transitions within any 1000 ms | "no more than three flashes within any one-second period". One flash is *a pair* of opposing transitions, so three flashes is six transitions; more than six transitions is more than three flashes |
| Opposing directions | a window must contain both `up` and `down` | "a pair of opposing changes ... an increase followed by a decrease, or a decrease followed by an increase" |

### Why red flash has no luminance floor

This is the single most consequential design decision in the detector, and it
is not ours: WCAG gives saturated red its own test precisely because red
flashing is more provocative than luminance flashing alone. A saturated red
alternating with a colour of matched relative luminance moves `luma_delta`
almost not at all. Gating the red rule on luminance would therefore reproduce
the exact blind spot the separate test exists to close.

`tests/test_ingest.py::test_red_alternation_at_matched_luminance_is_caught_only_by_the_red_rule`
demonstrates this from pixels: measured luminance swing stays under 0.01 while
saturated red swings past 0.9, the general rule stays silent, and the red rule
fires.

The two rules are also windowed **independently**. Four red-qualifying and four
luminance-qualifying transitions inside one second is eight transitions, but
neither rule reaches seven on its own, so nothing is reported. Combining them
would invent a violation that neither published test supports.
`tests/test_sql_parity.py::test_rules_are_windowed_independently` holds both the
Python and the SQL implementation to that.

## Not implemented

| Test | Status |
|---|---|
| Regular spatial pattern | **Not implemented.** Harding-style analysers test luminance flashes, red flashes *and* spatial patterns. Safe Frame implements the first two. A striped or checkerboard pattern that breaches the spatial criteria will not be flagged. |

The `regular_pattern` value exists in the schema's `rule` enum so the anti-join
is already keyed on rule and a third rule can be added without a migration.
Nothing in the product emits it, and no surface reports it.

## What this is not

Safe Frame is an open pre-check implementing published criteria. It is not
certified, not on any broadcaster's approved-device list, and not a medical
device. Agreement with a published threshold is not the same as validation
against a certified analyser, and we have not performed that comparison. See
[`LIMITATIONS.md`](LIMITATIONS.md).
