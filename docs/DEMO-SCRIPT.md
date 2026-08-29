# Demo video script — 2:48

Hard limit is 3:00; only the first 3:00 is evaluated. This is timed to 2:48 to
leave room for natural pacing.

**Rules to honour while recording**

- Show the product *executing*, not slides pretending to be execution.
- No third-party logos, music, advertising, or footage. Everything on screen is
  this app, this repository, and this terminal.
- English narration, or English subtitles.
- Upload Public to YouTube or Vimeo before submitting.
- Nothing in this demo flashes. Say so on camera — it is the point.

**Setup before you hit record**

- Browser at 1440×900, zoom 100%, signed out, no extensions visible.
- Have the sweep already run once so the ClickHouse MCP session is warm; then
  reload the page so the recording shows a genuine cold press of the button.
- Second tab: the GitHub repository at the root.
- Have `title_0022__subtitle_burnin` (or any `red_flash` row) in mind.

---

## 0:00–0:18 — The problem, in one sentence

> *On screen: the hero. Do not scroll yet.*

"A film is approved once. Then it becomes dozens of versions — different frame
rates, different grades, social crops, ad-break inserts, burnt-in subtitles.
Photosensitivity QC runs on the master, before all of that. So when a
conversion *introduces* a flash the approved master never had, nothing is
looking."

## 0:18–0:38 — Why it matters

> *Scroll to the three fact cards. Let them sit on screen while you talk.*

"Photosensitive epilepsy affects about one in four thousand people. In 1997 a
single broadcast sent six hundred and eighty-five children to hospital in Japan.
Ofcom Rule 2.12 and WCAG 2.3.1 both set thresholds. All of those standards judge
*a file* against *a standard* — none of them judges a file against the version
that was already signed off."

## 0:38–1:15 — The sweep, live

> *Scroll to the sweep. Point at the corpus counters, then press the button.*

"This catalogue is four hundred titles, thirty-two hundred renditions, nine
point six million transition measurements, in ClickHouse. I press this, and both
published flash rules are evaluated across every single one of those rows in one
pass, through the official ClickHouse MCP server."

> *Press **Sweep the catalogue**. Wait for the real result. Do not cut.*

"Forty-four renditions introduced a violation their approved master never had.
One point seven seconds. Thirty-one general flash, thirteen red flash — and the
red ones came from different transforms than the luminance ones."

## 1:15–1:55 — The evidence, and the case a luminance check misses

> *Click a **red flash** row. Wait for the chart to draw.*

"Both of these tracks come from the same query over the same table, on the same
scale. Top is the approved master — under the criterion for its entire runtime.
Bottom is the rendition that shipped. One second, twenty-five qualifying
transitions, well past the limit."

> *Point at the blue series on the child track — it stays flat.*

"And look at this: the general-flash track on the rendition never moves.
Luminance barely changed. WCAG gives saturated red its own test precisely
because red flashing is more provocative, and it deliberately carries no
luminance condition. A checker that only tests luminance passes this file. We
catch it because we implement the red rule as it is actually written."

## 1:55–2:20 — Who decides

> *Press **Ask the ADK agent**. Show the JSON.*

"Now the Gemini agent. It runs on Vertex through Google's ADK, and it cannot
reach a verdict of its own — it has to retrieve the rows through MCP. Look at
the response: `decision_source` is `clickhouse_sql`, and `requires_human` is
true. The arithmetic decides. The model explains. A human acts. If the MCP query
fails, this endpoint returns 502 rather than substitute a guess."

## 2:20–2:38 — Restraint

> *Scroll to the criteria provenance table.*

"Every threshold here is quoted from WCAG 2.3.1 — ten percent luminance,
saturated red with no luminance floor, twenty-five percent of the visual field,
more than three flashes a second. And the rule we have *not* implemented,
spatial pattern, is named right here rather than left implied. This is an open
pre-check. It is not certified, it is not a medical device, and the catalogue is
synthetic data we authored."

## 2:38–2:48 — Close

> *Cut to the repository, then back to the URL bar.*

"Everything is Apache-2.0 and public. The hosted app and the repo are in the
description. Safe Frame — find the version that introduced the risk, before an
audience does."

---

## Shot checklist

- [ ] Sweep pressed live, result not cut
- [ ] A `red_flash` row selected, chart drawn on camera
- [ ] The flat general-flash track on that rendition pointed out explicitly
- [ ] ADK response showing `decision_source` and `requires_human`
- [ ] Criteria provenance table including the "not implemented" row
- [ ] Public URL and repo URL legible at normal playback size
- [ ] Total runtime under 3:00
- [ ] Uploaded Public, English audio or subtitles
