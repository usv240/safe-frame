# Safe Frame, demo script

**Target 2:40–2:50. Hard limit 3:00**, only the first 3:00 is evaluated.

If the triage agent takes its full twenty seconds the run lands nearer 2:50 than
2:40. That is still safely inside the limit, so do not speed up to hit a number.
**A clear 2:50 beats a rushed 2:40.**

Narration is **400 words**, about 2:25 at a calm 165 words a minute. Forty-seven
of those words are spoken *over* the triage agent's wait, so they cost almost no
wall-clock time: the run measures **2:44 if the agent answers in twelve seconds,
2:47 if it takes twenty**, including scrolling, the six button presses, and the
few seconds the bring-your-own check and the stack check take to return.

Nine beats, and they are not equal. The red-flash case and the four-profile
result carry Potential Impact and Quality of the Idea between them; the agent
and the closing stack check carry Technological Implementation. Those four are
the reason to make the video at all. The evaluation and criteria beats are one
line each on purpose: their numbers are legible on screen, so narrating them
twice would spend the time the four above need.

Word count is not the constraint; runtime is. Do not add lines, the remaining
margin is the whole reason this fits.

The page is ordered to match this script and the header nav is in that same
order, so the demo moves **downward only** and ends on the live stack.
Use the nav rather than scrolling: it lands exactly on each panel, which is one
fewer thing to fumble on camera. Never go back up. The Safe Frame name sits in
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
- The triage agent takes 12–20 seconds. Do not cut it: the wait is the proof.
  The narration for that beat is deliberately short so you can talk over it.
- Read numbers **off the screen**. The catalogue is live and a row you click may
  differ by one or two from the figures below.

---

## 0:00–0:16, The gap

**DO:** Hero section, still. Do not scroll. The contents map under the hero
names every panel; the header nav repeats the main six and follows you down.
**POINT:** The headline, *"The master passed. The version people watched was
never checked."*

**SAY:**

> **"A film is approved once, then becomes dozens of versions: frame rates,
> ad-break inserts, social crops. Testing runs on the master, before all of
> that. Safe Frame finds the version that introduced the risk."**

---

## 0:16–0:42, Run the sweep

**DO:** Click **Sweep** in the header nav. Press **Sweep the catalogue**.
**POINT:** The four counters while it runs.

**SAY:**

> **"Four hundred and twenty-four titles. Ten million transitions. Both
> published flash rules across all of it in one pass, through the official
> ClickHouse MCP server."**

**POINT:** The result headline, then the **Rule** column.

> **"Under two seconds. Sixty-six renditions introduced a violation their
> approved master never had, forty-three luminance, twenty-three red."**

---

## 0:42–1:10, The case other checkers miss

**DO:** Click any row whose **Rule** reads **Red flash**. Wait for the chart.
**POINT:** The top track, then the bottom track.

**SAY:**

> **"The approved master stays under the limit for its whole runtime. The
> rendition that shipped crosses it, more than twenty qualifying transitions in
> one second, against a limit of six."**

**POINT:** Trace the **blue** series along the bottom track. It stays flat.

> **"But the luminance line here barely moves. Saturated red has its own test,
> with no brightness condition. The published rule evaluates red flashing even at
> steady brightness. A luminance-only checker passes this file. This one
> doesn't."**

---

## 1:10–1:34, Prove it isn't circular

**DO:** Click **Evidence** in the header nav. Press **Score the detector**.
**POINT:** The four tiles, left to right.

**POINT:** The **found and planted** tile, then **decoys correctly rejected**.

**SAY:**

> **"Synthetic data, so don't just believe it. This recovers what was planted
> using a query that reads no flash measurement. Sixty-six for sixty-six, and
> eighty-six decoys that really do flash, correctly left alone."**

---

## 1:34–1:54, Findings become an action

**DO:** Click **Cause** in the header nav. Press **Profile every transform**.
**POINT:** The four coloured bars, then the clean rows beneath them.

**SAY:**

> **"Sixty-six findings are not sixty-six problems. Every one traces back to
> four encoder profiles, and three introduced nothing. Four configurations to
> fix upstream, instead of sixty-six files to patch."**

**POINT:** The middle outcome tile.

> **"Twenty-three of them are the red-flash cases a luminance-only workflow
> would never have seen."**

---

## 1:54–2:22, The agent

**DO:** Click **Agent** in the header nav. Press **Run the triage agent**.
**POINT:** Keep the working state visible. Let the wait run.

