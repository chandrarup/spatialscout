# Demo video script (about 2 minutes 50 seconds)

You record the middle (screen plus your voice). The opening and closing are Remotion clips: `video/out/intro.mp4` (22 s) and `video/out/outro.mp4` (16 s). In your editor (iMovie, CapCut, QuickTime) put intro → your screen recording → outro, and speak over the clips too. Rebuild them with `npm --prefix video run render`.

## Voiceover for the finished video

`video/out/spatialscout-demo-v2.mp4` (2:38) is the whole video: intro, the real public site driven by `video/capture.py`, and outro. Record your voice over it. Rebuild: `uv run python -u video/capture.py <url>`, then `npm --prefix video run render:demo`.

| At | On screen | Say |
| --- | --- | --- |
| 0:00 | Intro clip | "Every kidney biopsy is a crime scene. This dataset alone holds 21.8 million RNA molecules in 753,099 cells, from healthy kidneys and four diseases. Each molecule is assigned to a cell by a boundary someone drew. Draw it a little too wide, and an immune cell suddenly 'expresses' a kidney gene. So we built SpatialScout: a co-scientist powered by Meta models that works like an agentic lab." |
| 0:22 | Overview | "Today, segmentation tools give you one answer and never doubt it. General AI assistants read papers but never touch the molecule table. SpatialScout plans the analysis, runs the counts, asks for the controls that could explain a signal away, and refuses any number it can't recompute." |
| 0:34 | Healthy and diseased biopsies, zoom, two boxes | "Here's a healthy biopsy and a diseased one, from different people, so each moves on its own. I draw a region on each, and the protein audit runs on exactly that box, right now. The diseased box has too few cells, so it says insufficient evidence instead of forcing an answer." |
| 0:54 | Typing the question, free trial | "Then I ask about both regions together, and run it live on the free trial. Muse Wonder writes the plan, and it just goes." |
| 1:08 | Recorded run, research team | "While that one cooks, here's one I made earlier. Muse Wonder plans, the engine re-counts under stricter rules, Muse Spark plays the sceptic and demands controls, Spark Open drafts claims, and code rechecks every cited number." |
| 1:25 | Part 1 | "Part one: podocytes really do carry LRP2. 23.8% over the nucleus, against 24.4% expected from random loss. Confirmed." |
| 1:35 | Part 2 | "Part two was my spillover hunch. UMOD in B cells goes from 17% to 12.3%. One random-loss baseline predicts 9.5%, so under the frozen rule it persists and my hunch is refuted. But a second baseline predicts 13.7%, and the label check can't rule out mislabelled cells. A lead, not proof, and it tells me exactly how sure to be." |
| 1:47 | 3D depth | "And here are those molecules at their measured depths. It helps me inspect the data; it doesn't prove why the signal is there." |
| 1:57 | Challenge the verifier | "Now let me try to cheat. I flip one claim's direction, and the verifier catches it. Across our benchmark it caught 147 of 147 injected errors and wrongly disputed 7 of 21 valid claims. We show both." |
| 2:11 | Evidence package | "I leave with a traceable report, figures, a suggested next experiment and a verification notebook. 18 Meta model calls, 29 cents, about three minutes." |
| 2:22 | Outro clip | "It doesn't drink coffee. It doesn't sleep. It just really wants to check your numbers. Oh, and our live run? Still checking. We'll let it run. Happy scouting." |

