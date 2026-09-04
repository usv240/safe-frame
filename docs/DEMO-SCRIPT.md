# Safe Frame, demo script

**Target 2:49 at 180 words a minute. Hard limit 3:00**, and only the first
3:00 is evaluated.

**Read this before you record.** The API beat added at 2:24 costs about nine
seconds, and it does not come free. At a brisk 180 words a minute the run lands
at **2:49**. At a calm 165 it lands at **3:00**, which is the limit itself, and
only the first 3:00 is evaluated.

You therefore have to pick one of two things, deliberately, before you start:

1. **Speak at 180 words a minute** and keep everything. 2:49, with 7 to 11
   seconds of margin. This is the recommended run.
2. **Speak at 165 and drop the stack line** from the close, the sentence
   beginning "And none of that is on my word" (24 words, about 9 seconds). The
   three green dots are still on screen and the API run has just made the same
   "check it yourself" point, so the close still lands. That gives 2:51.

Do not try to have both at 165. Do not speed up mid-take to rescue a number:
**a clear 2:51 beats a 3:00 that gets cut off mid-sentence.**

Narration is **393 words**. Forty-three of them are spoken *over* the triage
agent's wait and thirteen more over the API run, so those fifty-six cost almost
no wall-clock time.

**Your speaking pace decides whether this is comfortable or tight.** The table
below is built from each beat's own word count plus the presses and waits that
beat contains, rather than from a single guess at the total:

| pace | run lands at | margin to 3:00 |
|---|---|---|
| calm, 165 words a minute | **3:00**, or 3:04 if the agent is slow | **none, this overruns** |
| brisk, 180 words a minute | **2:49**, or 2:53 if the agent is slow | 7 to 11 seconds |

The "presses and waits" column is a human allowance. Measured on the deployed
revision at 1440x900, the machine's own response time is smaller: sweep 7.8s,
row to chart 0.4s, score 4.0s, profile 1.5s, sample verdict 1.6s, stack 0.9s,
and the agent 18.1s. The sweep is the slow one: `query_ms` is about two seconds
but press-to-rows is nearly eight, because the round trip through the load
balancer, Cloud Run and the MCP server is not free. The table below allows 33
seconds in total, which covers your hand and eye as well as the server.

| beat | words | speech | presses and waits | ends |
|---|---|---|---|---|
| The gap | 43 | 16s | a still hero, nothing to press | 0:15 |
| Run the sweep | 42 | 15s | **8s**: press to rows, measured, not the 2s query time | 0:39 |
| The case other checkers miss | 58 | 21s | 4s: click a row, the chart draws | 1:04 |
| Prove it isn't circular | 33 | 12s | 6s: press, the score computes | 1:22 |
| Findings become an action | 54 | 20s | 4s: press, the profile returns | 1:46 |
| The agent | 68 | 25s | the 12 to 20 second wait is covered by the line written for it | 2:10 |
| One-file workflow | 29 | 11s | 3s: one click, decode and verdict | 2:24 |
| The API, in one press | 13 | 5s | 9s: nine endpoints, measured 7.3s warm and 11.6s cold, spoken over | 2:33 |
| Credibility, shown not said | 0 | 0s | 4s: a silent dwell on the greyed row | 2:37 |
| Proof, and close | 53 | 19s | 4s: press, the stack answers | **3:00** |

An earlier version of this page claimed 2:39 to 2:41 at 165 words a minute. That
was wrong in a specific way worth knowing: it counted the words honestly but
under-counted the presses and returns between them, and the sweep alone takes
four seconds longer than it allowed. Rebuilt from the beats and checked against
the deployed revision, 165 words a minute gives 2:51. **If you want real margin,
speak at 180.**

Two things follow from the table. **The close is the longest unbroken stretch of
speech in the whole run and it sits at the very end**, where an overrun is fatal
rather than recoverable, so it is the beat to rehearse. And the criteria beat,
which used to cost about ten seconds of narration to say what the screen says on
its own, is now a four-second silent dwell. That is where most of the recovered
time came from.

The margin is the point. It absorbs a slower delivery, a fumbled click, or an
agent having a bad minute. Anything you add spends it.

Ten beats, and they are not equal. The red-flash case and the four-profile
result carry Potential Impact and Quality of the Idea between them; the agent
and the closing stack check carry Technological Implementation. Those four are
the reason to make the video at all. The evaluation beat is one line on purpose
and the criteria beat is silent: their numbers are legible on screen, so
narrating them twice would spend the time the four above need.

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
- **Press "Run every endpoint" once before you record, then reload.** Measured
  cold it takes 11.6 seconds and warm 7.3, and the timing above assumes warm.
  Four seconds is the whole margin at 180 words a minute.
- The triage agent takes 12–20 seconds. Do not cut it: the wait is the proof.
  The narration for that beat is deliberately short so you can talk over it.
- Read numbers **off the screen**. The catalogue is live and a row you click may
  differ by one or two from the figures below.
- **Rehearse the silent criteria beat.** The provenance table is behind a
  disclosure now, so that beat is a press, a cursor move and a two-second dwell
  in four seconds, with no narration to hide a fumble.
