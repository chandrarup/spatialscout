# SpatialScout co-scientist implementation handoff

Prepared 2026-11-04 against local HEAD `f6f1a50`. Recheck HEAD and existing work before editing. This is the user's requested implementation brief for another agent; it is not a report that these features already exist. Existing GitHub issues remain the tracker. This file provides the new requested direction and concrete completion criteria.

## Objective

Implement an understandable, polished spatial-omics co-scientist experience powered by Meta models. Start with kidney disease research and explain the work scientists can delegate. Present the existing assignment audit as the first completed investigation module inside that broader product.

The demonstration must make sense to someone who does not know gene symbols, transcriptomics or agent frameworks. Show a scientist's question, useful delegated work, inspectable evidence and a next experiment. Preserve the current scientific computations, datasets and recorded evidence.

## Start here

1. Read `CLAUDE.md`, `GLOSSARY.md` and current git status. Preserve unrelated edits and untracked recordings.
2. Read `docs/product/co-scientist-demo-plan.md`: intended copy, three-minute storyboard and visual layout. This handoff is the execution checklist; that document supplies narrative detail.
3. Read ADRs 0001, 0003, 0006, 0007, 0008 and 0009 before changing results, playback, lab, uploads or capability checks. For changed behavior, reconcile affected decisions explicitly.
4. Run and inspect the current app before editing. Record baseline views of Overview, Tissue, Run, Verdict/Lab and Your data. Use the relevant frontend design skill available in your environment, retaining the existing stack and working viewers.
5. Implement phases A–C in order. Phase D is future research scope, not a prerequisite. Complete a working phase before taking on the next. If time or a concrete blocker prevents phase C, report exactly what remains and keep the implemented access choices accurate.

Current local app commands are in `CLAUDE.md` and the Makefile. The known deployed URL is `https://chandrarupdaka--spatialscout.us-east.modal.run`. Use local work for development; deploy only under the executing agent's actual authorization. This file grants no additional permission to publish, spend money or use credentials.

## Facts every implementation must preserve

- **Product:** independent spatial-omics co-scientist built with Meta models. Attribution is “powered by Meta models”; this is not an official Meta product or a newly trained spatial foundation model.
- **RNA:** GSE286184 kidney cohort includes Control, DKD, IgAN, MCD and MN. The 50-gene panel limits supported questions. The existing featured audit pools eligible sections across groups; it does not establish a DKD-specific finding.
- **Images:** current KPMP CODEX biopsies have healthy-reference, CKD and AKI categories. These are different participants from the RNA cohort. CKD does not establish a DKD diagnosis.
- **LN:** lupus nephritis is a future application requiring an actual LN cohort. Current app screens must not imply LN was analysed.
- **Evidence:** persistence under tested restrictions supports robustness under those checks; it does not establish biological origin or rule out all contamination.
- **Statistics:** preserve descriptive disease comparisons and the donor-mapping limitations. Keep primary and exploratory SAM conditions distinct.
- **Playback:** recorded events, original questions, model outputs and scientific verdicts retain their identity and content. UI summaries are presentation metadata, never fabricated execution.
- **Measurements:** display counts, costs, timings and result values from artifacts/events. Separate recorded execution duration from compressed playback and lab duration. Describe reduced coordination or tasks delegated until human time savings are measured.
- **Uploads:** the present compatible Xenium upload audit uses temporary files and no model calls. A new model-enabled upload flow requires its own explicit data-handling description.

## Phase A — Change the story and guided demonstration

### A1. Make the first screen explain the product and domain

Likely files: `web/src/components/stage/Intro.tsx`, `web/src/App.tsx`, relevant styles.

Use this copy or an equally clear version with the same meaning:

- Headline: **A co-scientist for kidney research**
- Support: **Delegate the work of investigating tissue images, molecular signals and supporting evidence.**
- Scope: **Human kidney data. RNA cohort includes diabetic kidney disease (DKD); separate healthy/CKD/AKI protein images.**
- Primary action: **Follow an investigation**
- Secondary action: **Explore the tissue**

Show real tissue prominently. Explain the practical burden: a researcher must connect images, measurements, analysis checks and papers before deciding on another experiment. Put the border/assignment example inside the investigation rather than making it the entire product identity. Use existing assets and real computed figures.

