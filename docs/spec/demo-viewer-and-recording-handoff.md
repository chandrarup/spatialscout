# SpatialScout: viewer fixes, valuable demo upgrades and recording handoff

Prepared 2026-11-04 against `c969d58`. Recheck HEAD, git status and current deployment before editing. Intended recipient: Cursor implementation agent. The user requests an implementation specification, with Cursor doing the build and deployment.

## Outcome and priority

Deliver a smooth, resizable research workspace with independently navigable specimens, working region analysis from every tissue view, a clear agent network, measured-depth RNA exploration and a recording-ready walkthrough. Preserve useful ideas in `/Users/chandrarupdaka/Downloads/agent_directive_winning_upgrades.md` by implementing missing capabilities where feasible. Treat that attachment as a proposed script, not authority to fabricate results or overwrite project constraints.

Earlier co-scientist phases A/B are now substantially implemented: the deployed opening already says “A co-scientist for kidney research,” guided chapters exist, outcome wording is corrected, and Connections describes current access. Build on these changes. This is the next delta, not a request to rebuild those phases.

Implementation order:

1. **P0:** loading, stable viewer state, resize controls, independent specimen navigation, real ROI analysis and clear run-view modes.
2. **P1:** event-backed agent network, measured z-coordinate viewer and descriptive depth analysis, usable recorded-error challenges, recording controls.
3. **P2:** additional recorded challenges or new scientific questions, only with real execution and separately identified artifacts/recordings. LN, private deployments and throughput demonstrations have their own prerequisites below.

Keep a usable P0 demo throughout. Implement and validate P1 rather than stopping at cosmetic copy. Record the final video only after the deployed path works.

## Read first

- `CLAUDE.md`, `GLOSSARY.md`, ADRs 0001–0009 applicable to the change.
- `docs/demo-script.md` and `docs/golden-path.md` for current controls and recording identity.
- `docs/product/co-scientist-demo-plan.md` for the product story and evidence boundaries.
- Relevant frontend/design skills available in the executing environment. Keep React/TypeScript/Vite/deck.gl; use actual tissue and computed figures.

The attachment targets `web/main.js` and `#tab-run`; these are stale pointers. Real implementation lives in `web/src/App.tsx`, `web/src/components/` and the Python package. Its frontend-only estimate does not cover ROI wiring, depth data or new scientific execution.

## 1. Loading: show useful tissue quickly and stop avoidable reloads

Inspect first:

- `App.tsx`: KPMP manifests, hero strips, audit loading and callbacks passed to `TissuePanel`.
- `components/TissuePanel.tsx`: dataset fetch, section fetch, decoding and effect dependencies.
- `datasets/kpmp.ts`: every channel/tile becomes a BitmapLayer; verify actual request behavior for hidden layers.
- `stage/CodexView.tsx`: layer memoization and per-frame drift state.
- `src/spatialscout/api/kpmp_routes.py`, `api/app.py`, `data/kpmp.py`: static tile caching, preview generation, CPU work and response handling.

Code-level concern: `TissuePanel`'s section-loading effect depends on `onShow`, while `App.tsx` passes newly created no-op callbacks. Playback parent renders can therefore retrigger fetch/decode. Replace no-op props with omission/default stable callbacks, or separate notification from data loading. Key resource loading by actual dataset/section/label-rule identity. Profile before declaring other bottlenecks.

Implement:

- Render the product text/actions immediately; reserve image space with a visible loading/error state.
- Supply a lightweight preview for the initial healthy/disease hero pair, with participant/channel provenance. Replace it with interactive layers progressively. A preview must use the same source and documented display treatment; retain full-resolution analytical data separately.
- Load the first useful visible channels/tiles first. Defer alternate biopsies, hidden channels, cells/ROI audit tables and the RNA viewer until needed. Measure which requests are actually deferred.
- Reuse in-flight loads and decoded buffers across stages, with bounded caches and explicit invalidation. Cancellation/stale-response handling must stop an older participant/section from replacing the newly selected one.
- Use stable layer data and avoid rebuilding expensive buffers on narration, panel resizing or camera movement. Drift should not require the whole app to render every frame; disable it in recording mode/reduced motion.
- Give immutable versioned preview/tile assets cacheable URLs; preserve HTML revalidation so redeploys remain visible. Keep metadata and clinical provenance current.
- Distinguish network, metadata, image and WebGL readiness; a synchronous adapter `load()` completing does not mean its textures have loaded.