- The header nav now carries **Criteria**, between **API** and **Stack**. It was
  added for this beat: the section existed and was linked from the contents map,
  but there was no chip for it, which made a four-second silent beat into a
  scroll hunt.

---

## 0:00–0:15, The gap

**DO:** Hero section, still. Do not scroll. The contents map under the hero
names every panel; the header nav repeats the main six and follows you down.
**POINT:** The headline, *"The master passed. The version people watched was
never checked."*

**SAY:**

> **"A film is approved once, then becomes dozens of versions: frame rates,
> ad-break inserts, social crops. Testing runs on the master, before all of
> that. Safe Frame helps studio and streaming QC teams find the exact
> rendition, and transformation, that introduced the risk."**

---

## 0:15–0:39, Run the sweep

**DO:** Click **Sweep** in the header nav. Press **Sweep the catalogue**.
**POINT:** The four counters while it runs.

**SAY:**

> **"Four hundred and twenty-four titles. Ten million transitions. Both
> published flash rules across all of it in one pass, through the official
> ClickHouse MCP server."**

**POINT:** The result headline, then the **Rule** column.

*This line used to say "under two seconds". Measured on the deployed revision,
`query_ms` came back at 1909, 2048, 2138 and 2383 milliseconds on a warm
session, and 3938 on a cold one. Three of those four contradict "under two", and
the number is printed on screen next to your voice. "About two seconds" is true
across the warm range, which is why the pre-record step warms the session. **If
the panel shows something else, say what the panel shows.***

> **"About two seconds. Sixty-six renditions introduced a violation their
> approved master never had, forty-three luminance, twenty-three red."**

---

## 0:39–1:04, The case other checkers miss

**DO:** Click any row whose **Rule** reads **Red flash**. Wait for the chart.
**POINT:** The top track, then the bottom track.

**SAY:**

> **"The approved master stays under the limit for its whole runtime. The
> transformed rendition crosses it, more than twenty qualifying transitions in
> one second, against a limit of six."**

**POINT:** Trace the **blue** series along the bottom track. It stays flat.

> **"But the luminance line here barely moves. Saturated red has its own
> published test, which applies even at steady brightness. A luminance-only
> checker passes this file. This one doesn't."**

---

## 1:04–1:22, Prove it isn't circular

**DO:** Click **Evidence** in the header nav. Press **Score the detector**.
**POINT:** The four tiles, left to right.

**POINT:** The **found and planted** tile, then **decoys correctly rejected**.

**SAY:**

> **"Synthetic data, so don't just believe it. This recovers what was planted
> using a query that reads no flash measurement. Sixty-six for sixty-six, and
> eighty-six decoys that really do flash, correctly left alone."**

---

## 1:22–1:46, Findings become an action

**DO:** Click **Cause** in the header nav. Press **Profile every transform**.
**POINT:** The four coloured bars, then the clean rows beneath them.

**SAY:**

> **"Sixty-six findings are not sixty-six separate problems. Every one traces
> back to four encoder profiles, while three profiles remain clean. A QC team
> can fix four upstream configurations instead of manually patching sixty-six
> outputs, and prevent the same profiles from creating more unsafe versions."**

*The sweep counters above read **8 transform types** while this line says four
plus three. Both are right: the eighth value is `master`, the approved parent
itself, which is a lineage role and not a conversion. There are seven conversion
profiles, four of which regress. Verified live: `transforms_implicated` is 4 and
`transforms_clean` is 3 at `/v1/catalogue/transform-risk`. If a judge asks, that
is the answer.*

**POINT:** The middle outcome tile.

> **"Twenty-three regressions would be missed entirely by a luminance-only
> workflow."**

---

## 1:46–2:10, The agent

**DO:** Click **Agent** in the header nav. Press **Run the triage agent**.
**POINT:** Keep the working state visible. Let the wait run.

**SAY:**

> **"Now Gemini, through Google's Agent Development Kit on Vertex AI. Its four
> tools run live ClickHouse queries through MCP. It surveys the catalogue,
> profiles the transforms, measures the red-flash blind spot, and investigates
> the highest-priority case. The model chooses which case to prioritise."**

*(The line above runs about sixteen seconds, roughly the length of the wait.
Deliver it at the same pace as everything else. If the agent is still working
when you finish, hold the silence; do not fill it.)*

**POINT:** When the brief lands, run your cursor down the **numbered trace**.

> **"This is the real tool sequence from this run. Every number came from
> SQL."**

**POINT:** `decision_source` and `requires_human` in the panel beside it.

> **"ClickHouse decides, Gemini explains, and a human remains responsible for
> acting."**

---

## 2:10–2:24, One-file workflow

**DO:** Click **Your video** in the header nav, then the sample button **A
rendition that regressed**. One click, no file dialog. It returns in about two
seconds.
**POINT:** The verdict, then **Decision**.

**SAY:**

> **"Everything so far used the catalogue. This sample follows the same
> browser-side path available for a user's own video. Frames remain local, they
> are never displayed, uploaded, or stored."**