**Done:** the opening identifies the scientist, kidney domain, delegated work and next action without requiring gene knowledge; both actions work; source and run-mode information is legible at desktop and phone widths.

### A2. Build a guided view of the actual featured recording

Likely files: `App.tsx`, `stage/AgentBar.tsx`, `stage/runGraph.ts`, `stage/RunCanvas.tsx`; add a small chapter component or presentation configuration if helpful.

Use the existing `gse286184-two-part-hypothesis` recording. Load it by a stable recording identity where possible. If the API only selects by exact question, resolve the recording's original question from its metadata and send that; do not send a presentation summary as a fabricated recorded prompt.

Audience-facing mission: **Investigate an unexpected signal in kidney immune cells.**

Summary: “Check whether it survives stricter counting, inspect available protein evidence, read relevant research and prepare the evidence for a follow-up experiment.”

Present this as a summary of the recording's UMOD/B-cell branch. Keep the complete original two-part question accessible under **Exact research question**, and preserve the LRP2/podocyte branch and all its evidence.

Chapters:

1. **The question** — researcher goal, data and expected deliverable.
2. **The checks** — actual executed analysis and controls.
3. **What the data shows** — selected RNA region and observed/expected result.
4. **Other evidence** — recorded lab, separate protein specimens and cited papers.
5. **Review the result** — numerical provenance and recorded error challenge.
6. **The next experiment** — report, unresolved questions and evidence export.

Map chapter state to real events/artifacts. Keep pause, step, speed and detailed-run access. If a chapter's artifacts are not ready, show its true state. Lab starts only after the investigation completes; playback serves its actual recording.

**Done:** one user can follow all chapters from Overview to report/export; the original question and recording identity remain accessible; refreshed investigations reconnect; no chapter invents agent decisions, outcomes or concurrency.

### A3. Put the research outcome into plain language

Likely files: `stage/Results.tsx`, `stage/LabView.tsx`, `VerdictBanner.tsx`, `ClaimCard.tsx`.

Primary wording should describe measured behavior:

- **Signal persists under tested rules**
- **Sensitive to assignment choices**
- **More evidence needed**

Use each artifact's existing evidence status. Keep recorded confirmed/refuted/inconclusive values in a separate **Prediction check**, explaining their limited meaning. Do not change the verifier, label thresholds or stored verdicts to obtain nicer copy.

Fix `LabView.tsx`'s candidate headline to say the signal in **labelled** B cells persists under the tested restrictions. The existing “not explained by ... spillover” statement is too strong. Build supporting text from actual values and rule definitions: `stable` does not always mean above the random-thinning expectation. LRP2 is 23.8% nucleus-only against 24.4% expected in the current recording and passes a tolerance-based rule.

Use readable percentages in the primary explanation; retain full precision and technical keys in details. Show remaining explanations and suggested experiments next to the lead. Literature co-mention counts describe only the fetched titles/abstracts; they do not establish novelty. A citation-ID gate checks fetched-source membership, not semantic proof of every statement.

**Done:** every primary outcome matches the actual artifact and frozen rule; neither candidate headlines nor summaries claim biological proof; both recorded branches and their controls remain inspectable; insufficient and disputed results remain visible.

## Phase B — Make the workspace and effort reduction visible

### B1. Keep tissue/artifacts central; make task execution readable

Likely files: `App.tsx`, `stage/RunCanvas.tsx`, `stage/runGraph.ts`, `TissuePanel.tsx`, `stage/Results.tsx`, `stage/LabView.tsx`.

Use a central tissue/figure surface, a compact mission/task view and an evidence inspector. A complete navigation rewrite is unnecessary if the existing stages can support this. Keep the full graph as an optional detailed view.

Each task should show purpose, actual state, reason for running where recorded, measured elapsed time and output. Selecting it opens the relevant finding/control/figure/source rather than only a node description. Distinguish model reasoning from deterministic tools: six jobs need not imply six different LLMs.

The evidence inspector exposes **Summary**, **Inputs and method**, **Checks**, **Sources** and **Reproduce**. Adapt existing panels rather than creating a second evidence model. Preserve source links, recorded challenges, review decisions and downloads.

