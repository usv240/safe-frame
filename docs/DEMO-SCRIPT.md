# Demo video script — 2:50

Hard limit is 3:00; only the first 3:00 is evaluated.

**Rules to honour while recording**

- Show the product *executing*, not slides pretending to be execution.
- No third-party logos, music, advertising, or footage. Everything on screen is
  this app, this repository, this terminal.
- English narration, or English subtitles.
- Upload Public to YouTube or Vimeo before submitting.
- Nothing in this demo flashes. Say so — it is the point.

**Setup before you hit record**

- Browser at 1440×900, zoom 100%, signed out, no extensions visible.
- Run the sweep once to warm the MCP session, then reload so the recording
  shows a genuine cold press of the button.
- The triage agent takes ~20s. Do not cut it — the wait is the proof it is
  really running four queries. Narrate over it.
- Second tab: the GitHub repository at the root.

---

## 0:00–0:15 — The problem, one sentence

> *Hero on screen. Do not scroll.*

"A film is approved once. Then it becomes dozens of versions — frame rates,
grades, social crops, ad-break inserts, burnt-in subtitles. Photosensitivity QC
runs on the master, before all of that. When a conversion *introduces* a flash
the approved master never had, nothing is looking."

## 0:15–0:35 — Why it matters

> *Scroll to the three fact cards.*

"Photosensitive epilepsy affects about one in four thousand people. In 1997 a
single broadcast sent six hundred and eighty-five children to hospital. Ofcom
Rule 2.12 and WCAG 2.3.1 both set thresholds — and every one of them judges *a
file* against *a standard*. None judges a file against the version already
signed off."

## 0:35–1:05 — The sweep, live

> *Scroll to the sweep. Point at the counters, press the button, wait.*

"Four hundred titles, thirty-two hundred renditions, nine point six million
transition measurements in ClickHouse. Both published flash rules evaluated
across every row in one pass, through the official ClickHouse MCP server."

> *Result lands.*

"Forty-four renditions introduced a violation their master never had. Under two
seconds. Thirty-one general flash, thirteen red flash."

## 1:05–1:40 — The case a luminance checker misses

> *Click a **red flash** row. Wait for the chart.*

"Both tracks, same query, same scale. Top is the approved master — under the
criterion for its whole runtime. Bottom is the rendition that shipped: one
second, twenty-five qualifying transitions."

> *Point at the blue series on the bottom track — it is flat.*

"And the luminance track on that rendition never moves. WCAG gives saturated red
its own test, deliberately with no luminance condition, because red flashing is
more provocative. A checker that only tests luminance passes this file."

## 1:40–2:05 — The systemic answer

> *Scroll to Systemic cause. Press **Profile every transform**.*

"Forty-four findings sounds like forty-four problems. It isn't. Four encoder
profiles account for all of them, and three transforms introduce nothing.
Frame-rate interpolation and ad-break insertion produce every luminance
regression; subtitle burn-in and social crop produce every red one. That is two
different root causes with two different owners — and thirteen of the
forty-four are invisible to a luminance-only check."

## 2:05–2:35 — The agent's mission

> *Scroll to the brief. Press **Run the triage agent**. Talk while it works.*

"Now the Gemini agent, on Vertex through Google's ADK. It has four tools, every
one a live ClickHouse query through MCP, and it sequences them itself — survey
the sweep, profile the transforms, size the blind spot, then go deep on the one
case it ranks first."

> *Brief lands. Point at the numbered trace.*

"Those are the calls it actually made, recorded from the run. Every figure in
the brief came back from SQL. And look at the boundary: decision source is
`clickhouse_sql`, human required is `true`. The arithmetic decides, the model
explains, a person acts."

## 2:35–2:50 — Restraint, and close

> *Scroll to the criteria table. Let the "not implemented" row sit on screen.*

"Every threshold is quoted from the standard. We couldn't get a photosensitivity
expert to review this, so we audited it against the published texts ourselves —
and found our own detector wrong three times. The darker-image condition was
missing entirely; adding it removed thirteen false positives. The rule we still
don't implement is named right there rather than hidden. Open pre-check, not a
certified device, synthetic catalogue. Apache-2.0, repo and app in the
description. Safe Frame — find the version that introduced the risk, before an
audience does."

---

## Shot checklist

- [ ] Sweep pressed live, result not cut
- [ ] A `red_flash` row selected, chart drawn on camera
- [ ] The flat luminance track on that rendition pointed out explicitly
- [ ] Transform profile run live, the four-profiles point made
- [ ] Triage agent run live, numbered tool trace visible
- [ ] `decision_source` and `requires_human` shown on screen
- [ ] Criteria table including the "not implemented" row and the audit finding
- [ ] Public URL and repo URL legible at normal playback size
- [ ] Under 3:00, uploaded Public, English audio or subtitles
