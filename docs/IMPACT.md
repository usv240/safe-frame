# Who this is for, and what it is worth

This file states the case for the problem being real and the gap being real,
using published sources, and then states plainly what Safe Frame has *not*
shown. The distinction matters: the harm is documented, the standards are
documented, the gap is argued from public documentation, and the efficacy of
this particular implementation is not established.

## The harm is documented

- Photosensitive epilepsy affects roughly **1 in 4,000** people in the general
  population. It is about twice as common in women as men, and most often
  begins before age 20.
  [Fisher et al., "Visually sensitive seizures: an updated review by the
  Epilepsy Foundation", *Epilepsia* 2022](https://onlinelibrary.wiley.com/doi/10.1111/epi.17175)

- On **16 December 1997**, a single television broadcast in Japan sent **685
  children** to hospital; two remained hospitalised for more than two weeks.
  The trigger was a roughly four-second sequence of rapidly alternating red and
  blue frames.
  [Background](https://en.wikipedia.org/wiki/Photosensitive_epilepsy)

That incident is why the red-flash rule exists as a separate test, and why
Safe Frame implements it without a luminance floor — see
[`CRITERIA.md`](CRITERIA.md).

## The obligation is documented

- **Ofcom Broadcasting Code Rule 2.12** requires UK broadcasters to take
  precautions to maintain a low level of risk to viewers with photosensitive
  epilepsy.
  [Ofcom, Section Two: Harm and Offence](https://www.ofcom.org.uk/tv-radio-and-on-demand/broadcast-standards/section-two-harm-offence)
- **WCAG 2.3.1 (Level A)** sets equivalent thresholds for anything delivered on
  the web, which now includes most of what audiences actually watch.
  [W3C](https://www.w3.org/TR/UNDERSTANDING-WCAG20/seizure-does-not-violate.html)
- Harding-style analysers, the de-facto compliance tool, test luminance
  flashes, red flashes and spatial patterns and fail a file that breaches them.

## The gap

All of the above judges **a file** against **a standard**. Prevailing encoding
practice places the QC gate at ingest, before transcode, on the reasoning that
a defective master multiplies across the whole delivery ladder. That reasoning
is correct, and that gate is doing its job.

What it does not do is check what happens *after* sign-off. A single title
becomes many derived assets — frame-rate conversions, tone-maps, downscales,
social crops, ad-break insertions, subtitle burn-ins — and each transform is an
opportunity to introduce a violation into a file whose parent was already
approved. A per-file check run before the transform cannot see that, and a
per-file check run after it has no memory of the parent, so it cannot say
whether the violation is new.

Safe Frame answers one narrow question: **did this transformation introduce a
violation that was absent from the approved parent?** It aligns parent and
child on presentation time (never frame index, which frame-rate conversion
invalidates), evaluates the published criteria across the whole catalogue in
ClickHouse, and returns only the child-only violations, attributed to the
transform that produced them.

## What the demonstration actually produces

On the public corpus the sweep returns 44 renditions that introduced a violation
their approved master never had. The number that matters operationally is the
next one: those 44 come from **four** encoder profiles out of eight, and three
transforms introduce nothing at all.

| Transform | Renditions | Regressed | Rule |
|---|---|---|---|
| `60fps_interp` | 400 | 16 (4.00%) | general flash |
| `adbreak_insert` | 400 | 15 (3.75%) | general flash |
| `subtitle_burnin` | 400 | 7 (1.75%) | red flash |
| `social_crop_v` | 400 | 6 (1.50%) | red flash |
| three others | 1,200 | 0 | — |

Two consequences follow, and both are the kind of thing a QC lead can act on:

1. **This is a handful of upstream fixes, not 44 patches.** The failures cluster
   by profile, and the two rules cluster by *different* profiles — the
   frame-rate and ad-break paths introduce luminance flashes, the crop and
   subtitle-burn paths introduce saturated-red ones. Those are two separate
   conversations with two separate owners.
2. **13 of the 44 are invisible to a luminance-only check.** They come from
   profiles whose only failure mode is red flash, which holds luminance under
   the general-flash floor by construction.

This is measured on a synthetic corpus we authored, so it demonstrates that the
analysis produces an actionable answer at catalogue scale. It is not a claim
about the real-world rate of these defects.

## What we have not shown

- **No clinical or population validation.** Nothing here demonstrates that
  catching these regressions prevents seizures. That claim would need work we
  have not done and are not qualified to do alone.
- **No comparison against a certified analyser.** We implement published
  thresholds and hold two implementations to each other. We have not measured
  agreement with HardingFPA or any approved device.
- **No real footage.** The public corpus is self-authored synthetic
  measurement, generated by `sql/005_catalogue_generator.sql`. It exercises the
  criteria, the lineage isolation and the controls at realistic scale; it is
  not evidence about real content.
- **No external expert review.** Obtaining one from a qualified broadcast
  accessibility or photosensitive-epilepsy professional is the single most
  valuable thing that could be added, and it has not been done.
- **The prior-art claim is bounded.** Our search covered public product
  documentation and found no documented master-to-rendition regression check.
  That is a documented public gap, not proof that no private integration
  exists.

Anyone citing this project should carry these limits with it.