*Use the sample button rather than the file picker. A file dialog on camera is
slow, shows your own filesystem, and can fail in a way you cannot recover from
mid-take. The samples are served by the app and decode through the identical
path.*

---

## 2:24–2:33, The API, in one press

**DO:** Click **API** in the header nav. Press **Run every endpoint**. Nine
endpoints tick through in the browser, warm in about seven seconds and about
twelve on the first press of a session. **Speak the line over the run**, the
way you did for the agent: the rows filling in are the point, not the wait.
**POINT:** The summary line under the rows when it lands.

**SAY:**

> **"And it is a public API. Nine endpoints, no key needed, running now."**

*The screen finishes the sentence: "9 of 9 returned 200". Read whatever the
summary actually says. The endpoints that spend model tokens are deliberately
not in this loop, which is worth knowing if a judge asks why the agent is
missing from it.*

---

## 2:33–2:37, Credibility, shown not said

**DO:** Click **Criteria** in the header nav. The threshold table now sits
behind a disclosure, so press the summary line once to open it. Rest the cursor
on the greyed **Spatial pattern, not implemented** row, the last row in the
table, for about two seconds. Then keep moving to Stack. **Say nothing over
this.**

*This beat used to cost ten seconds of narration to make a point the screen
makes on its own. A judge who cares about the unimplemented rule will read it;
a judge who does not loses nothing. The time buys margin at the close.*

*Four seconds is enough for a press, a cursor move and a two-second dwell, but
only if you have done it once. It is silent, so there are no words to stumble
over, but there is a click to miss. Rehearse this one.*

---

## 2:37–3:00, Proof, and close

**DO:** Click **Stack** in the header nav. Press **Check the stack**. It returns in
about four seconds. This is where the demo ends.
**POINT:** The three green dots in the ClickHouse and Google rows.

**SAY:**

> **"And none of that is on my word. ClickHouse just reported its own version,
> the MCP server listed its own tools, and Vertex answered."**

**POINT:** The **Safe Frame** name in the sticky header, top-left.

> **"Safe Frame finds the version that introduced the risk, traces it to the
> system that caused it, and gives QC teams evidence to prevent it from reaching
> an audience."**

---

## Shot checklist

- [ ] Sweep pressed live, result not cut
- [ ] A **Red flash** row selected, chart drawn on camera
- [ ] The flat luminance line on that rendition traced explicitly
- [ ] Evaluation scored live: **66/66**, decoys **86/86**, cohort row shown
- [ ] Transform profile run live, four-versus-three point made
- [ ] Triage agent run live, numbered trace visible, **wait not cut**
- [ ] `decision_source` and `requires_human` legible on screen
- [ ] A sample scenario checked live, verdict and decision source visible
- [ ] **Run every endpoint** pressed live, nine 200s visible on screen
- [ ] The **not implemented** row rested on, silently, on the way to Stack
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
| Potential Impact | the red-flash case a luminance-only checker passes, and four upstream configurations to fix instead of sixty-six outputs to patch, which also stops the next unsafe version being made |
| Quality of the Idea | a non-obvious master-versus-rendition comparison that existing file-level checks do not address, with the unimplemented rule named rather than hidden |

The arc is one sentence: **find the regression → prove it isn't circular → show
what other checkers miss → name the cause → let the agent prioritise the work.**

## Things deliberately left out

Cut for time, and because each would dilute the arc rather than add to it. If a
judge asks, they are all on the page or in the repository.

- **Minting an API key on camera.** The runner beat shows the API answering
  without a credential, which is the stronger claim and costs nine seconds
  rather than twenty. The key generator, the copy button and `/docs` are all on
  the page if a judge wants them.
- **Runtime evidence**: the MCP handshake and the credential-boundary diagram.
  The closing stack check now carries that point in less time.
- **Decision boundary**: the SQL panel. The agent section makes the same point
  faster, on camera, with live output.
- The sample-file player, the findings export, the Plain/Technical toggle, and
  the light/dark toggle.
- The standards audit that found three defects in our own detector. It is the
  best thing in the repository and there is no room for it; put a line about it
  in the Devpost description instead.

## If you overrun

At 180 words a minute the margin is 7 to 11 seconds, and at 165 there is none
at all, so this list is not hypothetical. Cut in this order. Never cut the red-flash beat or the
four-profile result, they carry Potential Impact and Quality of the Idea
between them.

1. The `decision_source` / `requires_human` line (12 words). The fields stay
   visible on screen either way.
2. The criteria beat entirely (no words, about four seconds). It is already
   silent; skipping the pause is the last easy second.
3. The stack line in the close, from "And none of that is on my word" to
   "and Vertex answered" (24 words, 9 seconds). The three green dots are on
   screen and the final sentence still lands. This is the largest single saving
   available and it is in the beat with the least room for error.
4. The **twenty-three red-flash** line (10 words), but only if you must: it is
   the single sentence that names the blind spot in numbers.

Never cut the agent's opening line. It is written to run the length of the
agent's wait, so removing it does not save time, it creates dead air.
