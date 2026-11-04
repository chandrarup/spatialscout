# SpatialScout

SpatialScout tests whether a kidney spatial-transcriptomics finding survives a change to how RNA molecules are assigned to cells. A researcher states a hypothesis, typed or spoken. Meta's models plan the analysis, decide which controls it needs, and draft claims. Deterministic code computes every number, and a verifier checks each claim before it reaches a verdict. Everything the product shows comes from a computed artifact ([ADR-0001](docs/adr/0001-computed-results-only.md)).

Built for the Meta Global AI Developer Hackathon (Nov 2026). **Research use only: not for clinical decisions.**

**Public URL:** https://chandrarupdaka--spatialscout.us-east.modal.run. It opens on two real KPMP CODEX biopsies side by side. It replays the recorded live investigations (immutable replay); the run-mode banner names each recording and when it was recorded.

## The golden path (what the recorded run did)

The question, recorded live on 2026-11-04 ([anchor](docs/golden-path.md)): *"My hypothesis: the podocytes this atlas calls 'endocytic' really carry LRP2, and the UMOD seen in B cells is spillover from neighbouring thick ascending limb cells. Does each part hold up under stricter assignment?"*

1. **Muse Wonder** split the question into two sub-claims with the researcher's predictions: podocyte LRP2 *holds*, B-cell UMOD *drops*. It planned two assignment audits over the 21 distinct GSE286184 sections.
2. **The engine** ran each audit under four assignment conditions: default, nucleus-only, and 1 µm and 2 µm distance caps. Both came back stable.
3. **Muse Spark 1.3** read each result and requested its controls, each request citing the observation behind it: a random-thinning control for each audit, and a label-sensitivity check for each population. Three further requests were rejected without running.
4. **Muse Spark Open** (Baseten, with Fireworks failover) drafted one claim per audit. One draft was redrafted after the citation gate rejected it.
5. **The verifier** checked each claim three ways: structurally, by an independent numerical recompute from the molecule tables, and with Muse Spark 1.3 reading the two-panel figure. Both claims were verified. An injected error (a changed number) failed the numerical check.
6. **The frozen verdict rule** compared each sub-claim's prediction with its verified claims:

| Sub-claim | Prediction | Computed evidence (pooled over 19 sections) | Verdict |
| --- | --- | --- | --- |
| Podocytes (NPHS1-anchored rule) carry LRP2 | holds | 26.2% of podocytes express LRP2 by default and 23.8% nucleus-only, against a random-thinning expectation of 24.4%; stable | **confirmed** |
| UMOD in B cells is spillover | drops | 17.0% by default and 12.3% nucleus-only, against an expectation of 9.5%; stable | **refuted** |

The second hypothesis is refuted. UMOD signal in B cells does not fall faster under stricter assignment than random molecule loss predicts, so this evidence does not point to spillover. Every verdict is scoped to these sections and controls, and says nothing about biological truth.

The run made 18 model calls costing an estimated $0.29, and took 179 s from plan to evidence package. Source: `fixtures/recordings/gse286184-two-part-hypothesis/`.

## Implemented

- **Dual-biopsy viewer** on real microscopy: KPMP CODEX healthy reference 164-17 and diseased participant 31-10013. It has channel toggles (DAPI, Podocalyxin, LRP2, UMOD, CD20, CD3, aSMA) and a protein audit of any drawn box. The same viewer opens GSE286184 sections as channels rendered from molecules. No GSE286184 data is ever drawn on a KPMP image.
- **Assignment audit** on GSE286184 Xenium molecules. Four primary conditions plus an exploratory SAM 3.1 condition; closed-form random-thinning expectations (cell-matched and home-matched); neighbour-proximity shares; evidence regions; and evidence labels by frozen rules with leave-one-section-out.
- **Protein-level audit** on KPMP. Whole-label, eroded-interior and nucleus-region measurements; a random-pixel-loss expectation; bordering-home-cell shares; thresholds frozen on the healthy reference.
- **Agent loop.** Plan, approval, then follow-ups chosen by the agent within a 12-call budget. Nothing runs a control on the agent's behalf.
- **Verification** (structural, numerical, visual), an error injector, a benchmark, and a "Challenge the verifier" selector on every claim card.
- **Hypothesis verdicts:** sub-claims, a frozen rule, and a banner.
- **Review and export.** Per-claim review decisions in a hash-linked audit log. The evidence package holds findings, figures, a replay manifest, rerun instructions, and a standard-library notebook that rechecks every cited number and the log's hash chain.
- **Voice questions** via Muse Voice Transcribe, with an editable transcript.
- **Descriptive disease contrasts**, with no p-values ([ADR-0007](docs/adr/0007-descriptive-disease-contrasts.md)).
- **Run modes:** immutable replay, cached tool rerun, and live. Live runs are gated by a passcode and a file-locked daily budget.

## Measured results