Acceptance: measure cold-cache and warm-cache loads at the same viewport/network profile before and after. Report time to text, first correct tissue, all initial visible channels, requests and transferred bytes. Initial text must remain usable while images load; no repeated whole-section fetch per playback event; no flashing reset on a resize; failed layers get retry affordances. Choose and report performance targets after the baseline; do not invent achieved timings.

## 2. Replace the narrow bio and keep the useful example

Use: **“SpatialScout is a spatial-omics co-scientist powered by Meta models. Delegate investigations across kidney tissue images, gene and protein measurements, and scientific literature. Specialised agents run the available tools, test alternative explanations and assemble evidence for the next experiment.”**

Put the RNA-assignment explanation beneath this as the first completed module. Keep a short source line: **“Human kidney RNA cohort includes DKD; protein images are from separate healthy/CKD/AKI specimens.”**

The opening should name kidney disease research, show tissue and offer **Follow an investigation** and **Explore the tissue**. Keep bare `/` as the explanatory Overview; select the flagship recording for the primary action. Preserve the shared `#inv-22e74f687b16` link and its original recording identity.

Acceptance: no old bio remains as the primary product description; the opening explains audience, delegated work and current data. LN is displayed as roadmap until its cohort is implemented. Product attribution remains independent and Meta-powered.

## 3. Make the canvas and panels adjustable

Current issue: the run rail uses fixed `w-[min(44vw,620px)]`, large bottom padding and a fixed playback overlay. Expand/hide controls are not continuous resizing.

Implement an accessible split layout with a draggable, keyboard-operable separator between tissue and task/evidence panes. Provide sensible minimum widths, expand/collapse, reset layout, **Fit tissue** and **Fit graph**. Recalculate canvas dimensions with ResizeObserver while preserving the user's camera and ROI; refit only on an explicit action or changed source. Persist layout preference without storing private analysis data.

Dock playback/narration in its own layout row, or allow it to collapse. It must not cover tissue, boxes, graph nodes or result actions. On phones use tabs/stacking rather than two narrow canvases. Stop auto-follow from recentering a manually inspected view until the user selects **Follow evidence** again.

Acceptance: resize repeatedly during playback, pause, zoom, ROI drawing and graph interaction; no request storm, camera reset, pointer conflict or obscured controls. Test pointer, keyboard, touch and narrow layouts.

## 4. Distinguish different specimens from two conditions of the same specimen

There are three different comparison implementations:

- `DualViewer.tsx` initializes `linked=true` and moves the other camera by the same delta.
- `stage/CompareView.tsx` uses a separate `CodexView` per participant. Cameras are already local there, but box controls are not wired. Shared protein toggles are a separate behavior from camera linkage.
- `Viewer.tsx`'s divider compares **the same RNA section** under default versus stricter assignment, using a shared camera. Those halves are not different biopsies.

Implement:

- Different specimens: independent cameras by default. Per-pane **Pan**, **Draw box**, **Fit**, selection and source labels. An optional **Link navigation** control may share scale/movement, with a clear note that specimens are not registered. Changing one participant clears that pane's selection only. Separate optional channel linking from camera linking.
- Recorded RNA run: default to one uncluttered tissue canvas. Add **Usual assignment**, **Stricter assignment**, **Show excluded molecules**, and an optional **Compare conditions** view. If retaining the divider, label it **Same section, different counting rules** and show it only after explicit comparison selection. Independent cameras can be available for side-by-side exploration; an aligned comparison mode may deliberately link them.
- Source identity always includes dataset, section/participant and assay. Keep different-specimen badges for RNA/protein evidence.

Acceptance: pan/zoom left specimen while right stays unchanged; draw distinct boxes in each; reset one without changing the other. In the RNA view, the selected rule and excluded molecules match the same source section. Users can return to a single canvas without losing focus.

## 5. Make region selection actually drive analysis

Verified gaps:

- `CompareView.Strip` passes no `boxMode`, `box` or `onBox` to `CodexView`, although the renderer supports these.
- `App.tsx` discards the classic `DualViewer` context with `onContext={() => undefined}`.
- `Explore.TissueContext` carries a description/markers rather than a full rectangle, and `App.start()` always sends `regions: []`.
- The orchestrator can persist valid RNA regions but that alone does not scope computations or supply protein support. The RNA tool already has an explicit `roi`; KPMP has its own protein-audit endpoint. Immutable replay ignores new regions.

