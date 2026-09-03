# Safe Frame — demo script

**Target 2:40–2:45. Hard limit 3:00** — only the first 3:00 is evaluated.

The page is ordered to match this script, so the whole demo scrolls **downward
once**. Never scroll back up; if you miss a beat, keep going.

**Rules to honour while recording**

- Show the product executing. No slides, no mock-ups.
- **Do not open the GitHub tab on camera.** It puts a third-party logo on screen
  and spends product time. Put the repository link in the description.
- No music, no third-party footage, nothing but this app.
- English narration, or English subtitles.
- Upload Public to YouTube or Vimeo before submitting.
- Nothing in this demo flashes. Say so once, near the end.

**Before you hit record**

- Browser at 1440×900, 100% zoom, signed out, no extensions or bookmarks bar.
- Run the sweep once to warm the MCP session, then reload, so the recording
  shows a genuine cold press.
- The triage agent takes 12–20 seconds. Do not cut it — the wait is the proof.
  Narrate over it.
- Read numbers **off the screen**. The catalogue is live and a row you click may
  differ by one or two from the figures below.

---

## 0:00–0:18 — The gap

**DO:** Hero section, still. Do not scroll.
**POINT:** The headline, *"The master passed. The version people watched was
never checked."*

**SAY:**

> **"A film is approved once. Then it becomes dozens of versions — different
> frame rates, ad-break inserts, social crops, burnt-in subtitles.
> Photosensitivity testing runs on the master, before all of that. If one of
> those conversions introduces a dangerous flash, the approved master does not
> protect the audience. Safe Frame finds the exact version, and the exact
> transformation, that introduced the risk."**

---

## 0:18–0:45 — Run the sweep

**DO:** Scroll to **Live catalogue sweep**. Press **Sweep the catalogue**.
**POINT:** The four counters while it runs.

**SAY:**

> **"Four hundred and twenty-four titles. Over three thousand renditions. More
> than ten million measured transitions, in ClickHouse. Both published flash
> rules are evaluated across all of it in one pass, through the official
> ClickHouse MCP server."**

**POINT:** The result headline, then the **Rule** column.

> **"Under two seconds. Sixty-six renditions introduced a violation their
> approved master never had — forty-three luminance, twenty-three red."**

---

## 0:45–1:12 — The case other checkers miss

**DO:** Click any row whose **Rule** reads **Red flash**. Wait for the chart.
**POINT:** The top track, then the bottom track.

**SAY:**

> **"One finding. The approved master stays under the limit for its whole
> runtime. The rendition that shipped crosses it — more than twenty qualifying
> transitions inside one second, against a limit of six."**

**POINT:** Trace the **blue** series along the bottom track. It stays flat.

> **"But look at the luminance line on that same rendition. It barely moves.
> Saturated red has its own published test, deliberately with no brightness
> condition, because red flashing is hazardous even when brightness is steady.
> A checker that only tests luminance passes this file. This one does not."**

---

## 1:12–1:38 — Prove it isn't circular

**DO:** Scroll to **Does it actually work**. Press **Score the detector**.
**POINT:** The four tiles, left to right.

**SAY:**

> **"This is synthetic data, so you should not simply believe the result. This
> recovers what was planted from the generator's own random decisions, using a
> query that reads no flash measurement at all. Sixty-six planted, sixty-six
> found. Nothing missed. Nothing invented."**

**POINT:** The **decoys correctly rejected** tile, then the cohort table below.

> **"And eighty-six decoys placed to be rejected — files that genuinely flash,
> but whose master flashes identically, so nothing was introduced. All
> eighty-six left alone. Recall you can fake by flagging everything; precision
> against those decoys you cannot."**

**POINT:** The **Measured from pixels** row.

> **"And part of this catalogue isn't authored numbers at all — it's measured
> from actual frames. It scores the same."**

---

## 1:38–2:00 — Findings become an action