| What | Result | Source |
| --- | --- | --- |
| GSE286184 ingested | 22 GEO sections (21 distinct), 23,940,259 molecules, 792,072 cells, 50-gene panel | `artifacts/modal_batch_gse286184.json`, `artifacts/GSE286184/manifest.json` |
| Batch audit on Modal | 22 sections with `.map()` in 13.7 s wall time, estimated $0.0009 | `artifacts/modal_batch_gse286184.json` |
| Audit results | 21 computed; all 21 stable | `artifacts/GSE286184/audit/index.json` |
| Disease contrasts | 84 descriptive: 67 stable, 17 insufficient evidence | `artifacts/GSE286184/contrasts/index.json` |
| Verifier benchmark | 21 valid and 147 injected claims; 147 of 147 injected errors detected (49 of 49 held out); 7 of 21 valid claims wrongly disputed, all co-expression claims, by the visual check | `artifacts/GSE286184/benchmark/results.json` |
| KPMP protein audit (whole image) | 164-17: LRP2 in Podocalyxin+ cells insufficient evidence, UMOD in CD20+ cells stable. 31-10013: both stable | `artifacts/KPMP/*/audit_*.json` |

## Meta models and partners

| Model or platform | Role |
| --- | --- |
| Muse Wonder 1.0 | Planner: tool steps and sub-claims with predictions |
| Muse Spark 1.3 | Agent follow-ups (chooses controls) and the visual check of composite figures |
| Muse Spark Open on Baseten, Fireworks failover | Claim drafting |
| SAM 3.1 | Glomerulus outlines from box prompts, an exploratory condition only ([ADR-0006](docs/adr/0006-sam-condition-is-exploratory.md)) |
| Muse Voice Transcribe | Spoken questions |
| Modal | Public deployment (one warm container, a Volume for investigations) and the per-section batch |

## Run it locally

```bash
make install    # uv and npm, from the lockfiles
make data       # download and validate GSE286184 (needs network)
make kpmp       # KPMP CODEX artifacts, from raw downloads in data/kpmp/
make serve      # http://127.0.0.1:8000
make test       # seam-1 engine tests and seam-2 API tests, network blocked
make benchmark  # replays the verifier benchmark offline
```

Live runs need provider keys in `.env`, `SPATIALSCOUT_LIVE_PASSCODE` and `SPATIALSCOUT_DAILY_BUDGET_USD`. See `CLAUDE.md` for every command and setting.

## Limitations

- **Donors.** GEO lists 22 samples, and the paper reports 19 donors. GEO doesn't say which sections share a donor, so sections are not independent donors and the contrasts are descriptive only.
- **Panel size.** The 50-gene Xenium panel limits the label rules. Cell type labels are SpatialScout's own marker-rule labels, not the authors' annotation, which was not deposited.
- **Single-section and region results** are insufficient evidence for cohort-level claims. A KPMP participant compared with another is one person against one person.
- **KPMP masks are nucleus-sized:** the labels cover 4.6–7% of each image, with a median of 34–38 µm². "Whole cell" means the whole mask label. The two participants were imaged in different runs, so thresholds frozen on one are not calibrated for the other. Otsu's rule calls 24% of 164-17's cells CD20+, which suggests the CD20 threshold captures background.
- **SAM 3.1 outlines** are exploratory and never enter an evidence label.
- **The visual check** wrongly disputes a third of valid co-expression claims in the benchmark.
- **No clinical metadata** is shown: the KPMP clinical export was not downloaded.

The root PRD (`spatialscout_prd_srs_spec.md`), the two whitepaper `.docx` files and `docs/product/` are pre-build planning drafts with placeholders, superseded by `docs/spec/` and this README.

## Roadmap (not built)

- More participants, and a KPMP clinical-metadata view sourced from KPMP's own files.
- A Muse Glimmer LoRA annotator and its agreement study (ticket 14).
- Other tissues and assays, for example tonsil and brain atlases.
- A researcher feedback session (ticket 13). No lab-validation results are reported here.

## Credits

- **GSE286184:** Xenium in situ profiling of human glomerular disease, [NCBI GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE286184); paper [PMC13586693](https://pmc.ncbi.nlm.nih.gov/articles/PMC13586693/).
- **KPMP:** Kidney Precision Medicine Project, [Kidney Tissue Atlas](https://atlas.kpmp.org/repository/), open-access CODEX image collections and segmentation for participants 164-17 and 31-10013. Segmentation data DOI [10.48698/swzg-8j41](https://doi.org/10.48698/swzg-8j41). The Kidney Precision Medicine Project (KPMP) is supported by grant U24 DK114886 from the National Institute of Diabetes and Digestive and Kidney Diseases (NIDDK). Please follow KPMP's citation guideline when presenting or publishing KPMP data.
- **Method:** Mitchel et al. (2026) on how segmentation errors distort spatial differential expression motivated the assignment conditions.