**SAY:**

> **"Now Gemini, through Google's Agent Development Kit on Vertex AI. Its four
> tools run live ClickHouse queries through MCP: survey the catalogue, profile
> the transforms, measure the red-flash blind spot, then investigate the case it
> ranks highest, and which case that is, is the model's own call."**

*(The line above is written to run about fifteen seconds, roughly the length
of the wait. Deliver it at the same pace as everything else. If the agent is
still working when you finish, hold the silence; do not fill it.)*

**POINT:** When the brief lands, run your cursor down the **numbered trace**.

> **"That's the real sequence of calls from this run. Every number in the brief
> came from SQL."**

**POINT:** `decision_source` and `requires_human` in the panel beside it.

> **"The boundary is explicit. ClickHouse decides. Gemini explains. A human is
> still responsible for acting."**

---

## 2:22–2:36, Your file, not ours

**DO:** Click **Your video** in the header nav. Both files are already chosen. Press
**Measure and check**. It returns in about two seconds.
**POINT:** The verdict, then **Decision**.

**SAY:**

> **"Everything so far ran on our catalogue. This is my own file. It decodes in
> this browser, never uploaded, never shown, measured by the same code. Same
> verdict, same ClickHouse."**

---

## 2:36–2:44, Credibility

**DO:** Scroll down to **Criteria provenance**. Do not linger.
**POINT:** The greyed **not implemented** row.

**SAY:**

> **"Every threshold traces to published guidance, and the rule we have not
> implemented is stated openly."**

---

## 2:44–2:58, Proof, and close

**DO:** Click **Stack** in the header nav. Press **Check the stack**. It returns in
about four seconds. This is where the demo ends.
**POINT:** The three green dots in the ClickHouse and Google rows.

**SAY:**

> **"And none of that is on my word. ClickHouse just reported its own version,
> the MCP server listed its own tools, Vertex answered. Green means it replied
> just now."**

**POINT:** The **Safe Frame** name in the sticky header, top-left.

> **"Safe Frame finds the version that introduced the risk, names the system
> that caused it, and gives QC teams evidence to act on, before an audience is
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
- [ ] A file of your own checked live, verdict and decision source visible
- [ ] Criteria table including the **not implemented** row
- [ ] Stack checked live, the three green dots and the ClickHouse version visible
- [ ] Ends on the live stack, no scroll-back
- [ ] No GitHub tab, no logos, no music
- [ ] Under 3:00, uploaded Public, English audio or subtitles

---

## Why this order

The four judging criteria are **equally weighted**: there is no separate score
for the video itself. So the run has to demonstrate all four without ever saying
their names:

| Criterion | Where it lands |
|---|---|
| Technological Implementation | ten million rows in one pass through the official MCP server; the agent's real tool trace; and the stack answering live at the end, so the partner integration is shown rather than claimed |
| Design | a named contents map, a nav that follows you, and one downward path: problem, evidence, cause, action |
| Potential Impact | the red-flash case a luminance-only checker passes, and four profiles to fix instead of sixty-six files |
| Quality of the Idea | a non-obvious master-versus-rendition comparison that existing file-level checks do not address, with the unimplemented rule named rather than hidden |

The arc is one sentence: **find the regression → prove it isn't circular → show
what other checkers miss → name the cause → let the agent prioritise the work.**

## Things deliberately left out

Cut for time, and because each would dilute the arc rather than add to it. If a
judge asks, they are all on the page or in the repository.

- The `/v1/scan` per-pair API and the OpenAPI surface at `/docs`.
- **Runtime evidence**: the live MCP handshake and the credential-boundary
  diagram. Strong material, but the sweep already proves MCP is real.
- **Decision boundary**: the SQL panel. The agent section makes the same point
  faster, on camera, with live output.
- The findings export, the Plain/Technical toggle, and the light/dark toggle.
- The standards audit that found three defects in our own detector. It is the
  best thing in the repository and there is no room for it; put a line about it
  in the Devpost description instead.

## If you overrun

Cut in this order. Never cut the red-flash beat or the four-profile result, 
they carry Potential Impact and Quality of the Idea between them.

1. The **Measured from pixels** line (23 words).
2. The `decision_source` / `requires_human` line (15 words), the fields stay
   visible on screen either way.
3. The second half of the criteria line, from *"An open pre-check"* (10 words).