Show **Different specimens** when moving between GSE286184 RNA and KPMP protein evidence. Preserve the dataset/participant label for the selected view. Registered overlay is appropriate only with a verified transform and specimen relationship; these two cohorts cannot be overlaid as matched measurements.

On narrow screens, use Tissue / Tasks / Evidence tabs or another readable stacked arrangement. Run mode must remain visible; current desktop-only visibility classes need attention. Respect reduced motion and avoid animations that obscure counts or delay reading.

**Done:** desktop and phone layouts remain usable; every task opens its actual output; tissue source and selected evidence agree; no image is silently paired with unrelated RNA coordinates; existing pan/zoom, channels, ROI audits and navigation still work.

### B2. Show what work was delegated

Display a concise completed-work summary derived from actual events: analysis, executed controls, verified claims, protein checks, literature records and generated figures. Show links to the outputs. Keep unexecuted or rejected work distinguishable.

Use **Recorded execution time**, **Lab execution time**, **Estimated model cost** and **Playback** with distinct meanings. Label human time savings as unmeasured until an actual comparison exists. Keep visual verification's known false positives visible when presenting benchmark performance.

**Done:** the audience can point to completed research work and the final artifact; all displayed figures are computed from served metadata; no invented “hours saved” or universal accuracy claim appears.

### B3. Update the presentation material

Update `README.md` and the existing demo script/location to match the final built UI. Use the three-minute storyboard in `docs/product/co-scientist-demo-plan.md`, adjusting to actual working paths. Name the domain in the opening, introduce gene symbols only after the problem is clear, and close on report/next experiment.

**Done:** a presenter can reproduce the walkthrough from a fresh page without hidden setup; the script distinguishes replay, fresh computation and roadmap; all demonstrated links/buttons work.

## Phase C — Connections, sponsored access and the user's own API keys

### C1. Introduce explicit access choices

Likely files: `App.tsx`, `web/src/api.ts`, `src/spatialscout/api/routes.py`, `contracts/`, `settings.py`, `gateway/gate.py`, `gateway/budget.py`, `gateway/providers.py`, `gateway/live.py` and the orchestrator. Read the active implementations before choosing the seam.

Add **Connections** with:

| Choice | Required behavior |
| --- | --- |
| Recorded demo | No model spend; clearly identified immutable playback. |
| Sponsored live trial | Server-controlled availability, limits, session/run spend and disable path. Provider keys stay server-side. |
| Your model connection | Real per-session credentials and routing, explicit charges to the user's provider account, disconnect and expiry. |

Trial copy when enabled: “This live trial uses our model credits and may be paused when the budget is reached.” Otherwise show actual unavailability and working alternatives. The live trial must not bypass the existing passcode/budget protection by exposing a shared secret in browser assets. Use an owner-controlled trial entitlement or session mechanism with enforced limits.

**Done:** each available choice works as labelled; unavailable choices explain what is needed; disconnecting/disabling live access leaves public replay and supported deterministic sample audits working.

### C2. Implement actual session-scoped BYOK

The current `LiveGate` owns a shared server-funded client. Introduce an explicit session/client boundary rather than mutating that shared object's keys.

Required behavior:

1. Create an expiring session-scoped connection and a clear disconnect operation. Authorize all private investigation routes and related artifacts, events, lab, review and package access against ownership. Keep public recordings a separate readable category. Random investigation IDs alone are not authorization.
2. Use TLS; explain that SpatialScout's backend receives the supplied key to contact the chosen provider. Keep raw credentials in isolated server memory initially, with no browser persistence. Exclude them from request/error logs, disk, events, audit logs, fixtures and exports. Use an opaque session capability for reconnection; SSE URLs must contain no raw provider credential.
3. Offer a tested **Meta-only** live profile: Wonder planning and Spark specialist/claim/visual roles, with supported optional SAM/voice. The existing claim route uses Spark Open through Baseten, so one Meta key cannot silently run that profile. An advanced profile can accept additional provider connections explicitly. Confirm model availability and update request/cache identity for the selected bindings.
4. Use independent budgets and call accounting per session/run, with atomic reservations for concurrent work. Retain server compute/storage limits. Enforce expiry and cancellation; disconnect stops future calls and cancels in-flight work where supported without implying a provider can always undo an already submitted request.
5. Keep private caches/artifacts scoped to their session and routing. Failover may use only a connection the user supplied for that profile. Never fall back silently to sponsored credentials or another user's account.
6. Memory-only connections expire on restart and require reconnection. Persist result provenance without credentials, using the stated result-retention behavior. A resumed private investigation must still be owned and authorized, even if its model connection expired.
7. Preserve today's deterministic/no-model uploaded-data audit. If adding model-enabled uploads, implement a separate explicit action and disclosure for the selected crops/summaries sent to providers.