Story: **the crime scene** (a molecule may sit in the wrong cell) → **the investigation** (you pick the suspects, the agentic lab works the case) → **the verdict** (one hunch holds, one doesn't, and it tells you how sure it is).

Every number comes from the featured recording (`fixtures/recordings/gse286184-two-part-hypothesis/`, recorded live 2026-11-04 02:53 UTC) or `artifacts/`.

## Before recording

1. Open the public site, bare `/`, browser window at 1920×1080. Click **Recording mode** in the header.
2. Rehearse once without capturing so the images are warm.
3. Open **Connections** and check the free trial still has budget.
4. Start your screen recorder. Speak slowly; 2 minutes 50 seconds total is fine up to 3:00.

## Script

### 1. Intro clip — 0:00–0:22 (play `intro.mp4`, speak over it)

> "Every kidney biopsy is a crime scene. This dataset alone holds 21.8 million RNA molecules in 753,099 cells, from healthy kidneys and four diseases. Each molecule is assigned to a cell by a boundary someone drew. Draw it a little too wide, and an immune cell suddenly 'expresses' a kidney gene. So we built SpatialScout: a co-scientist powered by Meta models that works like an agentic lab."

### 2. What's out there — 0:22–0:35

**Show:** the app's **Overview** page with the two real biopsies.

> "Today, segmentation tools give you one answer and never doubt it. General AI assistants read papers but never touch the molecule table. SpatialScout plans the analysis, runs the counts, asks for the controls that could explain a signal away, and refuses any number it can't recompute."

### 3. You pick the suspects — 0:35–1:00

**Show:**
1. Click **Explore the tissue** → **Compare with the healthy reference**.
2. Scroll-zoom the top biopsy only; the bottom stays put.
3. Top pane: **Draw box**, drag a box, **Analyse this region**. Bottom pane: same.
4. Click **Ask SpatialScout about both regions**, type: *Compare these two regions: does B-cell UMOD look like spillover in the diseased tissue but not in the healthy one?*
5. Click **Run it live (free trial)**. Let it start for 3 seconds.

> "These are real biopsies from different people, a healthy one with 28,299 cells and a diseased one with 26,524, so each moves on its own. I draw a region on each and the protein audit runs on exactly that box, right now. If there are too few cells, it says so instead of forcing an answer. Then I ask about both together. Muse Wonder writes the plan, and since this is live, it just goes."

### 4. Here's one I made earlier — 1:00–1:20

**Show:** back to **Overview** → **Follow an investigation**. Point at the **Research team** steps lighting up. Drag the separator to make the tissue bigger. Keep the replay label visible.

> "While that one cooks, here's one I made earlier: the same kind of question, recorded live last night. Muse Wonder plans, Muse Spark plays the sceptic and demands controls, Spark Open drafts claims, and scientific code runs every measurement and independently rechecks every cited number."

### 5. The verdict, honestly — 1:20–1:55

**Show:** **Skip to end** → **See the findings**. Part 1 (podocyte LRP2, **Confirmed**). Then Part 2 (B-cell UMOD) and its figure; point at the observed value and the two baselines.

> "Part one: podocytes really do carry LRP2. Counting only molecules over the nucleus, 23.8%, against 24.4% expected from random loss. Confirmed.
> Part two was my spillover hunch. UMOD in B cells goes from 17% to 12.3%. One random-loss baseline predicts 9.5%, so under the frozen rule the signal persists and my hunch is refuted. But a second baseline predicts 13.7%, and the label check can't rule out mislabelled cells. So it doesn't hand me a confident answer; it hands me a lead and tells me exactly how sure to be."

### 6. Look inside the tissue — 1:55–2:08

**Show:** chapter **What the data shows** → **3D molecule depth** (section GSM8720426). Orbit a little, drag **Slice from**.

> "And I can look at those molecules at their measured depths and slice through them. It helps me inspect the data; it doesn't prove why the signal is there."

### 7. Try to cheat — 2:08–2:22

**Show:** chapter **Review the result** → open a claim → **Challenge the verifier** → **Changed effect**. It fails.

> "Now let me try to cheat. I change one number, and the verifier catches it. Across our benchmark it caught 147 of 147 injected errors and wrongly disputed 7 of 21 valid claims. We show both."

### 8. What you walk away with — 2:22–2:34

**Show:** chapter **The next experiment** → **Download evidence package**.

> "I leave with a traceable report, figures, open questions, a suggested next experiment and a verification notebook. 18 Meta model calls, 29 cents, about three minutes."

### 9. Outro clip — 2:34–2:50 (play `outro.mp4`, speak over it)

> "It doesn't drink coffee. It doesn't sleep. It just *really* wants to check your numbers. Oh, and our live run? Still checking. We'll let it run. Happy scouting."

## Don't say

- "Meta's AI Co-Scientist": it is built on Meta models, not a Meta product.
- That the recorded run analysed the boxes you just drew. The box numbers are fresh and go to the live run as context.
- That the UMOD result proves spillover is absent, or that depth proves vertical overlap.
- "Before and after" for the two biopsies: they are different people on different protein panels.
- Lupus nephritis: roadmap, not current data.

## If something goes wrong

- Live trial out of budget: skip step 3's last click and say "or bring your own model key".
- A box shows "insufficient evidence": leave it on screen and say the line about too few cells.
- Slow image load: keep talking; cut the wait in the editor.
