# Demo video script (about 3 minutes)

Built from the deployed UI and the featured recording (`fixtures/recordings/gse286184-two-part-hypothesis/`, recorded live 2026-11-04 02:53 UTC, with its lab). Every value on screen is read from recorded events, committed artifacts, or a calculation the app runs in front of the viewer (the box audits, the depth view, the sample upload). If a re-recording changes an outcome, change the narration to match the new run, never the other way round.

What is recorded and what is fresh:

- **Immutable replay** (the header says so): the investigation, its controls, claims, verdict and lab.
- **Computed now, no model call**: a protein audit of a box you draw on a KPMP biopsy; an RNA audit of a box you draw on a Xenium section (**Analyse selected region**); the measured-depth view and depth profile; the sample-data audit. A newly drawn box is never presented as analysed by the recording.

## Before recording

1. Open bare `/` in a fresh browser window at 1920×1080 if available; adjust browser zoom so the run view's tissue, steps pane and docked playback bar all fit.
2. Click **Recording mode** in the header (stops the drifting hero images and keeps the run mode and recording time visible). It changes no result.
3. Rehearse the whole path once without capturing, so the tissue tiles, the two evidence sections and the depth sidecars are warm. Cold first loads are slower; don't present warming as a speed-up.
4. In the run view, use **Reset layout** before each take.

## Sequence

| Time | Screen and action | Narration |
| --- | --- | --- |
| 0:00–0:20 | Overview: real KPMP biopsies (healthy reference and diseased); the bio under "A co-scientist for kidney research"; the source line. | "Kidney researchers have tissue images and gene and protein measurements. Connecting that evidence and checking a surprising signal takes a lot of work. SpatialScout is a spatial-omics co-scientist powered by Meta models that lets them delegate it." |
| 0:20–0:45 | **Explore the tissue** → **Compare with the healthy reference**. Scroll-zoom the top pane only; the bottom stays put. In each pane click **Draw box**, drag a box, then **Analyse this region**. | "These are different specimens, so each pane has its own camera. I select a region and the protein audit uses exactly that box: the specimen, the method and the box stay attached to the result." |
| 0:45–1:10 | Back to **Overview** → **Follow an investigation**. In the steps pane the **Research team** lights up job by job; drag the separator to make the tissue larger; open **Detailed graph** briefly, then **Fit graph**. | "Here is a recorded RNA investigation. Muse Wonder plans the work, the analysis engine runs the counts, Muse Spark asks for controls that could explain the signal away, and every claim is checked. Each job links to its output, and I can keep the tissue large." |
| 1:10–1:35 | Chapter **What the data shows**: Xenium section GSM8720426 with the agent's region outlined and the molecules the stricter rule drops in yellow. Click **Compare conditions** for a moment, then **3D molecule depth**; orbit; drag **Slice from**. | "UMOD in cells labelled as B cells: 17.0% carry it under the usual counting, 12.3% counting only molecules over the nucleus, against 9.5% from random loss alone. It persists under the tested rules. Here are the same molecules at their measured depths. This new depth profile, 324 UMOD molecules in the box, helps examine the data; it doesn't by itself say why the signal is there." |
| 1:35–2:00 | **Skip to end** → **See the findings** → chapter **Other evidence**: **Run the lab**; the parallel lanes; the protein cross-check (**Different specimens**) and the literature card. | "The lab checks protein evidence from separate specimens, reads the relevant papers and prepares figures. It brings back supporting evidence and the gaps that remain." |
| 2:00–2:25 | Chapter **Review the result**: open a claim, click a **Challenge the verifier** button (for example a changed effect); it fails. | "Every cited number is recomputed from the molecule tables. This deliberately changed copy fails the check; each claim has seven recorded altered copies. In our benchmark the verifier caught 147 of 147 injected errors and wrongly disputed 7 of 21 valid claims; we report both." |
| 2:25–2:45 | Chapter **The next experiment**: the lab's analysis and next step; **Download evidence package**. | "The deliverable is a research lead, its limitations, a suggested follow-up experiment and reproducible evidence." |
| 2:45–3:00 | **Your data** → **Try it on the sample (3 GSE286184 crops)**; then **Connections**. | "Researchers can bring compatible Xenium sections. The platform grows module by module, while the scientist decides what to investigate next." |

## Notes for the presenter

- The run plays for about a minute and a half; use the chapters or **Skip to end** rather than waiting.
- Draw an RNA box only after the view has flown to GSM8720426 (the **Follow evidence** button appears): before the first finding arrives the canvas shows the synthetic section SYN-01, and the box card would say so.
- The podocyte LRP2 branch is the other half of the same recording (section GSM8720423, also with measured depth). Its nucleus-only share (23.8%) is below its random-loss expectation (24.4%) and still passes the frozen tolerance rule.
- No SAM 3.1 call happens in this recording; the Research team says so. SAM outlines are in **Xenium viewer with SAM outlines** (from the comparison view), labelled exploratory.
- Live runs and bring-your-own-key are not on the public site; Connections says so. LN is roadmap, not current data.