**DO:** Scroll to **Systemic cause**. Press **Profile every transform**.
**POINT:** The four coloured bars, then the clean rows beneath them.

**SAY:**

> **"Sixty-six findings are not sixty-six problems. Every one traces back to
> four encoder profiles — and three profiles introduced nothing at all. That is
> four configurations to fix upstream, instead of sixty-six files to patch by
> hand."**

**POINT:** The middle outcome tile.

> **"Twenty-three of them are the red-flash cases a luminance-only workflow
> would never have seen."**

---

## 2:00–2:28 — The agent

**DO:** Scroll to **The agent's mission**. Press **Run the triage agent**.
**POINT:** Keep the working state visible and talk over it.

**SAY:**

> **"Now Gemini, through Google's Agent Development Kit on Vertex AI. It has
> four tools, each one a live ClickHouse query through MCP, and it decides the
> order itself — survey the catalogue, profile the transforms, measure the
> red-flash blind spot, then investigate the case it ranks first."**

**POINT:** When the brief lands, run your cursor down the **numbered trace**.

> **"That is the real sequence of calls from this run, not a scripted
> animation. Every number in the brief came back from SQL."**

**POINT:** `decision_source` and `requires_human` in the panel beside it.

> **"And the boundary is explicit. ClickHouse makes the decision. Gemini
> explains the evidence. A human is still responsible for acting."**

---

## 2:28–2:43 — Credibility, and close

**DO:** Scroll to **Criteria provenance**.
**POINT:** Two or three threshold rows, then the greyed **not implemented** row.

**SAY:**

> **"Every threshold traces to published guidance — and the one rule we have not
> implemented is stated openly rather than hidden. This is an open pre-check,
> not a certified medical or broadcast device, and nothing in this interface
> flashes."**

**DO:** Scroll back to the top so the product name is on screen as you finish.

> **"Safe Frame finds the version that introduced the risk, names the system
> that caused it, and hands a QC team evidence they can act on — before an
> audience is exposed to it."**

---

## Shot checklist

- [ ] Sweep pressed live, result not cut
- [ ] A **Red flash** row selected, chart drawn on camera
- [ ] The flat luminance line on that rendition traced explicitly
- [ ] Evaluation scored live: **66/66**, decoys **86/86**, cohort row shown
- [ ] Transform profile run live, four-versus-three point made
- [ ] Triage agent run live, numbered trace visible, wait not cut
- [ ] `decision_source` and `requires_human` legible on screen
- [ ] Criteria table including the **not implemented** row
- [ ] No GitHub tab, no logos, no music
- [ ] Under 3:00, uploaded Public, English audio or subtitles

---

## Why this order

The four judging criteria are **equally weighted** — there is no separate score
for the video itself. So the run has to demonstrate all four without ever saying
their names:

| Criterion | Where it lands |
|---|---|
| Technological Implementation | ten million rows in one pass through the official MCP server; the agent's real tool trace |
| Design | one downward scroll: problem, evidence, cause, action |
| Potential Impact | the red-flash case a luminance-only checker passes, and four profiles to fix instead of sixty-six files |
| Quality of the Idea | master-versus-rendition is the comparison nobody else makes, and the unimplemented rule is named rather than hidden |

The arc is one sentence: **find the regression → prove it isn't circular → show
what other checkers miss → name the cause → let the agent prioritise the work.**

## Things deliberately left out

Cut for time, and because each would dilute the arc rather than add to it. If a
judge asks, they are all on the page or in the repository.

- The `/v1/scan` per-pair API and the OpenAPI surface at `/docs`.
- **Runtime evidence** — the live MCP handshake and the credential-boundary
  diagram. Strong material, but the sweep already proves MCP is real.
- **Decision boundary** — the SQL panel. The agent section makes the same point
  faster, on camera, with live output.
- The findings export, the Plain/Technical toggle, and the light/dark toggle.
- The standards audit that found three defects in our own detector. It is the
  best thing in the repository and there is no room for it; put a line about it
  in the Devpost description instead.