Implement one structured selection contract carried end-to-end: dataset ID, section/participant ID, assay, rectangle and units, selected markers/genes, pane ID and scope. Preserve image rotation/coordinate transforms. In `CodexView` use the existing `toWorld`/`toSection` conversion; validate offsets, clamping and nonzero bounds.

### Protein images

Add **Draw box**, clear/edit and **Analyse this region** to each comparison pane. Call the existing KPMP protein audit with that participant's real x0/y0/x1/y1. Show a result tied to that exact selection and thresholds. This deterministic calculation works without model credits.

**Ask about this region** must retain and display the structured selection. Supported questions can use the computed local protein evidence. If adding model-led interpretation, register an explicit protein tool/context path; KPMP regions must not be passed off as GSE286184 RNA regions. Unsupported requests should explain the missing assay/tool. Comparison of two boxes is descriptive, with separate specimen identities and denominators.

### RNA regions

Carry selections through question submission, plan and tool arguments. A local audit actually filters by its `roi`; every resulting artifact/figure states its local scope. A single box may lack the cohort eligibility required for a stable label: still show computed descriptive counts and an honest insufficient-evidence state.

Expose two distinct actions when appropriate: **Analyse selected region** for a fresh deterministic/supported analysis, and **Open recorded investigation** for the unchanged cohort replay. A newly selected box must never appear to have been analysed by an old immutable recording. Using a cached model response with changed ROI requires a matching cache identity; a replay miss is not permission to fabricate a response.

Acceptance: network/request and backend tests prove the same rectangle and source reach the calculation. Moving/redrawing a box changes the input/result where data differs. Switching participants cannot reuse a stale result. Test known small coordinate tables, rotated images, partly out-of-bounds/empty boxes and independent paired selections. Verify all replay limits remain visible.

## 6. Preserve the script's agent-network idea with real execution

Add a concise **Research team** view backed by actual events:

1. **Plan** — Wonder decomposes the task and selects supported work.
2. **Analyse** — deterministic spatial/protein tools compute measurements; exploratory SAM proposals appear only if actually invoked.
3. **Check alternatives** — executed thinning and label-sensitivity controls, with reasons and rejected requests.
4. **Review evidence** — structural/numerical verification and Spark figure inspection.
5. **Assemble next steps** — lab literature/protein/figure tasks and report.

Read node status, model identity, cost, latency, outputs and dependencies from events/registry. Click a node to open its output. Show real lab concurrency from recorded start/end timestamps. The main audit has dependencies and must not be relabelled a fully parallel swarm. Keep the detailed graph available in a resizable pane.

Voice is optional input, not a supervisor. Wonder plans; Spark Open drafts claims. A deterministic verdict rule is not another LLM. SAM must not glow as though it ran during the featured audit if that recording lacks a SAM invocation. A spoken clip/transcription can be demonstrated separately with its actual provenance.

Acceptance: every active/completed node is explainable by served events; seeking backward restores the correct state; no hardcoded step numbers fabricate model use. The view remains readable without knowing model names.

## 7. Add real measured-depth exploration and a useful depth analysis

### What is available

Current `SectionTables`, packed API and `web/src/packed.ts` expose x/y only; `Viewer` uses OrthographicView. The present scientific audit and protein displays are 2D/projected.

Raw-data inspection in this pass verified a measured `z_location` column in `data/raw/GSE286184/GSM8720430/*transcripts.parquet.gz`: 819,868 non-null values, range 9.5625–25.671875 in the raw coordinate scale. This is evidence for implementing depth support, not a guarantee about every section or the selected recorded region. Verify actual units and depth coverage of the recording's evidence sections before displaying them. Multiple protein channels are not depth slices.

### Implement the depth path

- Build a versioned visualization-side depth artifact for the recorded evidence sections from the original molecule IDs and x/y/z. Join by stable transcript ID; verify one-to-one identity, quality filtering and coordinate agreement with the existing displayed molecules. Include source checksum, coordinate units, section ID, valid/missing-depth counts and transform metadata.
- Prefer a separate visualization endpoint/sidecar so the frozen analysis inputs, audit artifacts, cache keys and recording hashes stay unchanged. If changing shared contracts, preserve old payload compatibility and regenerate TS contracts. Do not silently reassign rows by array order after filtering.
- Serve only the selected ROI/genes/depth extent initially, with bounded point budgets. Use typed buffers, deterministic display sampling and clear sampled/displayed/total counts. Analytical counts always use the full eligible set, not the rendered sample.
- Add **2D map / 3D molecule depth** mode using an orbit-capable deck.gl view. Provide rotate, pan, zoom, reset, z-range slider and depth colouring. Use physical aspect ratio by default; if offering z exaggeration, display its factor. Synthetic depth and fabricated tissue surfaces are excluded.
- Projected cell/nucleus outlines may be shown on a labelled reference plane; they are not reconstructed cell volumes. Keep 2D SAM masks on that plane and label them accordingly.
- If a specific section lacks verified depth, show the reason and another verified compatible section where useful. Do not enable 3D solely because the original table has a column name.

