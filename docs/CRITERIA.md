# Criteria provenance and standards audit

Every threshold in Safe Frame's detector is a published one. This file records
where each came from, what an audit against the primary sources found wrong,
and what still deviates.

We could not obtain review by a qualified photosensitive-epilepsy or broadcast
professional. This audit is the substitute, and it is deliberately structured so
a reader can check it rather than trust it: each row quotes the published text
and points at the implementation. It is not equivalent to expert review, and it
does not establish efficacy.

Definitions are quoted from the W3C's *Understanding Success Criterion 2.3.1:
Three Flashes or Below Threshold* and the WCAG relative-luminance definition:

- <https://www.w3.org/TR/UNDERSTANDING-WCAG20/seizure-does-not-violate.html>
- <https://www.w3.org/TR/WCAG21/relative-luminance.html>

## Implemented

| Test | Safe Frame | Published definition |
|---|---|---|
| General flash — amplitude | `luma_delta >= 0.10` | "a pair of opposing changes in relative luminance of 10% or more of the maximum relative luminance" |
| General flash — darker image | `luma_min < 0.80` | "…**where the relative luminance of the darker image is below 0.80**" |
| Red flash | a saturated-red transition, **no luminance condition** | "any pair of opposing transitions involving a saturated red" |
| Saturated red | `R / (R + G + B) >= 0.8` in either state, and `\|Δ (R−G−B)×320\| > 20` | "for either or both states involved in each transition, R/(R+G+B) >= 0.8, and the change in the value of (R-G-B)x320 is > 20" |
| Relative luminance | `0.2126 R + 0.7152 G + 0.0722 B` over **linearised** sRGB | "if RsRGB <= 0.04045 then R = RsRGB/12.92 else R = ((RsRGB+0.055)/1.055) ^ 2.4" |
| Affected area | `changed_area_fraction >= 0.25` | flashes occupying more than "25% of any 10 degree visual field on the screen" |
| Rate | more than 6 opposing transitions within any 1000 ms | "no more than three general flashes and / or no more than three red flashes within any one-second period". One flash is *a pair* of opposing transitions, so three flashes is six transitions |
| Opposing directions | a window must contain both `up` and `down` | "a pair of opposing changes … an increase followed by a decrease, or a decrease followed by an increase" |

## What the audit found wrong

Three defects, all of which changed results.

**1. Relative luminance was not linearised.** `metrics.relative_luminance`
applied the BT.709 coefficients directly to sRGB samples. sRGB is gamma-encoded,
so weighting the encoded values overstates the luminance of dark pixels and
understates bright ones. Every threshold downstream is expressed against WCAG's
definition, so the error propagated into the general-flash rule and into the
matched-luminance test fixture — which was constructed from the raw
coefficients and therefore passed for the wrong reason.

**2. The darker-image condition was missing entirely.** The general-flash test
applies only "where the relative luminance of the darker image is below 0.80".
Safe Frame checked the amplitude, the area and the rate, and never the darker
image, so a high-amplitude alternation between two near-white states was
reported as a violation. It is not one.

The corpus now carries a control cohort for exactly this — a bright-on-bright
alternation in `hdr10_passthrough` that clears the delta, area and rate floors
with `luma_min` at 0.86. Measured against the live catalogue:

| | regressions returned |
|---|---|
| with the darker-image condition (shipped) | **44** — 31 general flash, 13 red flash |
| without it (what we shipped before this audit) | 57 — 44 general flash, 13 red flash |

Thirteen false positives, every one of them an `hdr10_passthrough` rendition
that the published test does not apply to.

**3. Saturated red was a proxy.** `metrics.saturated_red` returned
`R − max(G, B)`, which looks reasonable and is not the published test. WCAG
defines saturated red precisely, and the definition is now implemented as
written, including the `(R−G−B)×320` swing condition.

Fixing (3) surfaced a fourth, smaller defect: direction for a red transition was
being taken from the *luminance* signal. A red/blue alternation at matched
luminance has no luminance direction at all, so it was recorded as `flat`, which
silently disqualified the exact case the red rule exists to catch. Direction for
the red rule is now taken from the change in `(R−G−B)`.

## What still deviates

These are simplifications we have not resolved. They are stated here rather than
implied.

**Area is a fraction of the frame, not of a 10-degree visual field.** The
published condition is angular: "25% of any 10 degree visual field on the
screen" at typical viewing distance. That depends on screen size and viewing
distance, which a file does not carry. Safe Frame uses the fraction of the frame
that changed, which is the common file-based approximation. On a large screen
viewed closely, a smaller frame fraction can subtend a 10-degree field, so this
approximation can under-report.

**The published area test is over flashes "occurring concurrently".** Safe Frame
measures the changed area of each transition and takes the peak across the
window rather than compositing concurrent flashing regions.

**The synthetic catalogue is generated as transition metrics, not pixels.** The
corpus exercises the criteria, the lineage isolation and every control at scale,
but its `red_delta` and `luma_min` are authored values rather than measurements
of real frames. The pixel-accurate implementations of both live in
`safe_frame/metrics.py` and `safe_frame/ingest.py` and are covered by
`tests/test_ingest.py`; the catalogue does not exercise them.

**Spatial pattern is not implemented at all.** Harding-style analysers test
luminance flashes, red flashes *and* regular spatial patterns. Safe Frame
implements the first two. A striped or checkerboard pattern that breaches the
spatial criteria will not be flagged. The `regular_pattern` value exists in the
schema's `rule` enum so the anti-join is already keyed on rule and a third rule
needs no migration; nothing in the product emits it.

## Why red flash carries no luminance floor

This is the most consequential design decision in the detector, and it is not
ours: WCAG gives saturated red its own test precisely because red flashing is
more provocative than luminance flashing alone. A saturated red alternating with
a colour of matched relative luminance moves `luma_delta` almost not at all.
Gating the red rule on luminance would reproduce the exact blind spot the
separate test exists to close.

`tests/test_ingest.py::test_red_alternation_at_matched_luminance_is_caught_only_by_the_red_rule`
demonstrates this from pixels, solving numerically for the matched colour against
the shipped luminance implementation rather than hard-coding it.

The two rules are also windowed **independently**. Four red-qualifying and four
luminance-qualifying transitions inside one second is eight transitions, but
neither rule reaches seven on its own, so nothing is reported. Combining them
would invent a violation that neither published test supports.
`tests/test_sql_parity.py::test_rules_are_windowed_independently` holds both the
Python and the SQL implementation to that.

## What this is not

Safe Frame is an open pre-check implementing published criteria. It is not
certified, not on any broadcaster's approved-device list, and not a medical
device. Agreement with a published threshold is not the same as validation
against a certified analyser, and we have not performed that comparison. See
[`LIMITATIONS.md`](LIMITATIONS.md) and [`IMPACT.md`](IMPACT.md).
