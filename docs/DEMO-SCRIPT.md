# Safe Frame — demo script

**Target 2:40–2:45. Hard limit 3:00** — only the first 3:00 is evaluated.

Narration is **~380 words**. At a calm 165 words a minute that is about 2:18 of
speech, leaving roughly 25 seconds for clicking, scrolling and the agent's wait.
Do not add lines: the margin is the whole reason this fits.

The page is ordered to match this script, so the demo scrolls **downward once**
and ends on the criteria table. Never scroll back up. The Safe Frame name sits in
the sticky header the entire time, so the close does not need to return to the
hero.

**Rules to honour while recording**

- Show the product executing. No slides, no mock-ups.
- **Do not open the GitHub tab on camera.** It puts a third-party logo on screen
  and spends product time. Put the repository link in the description.
- No music, no third-party footage, nothing but this app.
- English narration, or English subtitles.
- Upload Public to YouTube or Vimeo before submitting.

**Before you hit record**

- Browser at 1440×900, 100% zoom, signed out, no extensions or bookmarks bar.
- Run the sweep once to warm the MCP session, then reload, so the recording
  shows a genuine cold press.
- The triage agent takes 12–20 seconds. Do not cut it — the wait is the proof.
  The narration for that beat is deliberately short so you can talk over it.
- Read numbers **off the screen**. The catalogue is live and a row you click may
  differ by one or two from the figures below.

---

## 0:00–0:16 — The gap

**DO:** Hero section, still. Do not scroll.
**POINT:** The headline, *"The master passed. The version people watched was
never checked."*

**SAY:**

> **"A film is approved once. Then it becomes dozens of versions — frame rates,
> ad-break inserts, social crops, subtitles. Testing runs on the master, before
> all of that. Safe Frame finds the version, and the transformation, that
> introduced the risk."**

---

## 0:16–0:42 — Run the sweep

**DO:** Scroll to **Live catalogue sweep**. Press **Sweep the catalogue**.
**POINT:** The four counters while it runs.

**SAY:**

> **"Four hundred and twenty-four titles. Over three thousand renditions. Ten
> million transitions in ClickHouse. Both published flash rules, evaluated
> across all of it in one pass, through the official ClickHouse MCP server."**

**POINT:** The result headline, then the **Rule** column.

> **"Under two seconds. Sixty-six renditions introduced a violation their
> approved master never had — forty-three luminance, twenty-three red."**

---

## 0:42–1:10 — The case other checkers miss

**DO:** Click any row whose **Rule** reads **Red flash**. Wait for the chart.
**POINT:** The top track, then the bottom track.

**SAY:**

> **"The approved master stays under the limit for its whole runtime. The
> rendition that shipped crosses it — more than twenty qualifying transitions in
> one second, against a limit of six."**

**POINT:** Trace the **blue** series along the bottom track. It stays flat.

> **"But the luminance line here barely moves. Saturated red has its own
> published test, with no brightness condition — red flashing is hazardous even
> at steady brightness. A luminance-only checker passes this file. This one
> doesn't."**

---

## 1:10–1:34 — Prove it isn't circular

**DO:** Scroll to **Does it actually work**. Press **Score the detector**.
**POINT:** The four tiles, left to right.

**SAY:**

> **"Synthetic data — so don't just believe it. This recovers the planted set
> from the generator's own random decisions, using a query that reads no flash
> measurement. Sixty-six planted, sixty-six found."**

**POINT:** The **decoys correctly rejected** tile.

> **"And eighty-six decoys placed to be rejected — files that genuinely flash,
> but whose master flashes identically. All eighty-six left alone."**

**POINT:** The **Measured from pixels** row in the cohort table.

> **"Part of this catalogue is measured end to end from constructed image frames
> rather than preselected measurements — and it produces the same result."**

---

## 1:34–1:54 — Findings become an action

**DO:** Scroll to **Systemic cause**. Press **Profile every transform**.
**POINT:** The four coloured bars, then the clean rows beneath them.

**SAY:**

> **"Sixty-six findings are not sixty-six problems. Every one traces back to
> four encoder profiles — and three introduced nothing. Four configurations to
> fix upstream, instead of sixty-six files to patch."**

**POINT:** The middle outcome tile.

> **"Twenty-three of them are the red-flash cases a luminance-only workflow
> would never have seen."**

---

## 1:54–2:22 — The agent

**DO:** Scroll to **The agent's mission**. Press **Run the triage agent**.
**POINT:** Keep the working state visible. Let the wait run.

**SAY:**

> **"Now Gemini, through Google's Agent Development Kit on Vertex AI. Four
> tools, each a live ClickHouse query through MCP. It chooses the order
> itself."**

*(Pause here. The agent is working. Say nothing until the brief lands.)*

**POINT:** When the brief lands, run your cursor down the **numbered trace**.

> **"That's the real sequence of calls from this run. Every number in the brief
> came from SQL."**

**POINT:** `decision_source` and `requires_human` in the panel beside it.

> **"The boundary is explicit. ClickHouse decides. Gemini explains. A human is
> still responsible for acting."**

---

## 2:22–2:40 — Credibility, and close

**DO:** Scroll to **Criteria provenance**. This is where the demo ends — do not
scroll further, and do not scroll back.
**POINT:** Two or three threshold rows, then the greyed **not implemented** row.

**SAY:**

> **"Every threshold traces to published guidance — and the one rule we haven't
> implemented is stated openly. An open pre-check, not a certified device.
> Nothing here flashes."**

**POINT:** The **Safe Frame** name in the sticky header, top-left.

> **"Safe Frame finds the version that introduced the risk, names the system
> that caused it, and gives QC teams evidence to act on — before an audience is
> exposed."**

---

## Shot checklist

- [ ] Sweep pressed live, result not cut
- [ ] A **Red flash** row selected, chart drawn on camera
- [ ] The flat luminance line on that rendition traced explicitly
- [ ] Evaluation scored live: **66/66**, decoys **86/86**, cohort row shown
- [ ] Transform profile run live, four-versus-three point made
- [ ] Triage agent run live, numbered trace visible, **wait not cut**
- [ ] `decision_source` and `requires_human` legible on screen
- [ ] Criteria table including the **not implemented** row
- [ ] Ends on the criteria section — no scroll-back
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
| Quality of the Idea | a non-obvious master-versus-rendition comparison that existing file-level checks do not address, with the unimplemented rule named rather than hidden |

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

## If you overrun

Cut in this order. Never cut the red-flash beat or the four-profile result —
they carry Potential Impact and Quality of the Idea between them.

1. The **Measured from pixels** line (23 words).
2. The `decision_source` / `requires_human` line (15 words) — the fields stay
   visible on screen either way.
3. The second half of the criteria line, from *"An open pre-check"* (10 words).
