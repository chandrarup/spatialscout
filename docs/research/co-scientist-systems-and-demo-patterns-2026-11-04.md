# Co-scientist systems, presentation and Meta fit

Checked 2026-11-04. Research and design recommendations for SpatialScout; not a comparison benchmark or an implementation status change. Related scientific research: `spatial-omics-delegation-opportunities-2026-11-04.md`.

## Findings that change our positioning

**The contribution can be a specialized research system built around existing models. It need not be a new foundation model.** Anthropic explicitly describes Claude Science as an application using existing Claude models, with scientific tools and compute around them. Calling SpatialScout a spatial-omics co-scientist is therefore reasonable if we demonstrate substantive scientific execution. Calling it Meta's official science product or a newly trained omics model would misrepresent our work. [Claude Science FAQ](https://claude.com/product/claude-science).

**Agent orchestration, literature, provenance and numerical review are already competitive requirements.** Our distinction must be the spatial workflow's depth and evidence, rather than claiming those capabilities are unique.

## What the primary sources establish

### Google Co-Scientist

The current public description organizes agents around generating, debating and evolving hypotheses. A supervisor assigns work; generation, proximity, reflection, ranking, evolution and meta-review play different roles. Pairwise tournaments help prioritize proposals. These are model evaluations of proposals, not experimental proof. The lesson for SpatialScout is to expose a research objective, alternatives considered, critiques and an actionable research overview. A spatial audit should use scientific controls rather than substitute an Elo score for quantitative evidence. [2026 DeepMind description](https://deepmind.google/blog/co-scientist-a-multi-agent-ai-partner-to-accelerate-research/), [primary paper](https://www.nature.com/articles/s41586-026-10644-y).

Google's Enterprise documentation says detailed access is restricted. This research pass inspected public descriptions and architecture, not a signed-in Co-Scientist workspace; it cannot establish the private UI's exact current behavior. [Enterprise documentation](https://docs.cloud.google.com/gemini/enterprise/docs/co-scientist).

### Claude Science

Claude Science already describes a coordinating agent, specialists, database connections, compute management and a reviewer. It preserves code and environment with outputs and supports natural-language figure iteration. Its own broad capabilities overlap much of our proposed harness; we should not claim Claude cannot run spatial analysis. The narrower case for SpatialScout is a prepared, bounded, inspectable workflow for a particular spatial research decision. [Launch description](https://www.anthropic.com/news/claude-science-ai-workbench), [current product overview](https://claude.com/resources/guides/claude-science-product-guide/claude-science-product-overview), [getting started](https://support.claude.com/en/articles/16563838-get-started-with-claude-science).

Direct UI observation: the official published screenshot has project/files navigation on the left, a large scientific figure in the center, and an artifact inspector on the right. The inspector exposes Code, Execution Log, Messages, Environment and Review, along with inputs and an artifact version. Figure annotations carry a request back to the agent. This is a useful reference for making evidence the working surface. [Official interface image, linked from the launch article](https://www-cdn.anthropic.com/images/4zrzovbb/website/1c78d0a671cbf1715b3f09a790e6d1a90466de1a-2048x1257.jpg).

The product site's interactive embeds rendered blank during this browser inspection. Observations above come from the visible public page, official screenshot and documentation, not an authenticated hands-on session.

### AlphaGenome and its agent walkthrough

AlphaGenome's page explains a difficult biological task, shows concrete use cases, and offers routes to inspect evidence or use its API. Its scientific model and atlas are different in kind from SpatialScout's orchestration layer. We can learn from its communication without suggesting equivalent scientific validation. [AlphaGenome](https://deepmind.google/science/alphagenome/).

The embedded 3-minute-20-second AlphaGenome Atlas/Antigravity walkthrough was inspected in-browser at several points. It moves from researchers describing the task, to the tool setup, a natural-language request, an annotated variant table, and handoff to evidence in Atlas. The useful pattern is **question → delegated work → concrete artifact → inspectable evidence**, with presenters explaining why the result matters. This was sampled inspection, not a transcription of every frame. [Walkthrough](https://www.youtube.com/watch?v=b2qw3rDNX0Q).

For SpatialScout, show a kidney image, a research mission, the controls and a completed evidence report. Do not open with a long list of gene symbols or model names. Show one selected region and one understandable decision before revealing implementation detail.

## Meta models: a justified composition

Meta's documentation supports different models for different jobs: Wonder for complex planning/orchestration, Spark for tighter specialist loops and multimodal interpretation, SAM 3.1 for segmentation geometry, Voice Transcribe for speech input, and open-weight options for adaptable deployment. This is a rationale for workload routing, not evidence of higher scientific accuracy than competitors. [Model catalogue](https://dev.meta.ai/docs/models).

| Component | Useful role in SpatialScout | Evidence or constraint |
| --- | --- | --- |
| Muse Wonder | Decompose a question; select tools, controls and specialist tasks | Already used for planning and lab dispatch in the recorded workflow. |
| Muse Spark 1.3 | Read tool results and fetched literature; inspect computed figures | Already used; a model's visual agreement is fallible. |
| Muse Spark Open | Draft claims with the same evidence contract | Already routed through Baseten with Fireworks failover. Open weights offer deployment/adaptation choices, not effortless laptop inference. |
| SAM 3.1 | Propose inspectable tissue outlines from supported crops and prompts | Existing RNA-rendered outlines are exploratory; not validated pathological anatomy. |
| Muse Voice Transcribe | Make requesting a task easier | Optional interaction, not the scientific differentiator. |
| Muse Glimmer | Potential smaller locally deployed specialist after evaluation | Roadmap, not a completed tuned spatial model. |
| Deterministic analysis tools | Quantify molecules/proteins; run controls; recompute citations | The quantitative foundation; not a language-model role. |

We should not add generated microscopy to scientific evidence. Image generation is unnecessary for this demo. Model roles should be visible in a details drawer when useful, while the main UI names the research task and result.

### Large images are a systems problem

Meta's vision documentation lists supported image MIME types without TIFF. It also sets image/request limits. A large context window is not a license to send an arbitrary multichannel whole-slide TIFF and assume correct quantitative interpretation. [Image understanding, formats and limits](https://dev.meta.ai/docs/image-understanding).

The desired harness reads OME-TIFF/OME-Zarr metadata, tiles at multiple resolutions, keeps channel identities and coordinate transforms, selects relevant crops and passes derived previews to vision models. Quantitative tools operate on original measurements. The present repo has a curated KPMP TIFF-to-tile pipeline; arbitrary TIFF uploads, general cross-assay registration and large-scale resumable ingestion are separate future capabilities. [OME-NGFF](https://ngff.openmicroscopy.org/latest/), [SpatialData](https://pmc.ncbi.nlm.nih.gov/articles/PMC11725494/).

## What would demonstrate an advantage

1. A researcher can delegate a defined question with the files and metadata the task needs.
2. The system selects and executes relevant checks; it visibly rejects unsupported steps.
3. Every reported result links to a dataset, spatial region, parameters and computed artifact.
4. Alternative explanations and missing evidence remain visible in the final report.
5. Another person can reproduce the result from the exported package.
6. A measured comparison shows less researcher effort at comparable correctness.

A simple prompt-only baseline establishes the benefit of tools, but is not a fair claim of superiority over Claude Science or Google Co-Scientist. A stronger evaluation would compare the same task, data, tool access, budget and required deliverables, with independent review. A separate same-Meta-model ablation can compare the full harness to a single agent with the same tools; count missing controls, unsupported claims, interventions, cost and completion time. Until those experiments exist, claim the completed workflow and recorded run measurements, not a performance lead.