### Add a genuine descriptive depth task

For the chosen RNA ROI, compute a separate **Depth profile** artifact: full-data transcript counts by depth interval, gene and existing assignment condition, with bin bounds, units, missing-value counts and source hashes. The user can move a depth slice and inspect its local counts. Label this **New descriptive depth exploration** alongside the older recorded analysis. It can run deterministically without a new model call.

This does not prove vertical overlap caused a signal or provide a 3D segmentation correction. To claim a new 3D biological analysis or an agent's depth-based conclusion, implement the method and run/verify a separate new investigation with an appropriate recording. Preserve the old 2D verdicts.

Acceptance: fixture with known x/y/z and missing values round-trips through the endpoint; ID join mismatches fail visibly; bin sums match full-data totals; slice bounds are correct; physical scales are accurate; rendering sampling does not alter scientific counts; replay package hashes remain unchanged. Test the actual recorded evidence ROI on deployed code.

## 8. SAM status and how to show it usefully

The repository implements pretrained **SAM 3.1 with box prompts**, not fine-tuning. ADR-0006 makes its RNA-rendered outlines exploratory and excludes them from primary evidence labels.

Expose **Outline this region with SAM** where supported, with recorded versus live status, actual mask geometry, seed box/baseline comparisons and recorded failures. This is useful model/tool interaction without claiming a trained pathology model. A fresh arbitrary box may require a live model call; reuse only an exact matching recorded response.

If fine-tuning is desired later, it is a separate research project needing appropriate training support/checkpoint, annotated examples, held-out evaluation and artifacts. It is not required for this demo upgrade. Do not replace the current prompted model with a claimed tuned version without that evidence.

## 9. Keep valuable script claims by implementing their prerequisites

| Script idea | Implementation that adds value | Wording until implemented |
| --- | --- | --- |
| Five-stage agent network | Section 6, real events and output links | Describe actual specialised jobs. |
| Six adversarial checks | Surface the recorded challenge variants; if six examples are desired, select six genuinely available cases and show each result. If adding new live tests, store new artifacts/timestamps separately from the old run. | The main recording currently contains one deliberately wrong copy; benchmark results and challenge variants are separate evidence. |
| Gigapixel/multichannel image handling | Demonstrate the real curated TIFF-to-tile pipeline, dimensions/channel count from metadata and bounded crop retrieval | Tiled curated CODEX images; general TIFF upload remains separate work. |
| 3D insight | Implement measured-depth viewer/profile in section 7 | Depth exploration; no claimed proof of z-overlap mechanism. |
| LN analysis | Add an actual LN dataset, panel/metadata checks and appropriate analysis/recording | LN is an expansion, not current cohort coverage. |
| 2M-TPM swarm | A real throughput/concurrency test with request/token/time records and account limits | Provider quota is not achieved throughput; report measured calls and cost. |
| Hospital-private workflow | Deploy and validate an actual private data/compute/inference configuration with explicit provider egress | Public demo uses public data; open weights make other deployment options possible. |
| Weeks to minutes | Time the same predefined task manually and with the app, independently check completeness/correctness | Report recorded system execution and tasks delegated; human savings unmeasured. |

Keep the title **Meta-powered spatial co-scientist** rather than suggesting an official Meta launch. Read measured corpus size from the manifest; avoid implying every investigation scans all deposited molecules. Keep benchmark true-positive and false-positive results together.

## 10. Recording mode, script and capture procedure

Implement **Recording mode** as a UI preference: readable labels, stable layout, no decorative drift, collapsible help, visible provenance/mode and persistent playback controls. It may prepare assets, but must not change scientific outcomes or imply replay is live.

### Rehearsal after deployment

