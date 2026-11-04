# Demo video script (about 3 minutes)

Built from the deployed UI and the featured recording (`fixtures/recordings/gse286184-two-part-hypothesis/`, recorded live 2026-11-04 02:53 UTC, with its lab). Every value on screen is read from recorded events or committed artifacts. If a re-recording changes an outcome, change the narration to match the new run, never the other way round.

Start from a fresh page at the public URL. Everything shown is immutable replay (the header says so) except the sample-data audit at the end, which computes fresh. Nothing below needs hidden setup.

| Time | Screen and action | Narration |
| --- | --- | --- |
| 0:00–0:20 | Overview: real KPMP kidney biopsies drift across the top; "A co-scientist for kidney research"; the scope line under it. | "A kidney researcher has tissue images and thousands of cell measurements. An unexpected signal may be worth following up, but first someone has to connect the evidence and test the other explanations. SpatialScout is a co-scientist for that work, powered by Meta models, starting with human kidney data that includes diabetic kidney disease." |
| 0:20–0:40 | Click **Follow an investigation**. The run opens: mission "Investigate an unexpected signal in kidney immune cells", the six chapters, and **Exact research question** folded under it. | "The researcher delegates an investigation. The exact question is kept here; the mission is its summary. SpatialScout plans the checks, runs the analysis and brings back evidence they can inspect." |
| 0:40–1:05 | Chapter **The checks**: the agent's steps play; Muse Wonder's plan, then Muse Spark 1.3 reading each result and requesting controls. | "Muse Wonder plans two analyses across 21 kidney sections. Muse Spark reads each result and asks for its controls: does random molecule loss alone explain the change, and does it depend on how cells were labelled? Code runs every analysis; no model computes a number." |
| 1:05–1:30 | Chapter **What the data shows**: the real Xenium section with the agent's region boxed; drag the divider between usual and stricter counting. | "Here the signal is UMOD in cells labelled as B cells. Under the usual counting 17.0% carry it; counting only molecules over the nucleus, 12.3%. Random molecule loss alone would predict 9.5%. It survives these checks." |
| 1:30–1:55 | **Skip to end**, **See the findings**: "Signal persists under tested rules" with the plain sentence, and the separate **Prediction check**. Scroll to **Work delegated**. | "The finding is stated as measured behaviour. The researcher predicted the B-cell signal would drop; the prediction check says refuted, which is about this test, not biological truth. Here is the work that was delegated: analyses, controls, verified claims, and an injected error the verifier caught, with the recorded time and cost. Human time saved isn't measured yet." |
| 1:55–2:20 | Chapter **Other evidence**: **Run the lab**; the parallel lanes play; scroll to the protein cross-check (**Different specimens**) and the literature card. | "Then Muse Wonder dispatches sub-agents in parallel: protein images from different kidney specimens, a literature agent reading Europe PMC with every citation checked against what it fetched, and a figure agent. The protein images are another line of evidence, not a matched repeat." |
| 2:20–2:40 | Chapter **Review the result**: the checked claims, including the deliberately wrong copy failing the numerical check. | "Every cited number is recomputed from the molecule tables. A deliberately changed number fails that check. In our benchmark the verifier caught 147 of 147 injected errors, and wrongly disputed 7 of 21 valid claims; we report both." |
| 2:40–2:55 | Chapter **The next experiment**: the lab's analysis (what happened, why, what to do next), then **Download evidence package**. | "The outcome is a research lead with its limits, a suggested follow-up such as RNAscope on human biopsies, figures, and an evidence package with a notebook that rechecks every number." |
| 2:55–3:00 | **Your data** → **Try it on the sample**; then open **Connections**. | "The same engine audits compatible Xenium sections you bring. From kidney tissue to a checked research lead, so the scientist can spend more time choosing the next experiment." |

Notes for the presenter:

- The run plays for about a minute; use the chapters or **Skip to end** rather than waiting.
- Gene symbols appear only once the problem is clear (from 1:05).
- The podocyte LRP2 branch is the other half of the same recording; open it under the findings if asked. Its nucleus-only share (23.8%) is below its random-loss expectation (24.4%) and still passes the frozen tolerance rule.
- Live runs and bring-your-own-key are not on the public site; Connections says so.