**Done:** a researcher can connect their own supported credentials, launch a genuinely fresh question, inspect progress and evidence, disconnect, and observe further calls refused. Replay remains unchanged. A key field or a successful credential probe alone does not complete this feature.

### C3. Verify access and spending at the existing test seams

Use fake provider transports/recorded responses in automated tests. Cover:

- Session A cannot read, stream, review, run lab work or export session B's private investigation.
- Credentials are absent from state files, events, audit logs, recordings, exports and error output, including provider errors that echo secret text.
- Expiry/disconnect blocks subsequent calls; server restart does not resurrect memory-only keys.
- Concurrent calls cannot exceed the enforced session/run reservation budget.
- Replay and deterministic upload audits invoke no model provider.
- Meta-only routing invokes no undeclared Baseten/Fireworks connection.
- A failed provider connection does not fall back to server-funded credentials.

Regenerate TypeScript contracts when Pydantic contracts change. Update relevant domain/ADR documentation for new session and routing semantics using the repository's conventions.

## Phase D — Roadmap only in this pass

Retain the broader vision in a clearly marked roadmap: general multichannel OME-TIFF/OME-Zarr ingestion; coordinate-aware tiling/registration; richer gene/protein assays; injury/immune/fibrotic neighbourhood tools; donor-aware replication; an LN cohort; evaluated smaller/adapted specialists.

The current curated TIFF pipeline and Xenium table upload do not constitute general arbitrary-image ingestion. A larger model context does not replace a data pipeline. Future modules require actual compatible data and scientific evaluation before becoming executable UI actions.

## Validation and completion report

1. Run the repository's required build/type checks and appropriate seam tests for the changed behavior. Extend the existing public/local smoke workflow for changed entry points and the guided path.
2. Exercise a fresh Overview → guided recorded investigation → evidence → lab → report/package flow. Check supported custom-question handling, an off-panel question, sample upload audit and the original detailed investigation view.
3. Inspect desktop and mobile screenshots, including loading, missing-data, disputed/insufficient evidence and unavailable-connection states. Verify source labels and run mode in each view.
4. Check refresh/reconnect and long-running streams. For private runs, verify ownership and expired-connection behavior. Use mocked provider calls for security/budget tests; real user-funded or sponsored calls depend on actual authorization.
5. Summarize completed phases, checks run, screenshots, remaining blockers and exact live-versus-recorded capability. Report whether deployment occurred. Preserve reviewable diffs; follow the repository's secret-scan rule before any commit.

## Reference pointers

- Narrative, screenshot/layout interpretation and full demo script: `docs/product/co-scientist-demo-plan.md`.
- Google/Claude/AlphaGenome research and observed interface patterns: `docs/research/co-scientist-systems-and-demo-patterns-2026-11-04.md`.
- Researcher problems, kidney data boundaries and scientific sources: `docs/research/spatial-omics-delegation-opportunities-2026-11-04.md`.
- Recorded run identity and timings: `docs/golden-path.md` and `fixtures/recordings/gse286184-two-part-hypothesis/`.

## Prompt to give the implementation agent

> Implement the changes in `docs/spec/co-scientist-implementation-handoff.md` in `/Users/chandrarupdaka/Documents/Personal/Projects/Meta-Hackathon`. Read `CLAUDE.md`, inspect current work, and execute phases A–C in order with their acceptance checks. Preserve the scientific computations and recorded evidence; use the linked narrative for copy and presentation. Treat phase D as roadmap. Report completed phases, meaningful validation and any remaining work. This request is to implement and verify the changes; publication/deployment follows the authorization available in this session.