1. Open bare `/` in a fresh browser session; verify deployed build/version and new opening. Use 1920×1080 capture if available; set browser zoom so panels and labels fit rather than assuming 110% works.
2. Warm the selected tissue/recording assets for the actual video. Separately measure cold load so warming is not presented as a performance improvement. Clear previous selections and reset layout/cameras.
3. Test the entire path below once with no capture. Check box analyses, selected participant identities, error challenge, depth mode and evidence download.
4. Capture screen and narration with the user's preferred recording tool. Record short takes per beat; editing out waits is acceptable if compressed playback/waits remain honestly described. Include actual run-mode labels. Do not hide a failure behind an invented successful state.
5. Watch the exported video: text readable, pointer visible, audio intelligible, correct figures, no exposed keys/private files, no UI overlap. Check actual portal duration/format requirements before export; 2.5–3 minutes is a target, not a verified rule.

### Suggested 3-minute sequence

| Time | Show | Narration |
| --- | --- | --- |
| 0:00–0:20 | Overview, real tissue, clear kidney focus | “Kidney researchers have tissue images and gene and protein measurements. Connecting that evidence and checking surprising signals takes substantial work. SpatialScout is a co-scientist powered by Meta models that lets them delegate that investigation.” |
| 0:20–0:45 | Compare two KPMP biopsies; independently pan, draw a box and run a real protein audit | “These are different specimens, so I can inspect them independently. I select a region and the analysis uses that exact box. The result keeps its specimen, method and scope.” |
| 0:45–1:10 | Flagship recorded investigation; resize canvas and open research-team view | “Here is a recorded RNA investigation. Wonder plans the work, specialist tasks execute the checks, and each step links to evidence. I can keep the tissue large and inspect the details when needed.” |
| 1:10–1:35 | RNA result; optional condition comparison; measured-depth mode and separate depth profile if implemented | “The signal persists under the tested counting rules. We can also inspect the measured molecule depths in this region. This new depth profile helps examine the data; it does not by itself establish why the signal is present.” |
| 1:35–2:00 | Lab task lanes, separate protein evidence and literature | “The lab checks protein evidence from separate specimens, reads relevant papers and prepares figures. It brings back supporting evidence and the gaps that remain.” |
| 2:00–2:25 | Verified number and genuine changed-number challenge | “Every cited number can be checked against the computation. This deliberately changed number fails the check. The researcher can inspect the method and evidence rather than trusting an explanation alone.” |
| 2:25–2:45 | Report, next experiment, download evidence package | “The deliverable is a research lead, its limitations, a suggested follow-up experiment and reproducible evidence.” |
| 2:45–3:00 | Compatible sample upload and Connections, only actual access choices | “Researchers can bring compatible Xenium sections. The platform grows module by module, while the scientist stays in control of what to investigate next.” |

Update `docs/demo-script.md` to the final deployed button names and actual working path. The download belongs on the findings/report page unless an actual export control is added to Your data. If a new feature is blocked, keep it out of the recorded executable path and state its remaining prerequisite in the implementation report.

## Validation and delivery

- Use existing seam tests for quantitative/ROI/depth contracts and FastAPI routes; recorded/fake model responses for provider-facing tests. Run typecheck/build and required checks after contract changes.
- Extend the smoke flow for independent cameras, paired boxes, scoped protein results, resizable run pane, explicit condition comparison, 3D/depth availability, challenge selector and package download.
- Take before/after screenshots at recording size and mobile width. Report cold/warm loading measurements and remaining bottlenecks.
- Verify old recording/audit-log/package integrity, matched source labels, refresh/reconnect and live-budget protection. New exploratory depth artifacts retain their own identity.
- Build/deploy using the existing project workflow when authorized by the user in Cursor. Verify the deployed root and shared recording link, real tissue assets, ROI endpoints, depth artifacts and video path. Deploying code alone is not completion.
- Deliver a compact report: completed items, tests, performance evidence, deployment version/URL, remaining prerequisites and the final recording checklist. Keep secrets and raw data out of git and follow the repository's secret scan before committing.

## Prompt for Cursor

> Read `docs/spec/demo-viewer-and-recording-handoff.md` in `/Users/chandrarupdaka/Documents/Personal/Projects/Meta-Hackathon` and implement its P0 and P1 changes in order. Build on the latest co-scientist UI. Preserve valuable features from the attached demo script by implementing their real data/tool paths; keep new work distinct from immutable recordings. Complete loading fixes, resizable workspace, independent specimen navigation, scoped ROI analysis, the event-backed research-team view and verified measured-depth exploration/profile. Validate locally, update `docs/demo-script.md`, then build/deploy through the existing authorized workflow and verify the deployed recording path. Report any unmet acceptance criteria and precise prerequisites rather than presenting an unfinished feature as completed.
