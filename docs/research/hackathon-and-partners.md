# Meta Global AI Developer Hackathon: rules and partner platforms (verified 2026-11-02)

All sources below were fetched on 2026-11-02 and are primary (Cerebral Valley, Meta, Baseten, Fireworks, Modal, PyPI, NIST). Every claim links to its source. Bracketed labels such as [cv-rules] point to the full URLs in **Sources** at the end. **UNVERIFIED** marks anything the public primary sources do not establish. Third-party pages appear only where the task asked for them to be checked.

## Corrections to `spatialscout_prd_srs_spec.md`

| Spec claim | What the primary sources say |
|---|---|
| Fireworks gives **$25** in credits; Meta plus the three partners total **$375** | **Wrong.** The official event page says "Fireworks is offering **$100** in credits to select participants" [cv-event] [cv-event-md]. The page data shows the event record was last updated 2026-10-30 [cv-event]. The $25 figure comes from an Oct 17–18 third-party snapshot [reconscribe]. The maximum is $150 Meta + $100 Baseten + $100 Modal + $100 Fireworks = **$450**, but partner credits go only "to select participants" [cv-event]. |
| Judging weights: Impact 30%, Use of Meta AI tooling 25%, Demo 25%, Technical depth 20%, cited to reconscribe.com | **The weights are official.** They appear verbatim in the Official Rules on the Cerebral Valley waiver page [cv-rules]. Cite that page, not reconscribe. |
| "Muse Spark Open at 2M TPM on Baseten" | **The model is real**, and Baseten hosts it as `meta-models/muse-spark-open` [bt-modelapis]. **2M TPM is not a model property.** It is a hackathon grant "to select participants" [cv-event]. Baseten's account defaults are 100K–1M TPM and 15–120 RPM [bt-limits]. |
| "LoRA-tuned Muse Glimmer on Fireworks" served as an endpoint on $25 | **The model is real** (`accounts/fireworks/models/muse-glimmer-30b`), and LoRA SFT is supported and **free until Nov 30** [fw-glimmer] [fw-ft-models]. **Glimmer has no serverless inference on Fireworks**, and a trained LoRA can be served **only on an on-demand dedicated deployment** (H100 at $8.00/hr) [fw-glimmer] [fw-deploy-lora] [fw-pricing]. See section 6. |
| "Showcases 7 Meta models ... with zero non-Meta models" | **No rule requires exclusivity.** The rules say participants "build with Meta AI products, including Muse Spark, Glimmer, SAM 3, and any other Meta AI products identified on the Event page" [cv-rules]. Excluding non-Meta models is the spec's own choice. |
| "2-Minute Demo Video" | **UNVERIFIED.** No primary source states a video length. The rules only say the Demo score includes "the quality of the demo video" [cv-rules]. |
| Strict JSON-schema worker swarm on Baseten Muse Spark Open | **Risk.** On Baseten, Muse Spark Open is the only Model API model **without** structured outputs or JSON mode [bt-modelapis]. |
| "Deterministic replay" | On Baseten, "Neither `seed` nor `temperature: 0` guarantees reproducible output" for Muse Spark Open [bt-modelapis]. Caching responses, as the spec already does, is the right approach. |
| Judges clicking the public URL between Nov 4 and Nov 8 | The judging window of Nov 4–8 is official [cv-event]. Live testing is **implied** by "whether the product holds up live" but is not stated explicitly [cv-rules]. |
| Whitepaper PDF in repo root | **No whitepaper or write-up requirement** appears in the public rules [cv-rules]. |

---

## Part 1: Hackathon rules

### 1. Deadline, timezone, tracks, prizes, themes

- **Submission deadline:** "Nov 4: Project submissions due by 9:00 PM ET" [cv-event] [meta-event]. The page header reads "Oct 26, 12:00 PM – Nov 4, 9:00 PM (EST)" [cv-event].
  - US daylight saving time ends 2026-11-01 [nist-dst], so the deadline falls under EST (UTC−5): **2026-11-05 02:00 UTC**.
  - The page data stores `"hackathonSubmissionDueDate":"2026-11-05 02:00:00"` [cv-event], and the markdown version says "submissions due Nov 5, 2026 UTC" [cv-event-md].
- **Late submissions:** the page data also contains `"submissionDueDateGracePeriodHours":6` [cv-event]. The platform UI says "This project will be marked late. Hosts may consider that during judging." and "Changing the repository after the deadline will mark this project late." [cv-js]. **No rule mentions a grace period** [cv-rules]. Do not rely on it.
- **Event start:** "Oct 26: Hackathon begins with kickoff livestream". Workshops and Discord office hours run Oct 27 – Nov 4 [cv-event].
- **Judging and results:**
  - "Nov 4 – Nov 8: Judging" and "Nov 9: Closing ceremony - live finals and winners announced" [cv-event].
  - Bonus prizes will be "announced on or about November 10, 2026" [cv-rules].
  - Dates "may be subject to change at Meta's sole discretion" [cv-event].
- **Tracks:** "Every project enters one track" [cv-event]. A participant may apply for one track only, and a project may be entered in one track only [cv-rules].
  - **Indie developer track:** "For individual builders and students. Judged on creativity, technical ambition, and whether it works." [cv-event] [meta-event]
    - The rules add: "Open to individual builders and students, teams of up to four (4)".
    - The team's Representative submits and "shall identify all other team members in the project submission" [cv-rules].
  - **Startup track:** "For teams and founders building a real product. Judged on technical execution and whether it holds up in production." [cv-event]
- **Prizes** [cv-rules]:

  | | Indie Developer Track (total $400,000) | Startup Track (total $550,000) |
  |---|---|---|
  | 1st | $150,000 | $250,000 |
  | 2nd | $100,000 | $150,000 |
  | 3rd | $75,000 | $75,000 |
  | 4th | $50,000 | $50,000 |
  | 5th | $25,000 | $25,000 |

  - Bonus prizes are capped at $50,000 in aggregate (for example community vote or most viral), and the total pool is $1,000,000 [cv-rules].
  - Prizes are paid after eligibility verification. Winners must sign the waiver and Official Rules and provide a W-9 or W-8BEN [cv-rules].
- **Themes** apply whichever track you choose [cv-event]:
  - **Build for Your World:** "Bring Meta's models into your domain. Solve a problem you know firsthand..."
  - **Push the Frontier:** "...accelerate a scientific experiment, or unlock a better way to understand and control a physical system."

### 2. Judging criteria: exact wording, and the weights are official

These appear in the Official Rules ("Hackathon Terms & Conditions ('Official Rules') and Event Waiver"), which the event page embeds and which are published at [cv-rules]:

> "Hackathon Judging Criteria. These criteria apply only to projects submitted during the Hackathon, not to applications. ... Hackathon Project submissions will be evaluated based on the following criteria: **Impact (30%)** — the real-world potential of the Project, who benefits, how much it matters, whether it could become something people use, and whether it fits one of the problem statements; **Use of Meta AI Tooling (25%)** — how creatively the team used Meta's AI tooling, whether they went beyond a basic integration, and whether they surfaced unexpected capabilities; **Technical Depth & Execution (20%)** — whether the engineering is sound and thoughtfully refined and the Project demonstrates real craft; and **Demo (25%)** — whether the Project has a working, impressive demo, whether the product holds up live, and the quality of the demo video." [cv-rules]

- **Verdict on the weights:** the official page **confirms** 30/25/20/25. The third-party page [reconscribe] lists the same four weights and says they come "from the waiver". It is secondary and should not be the citation.
- **The track descriptions are separate and unweighted.** The Indie line "creativity, technical ambition, and whether it works" sits on the event page with no weights [cv-event]. The weighted rubric above is in the rules [cv-rules].
- **"Problem statements"** (in the Impact criterion) is not defined anywhere in the public pages. The only candidates published are the two themes [cv-event]. Treat that mapping as **UNVERIFIED**.
- **Who judges:** "Finalists will be chosen by a panel of Organizers selected judges ('Judges'). The judges' selections are final and binding." [cv-rules]

### 3. Submission requirements

- **Where to submit:** "Participants will submit their project to Cerebral Valley's portal at https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit" [cv-rules].
  - The portal redirects anonymous visitors to `/auth/login` [cv-submit].
  - The hackathon-details API returns `403 {"detail":"Unauthorized"}` without a login [cv-api].
  - So **this event's required fields are UNVERIFIED** (not logged in, by design).
- **Platform-generic form fields:** the Cerebral Valley site JavaScript labels "Team Name", "Team Members", "GitHub Repository", "Live Project", "Demo Video", "Hugging Face Repository" and "Project Description" [cv-js].
  - It also supports per-event "custom submission fields" [cv-js].
  - These are platform labels, **not confirmed requirements** for this event.

| Question | Answer |
|---|---|
| Demo video required? Maximum length? | A demo video is implied, because the Demo criterion scores "the quality of the demo video" [cv-rules]. **Maximum length: UNVERIFIED** (not published). |
| Public GitHub repo required? | **UNVERIFIED.** "GitHub Repository" is a generic platform field [cv-js]. No rule requires a public repo [cv-rules]. |
| Live URL required? | **UNVERIFIED.** "Live Project" is a generic field [cv-js]. The Demo criterion rewards a product that "holds up live" [cv-rules]. |
| Write-up or whitepaper? | Not required by any public rule [cv-rules]. "Project Description" is a generic field [cv-js]. |
| Required use of Meta models? | Expected but not exclusive: "Participants build with Meta AI products, including Muse Spark, Glimmer, SAM 3, and any other Meta AI products identified on the Event page" [cv-rules]. The page names "the Muse Spark series, Muse Wonder, Muse Image and SAM 3.1 through Meta Model API, ... Meta open weights models, and ... Muse Code" [cv-event]. Meta tooling carries 25% of the score [cv-rules]. |
| Team size | Indie: individuals and students, teams of **up to 4**. Startup: technical founders, with a Representative who must be an active employee of the startup [cv-rules]. |
| Work started before the event | **No explicit restriction found.** The rules require the Submission to be the team's "original work product" and "solely owned". Contracting third-party technical help is allowed if the components "remain the Participant's own work". Open source is allowed if licenses are followed and the Submission "enhances or builds upon" it [cv-rules]. The build window is Oct 26 – Nov 4 [cv-event]. |
| Judging period; do judges try live URLs? | Judging runs Nov 4–8, with live finals on Nov 9 [cv-event]. Live testing is implied by "holds up live" [cv-rules] but **not explicitly stated**. |
| Eligibility | Age 18+ and the age of majority; listed sanctioned or excluded countries; no Meta or Cerebral Valley staff or their families [cv-rules]. |
| Rights | Entrants keep IP but grant the Organizers a perpetual, royalty-free license. Nothing shared is treated as confidential [cv-rules]. |

### 4. Credits: how each is obtained and redeemed

| Credit | What the official sources say | How to get or redeem it |
|---|---|---|
| Meta Model API **$150** | "Participants selected to participate in the Hackathon will receive $150 in Meta Model API credits, **valid for a 10-day development window**. Before claiming your credits, carefully review the Credit Terms." [cv-rules] | **UNVERIFIED.** The Credit Terms link is a signed fbcdn PDF URL that expired 2026-10-28 and returned 403 on fetch [cv-rules]. No claim procedure appears in Meta's docs [meta-pricing]. If the 10 days started around Oct 26, the credits may **lapse before or during judging (Nov 4–8)**, so plan for the live URL running on cached responses or a paid key. |
| Baseten **$100 + 2M TPM** | "offering $100 in credits and 2M TPM rate limits to select participants to use Meta's open-weights models" [cv-event] | Hackathon procedure: **UNVERIFIED** (look for the acceptance email or Discord). Generic Baseten behavior: workspace credits apply automatically, "you do not need to redeem them" [bt-billing]. Check your actual limit with `GET https://api.baseten.co/v1/model_apis/meta-models%2Fmuse-spark-open` or the `x-ratelimit-*` response headers [bt-limits]. |
| Modal **$100** | "offering $100 in credits to select participants to use Meta's open-weights models through Endpoints in addition to their serverless GPUs, sandboxes, and tools for LLM training" [cv-event] | Hackathon procedure: **UNVERIFIED**. Caveats: Modal requires a payment method on file [modal-billing]; "Using a GPU requires having a valid payment method on file" [modal-gpu]; and "Credits included with your plan cannot be used for Shared Endpoint usage" [modal-shared]. Whether the hackathon credit covers Shared Endpoint usage is **UNVERIFIED**. |
| Fireworks **$100** | "offering $100 in credits to select participants to use Meta's open-weight models along with a workshop from Sinan Ozdemir" [cv-event] | Hackathon procedure: **UNVERIFIED**. The generic mechanism is credit codes, redeemed with `firectl credit-redemption redeem <CODE>` [fw-credit-redeem]. Separately, Muse Glimmer 30B LoRA SFT is free until Nov 30 with no credit card required [fw-ft-models]. |

---

## Part 2: Partner platforms

### Background: the two Meta open-weight models exist

Both "Muse Spark Open" and "Muse Glimmer" are real Meta models. dev.meta.ai lists both [meta-event], and the Official Rules name "Glimmer" [cv-rules].

| | Muse Spark Open | Muse Glimmer |
|---|---|---|
| Size and architecture | 816B total / 42B active sparse MoE. Inputs: text, image, audio, video. Output: text [meta-spark-open-doc] | 30B dense multimodal (text and image in, text out), "distilled from Muse Spark" [meta-glimmer-doc] |
| Context | 1,048,576 tokens [meta-spark-open-doc] | 128K by default [meta-glimmer-doc] |
| License | Muse Model License [meta-spark-open-doc] | Apache 2.0 [meta-glimmer-doc] |
| Inference partners Meta names | "Baseten, Fireworks AI, Groq, Modal, Nebius, and Together AI" [meta-spark-open-doc]. The "Where to deploy" section links baseten.co, fireworks.ai and modal.com pages for it [meta-spark-open-page] | Meta's model page lists Fireworks "deployments" [meta-glimmer-page]. Meta's deploy doc lists only Together AI as a hosted provider (`meta-models/Muse-Glimmer-30B`; Together is not a hackathon partner) [meta-glimmer-deploy] |

### 5. Baseten

- **Meta models on Model APIs (serverless, per token):** only **Muse Spark Open**, slug `meta-models/muse-spark-open`, with a 1,048K context and 1,048K maximum output. This comes from the docs' supported-models table [bt-modelapis]. No Muse Glimmer or Llama models are on Model APIs [bt-modelapis].
  - Baseten's model library lists only `muse-spark-open` among Meta models [bt-library].
  - Llama 3.1, 3.2, 3.3 and 4 appear only as dedicated-deployment "model recipes" [bt-llms].
- **"Muse Spark Open":** real, and "available day 0 on Baseten Model APIs and Dedicated Inference ... served in NVFP4" [bt-blog]. "2M TPM" is the hackathon grant [cv-event], not a documented model limit.
- **OpenAI-compatible:** yes. Supported formats are OpenAI Chat Completions, OpenAI Responses, and Anthropic Messages (beta) [bt-modelapis].
  - **Base URL:** `https://inference.baseten.co/v1` [bt-modelapis] [bt-lib].
  - **Auth:** `Authorization: Bearer $BASETEN_API_KEY` [bt-limits]. Create the key in the Baseten app under Settings → API Keys [meta-spark-open-deploy].
  - Example from Baseten's own page [bt-lib]:

    ```python
    from openai import OpenAI
    client = OpenAI(base_url="https://inference.baseten.co/v1", api_key=os.environ["BASETEN_API_KEY"])
    client.chat.completions.create(model="meta-models/muse-spark-open", messages=[...])
    ```

- **Muse Spark Open caveats on Baseten** [bt-modelapis]:
  - Tool calling is supported.
  - **No structured outputs or JSON mode.** "All except Muse Spark Open support structured outputs and JSON mode".
  - `logprobs` is ignored.
  - `n>1` returns HTTP 400.
  - Output is not reproducible, even with `seed` or `temperature: 0`.
  - Audio input is supported.
- **Pricing:** **$1.25 input / $0.15 cached input / $4.25 output per 1M tokens** [bt-lib] [bt-pricing].
- **Rate limits** [bt-limits]:
  - Default tiers: Basic unverified 15 RPM / 100K TPM; Basic verified 120 RPM / 500K TPM; Pro 120 RPM / 1M TPM.
  - Cached and uncached input both count toward TPM. Overloads return 429 or 529.
  - At 15–120 RPM, **request count, not TPM, is the likely ceiling for a parallel worker swarm** unless the hackathon grant raises it.

### 6. Fireworks AI

- **Meta models on serverless (per token):** only **Muse Spark Open** (`accounts/fireworks/models/muse-spark-open`).
  - The model-library data marks Muse Spark Open `"serverless":true`, and every other Meta-provider model (Muse Glimmer 30B, Muse Spark Open NVFP4, all Llama 2/3/3.1/3.2/3.3/4 and Llama Guard) `"serverless":false`, meaning on-demand only [fw-models-lib].
  - Muse Spark Open runs on US-only capacity at **$1.25 / $0.15 / $4.25 per 1M** (Standard) and $1.875 / $0.225 / $6.375 (Priority) [fw-serverless-pricing] [fw-spark].
- **"Muse Glimmer":** real, model path `accounts/fireworks/models/muse-glimmer-30b` (29.7B, 131K context, image input, function calling) [fw-glimmer].
  - It shows **Serverless: Not Supported**. FAQ: deprecated "Only on serverless, starting on September 25, 2026. On-demand deployment will continue to be available." [fw-glimmer]
  - To call base Glimmer you therefore need an on-demand deployment.
- **OpenAI-compatible:** yes. "Fireworks provides an OpenAI compatible endpoint" [fw-quickstart].
  - **Base URL:** `https://api.fireworks.ai/inference/v1` [fw-quickstart].
  - **Auth:** `Authorization: Bearer $FIREWORKS_API_KEY` [fw-quickstart].

#### LoRA fine-tuning: supported, cheap to train, expensive to serve

- **Muse Glimmer 30B: LoRA SFT is supported and currently free.**
  - "Muse Glimmer 30B SFT is free to train until November 30, 2026. No credit card required." [fw-ft-models]
  - The free offer covers the UI and the Serverless Training API. RL, DPO, full-parameter training, **deployments, and inference outside the training run are not covered** [fw-glimmer-cookbook].
  - Even inside a free run, "In-session evaluation sampling is priced separately at the published per-token rates". The default serverless run samples 80 answers [fw-glimmer-cookbook].
  - Settings: base `accounts/fireworks/models/muse-glimmer-30b`, tokenizer `meta-models/Muse-Glimmer-30B`, default LoRA rank 8 [fw-glimmer-cookbook].
  - Data format: chat JSONL with `{"messages":[...]}` [fw-glimmer-cookbook].
- **Duration of a ~300-example job:** "A typical run finishes in a few minutes once it starts. In one example run, eval loss fell from 0.58 to 0.03 over 17 steps."
  - The job may first wait "for a training slot" [fw-glimmer-cookbook].
  - The preloaded example datasets have 600 and 300 rows, and "A few hundred clean rows are enough for a first signal." [fw-glimmer-cookbook]
  - Queue wait at submission time is **UNVERIFIED**.
- **Price after the free period:**
  - Managed LoRA SFT costs **$3.00 per 1M training tokens** for 16.1B–80B models [fw-pricing].
  - Serverless Training API rates for Glimmer: prefill $1.96, cached prefill $0.39, sample $4.88, train $5.86 per 1M [fw-pricing] [fw-serverless-training].
  - Rough estimate (my arithmetic, assuming about 1K tokens per example): 300 examples × 1 epoch × $3/M ≈ $0.90.
- **Serving the tuned LoRA is the cost problem:**
  - "Trained LoRA models ... can **only** be deployed to **on-demand (dedicated) deployments**. Serverless deployment is not supported for LoRA models." [fw-deploy-lora]
  - On-demand pricing: H100 80GB **$8.00/hr**, H200 $8.00/hr, B200 $13/hr, B300 $15/hr, billed per GPU-second [fw-pricing].
  - Example: one H100 kept up from Nov 4 to Nov 8 (~96 h) ≈ **$768**. That is my arithmetic, and the GPU count Fireworks picks for Glimmer is **UNVERIFIED**.
  - Scale-to-zero exists (`--min-replica-count 0`, minimum idle window 5 minutes). However, requests to a scaled-down deployment get **503 `DEPLOYMENT_SCALING_UP`, are not queued**, and wait "a few minutes" for a cold start [fw-autoscaling].
- **Possible per-token workaround (verify before relying on it):**
  - The Serverless Training API can sample saved sampler checkpoints per token, "including checkpoints from a run that has already ended" (SDK ≥ 1.2.29). It uses the completions API with a tokenizer, not chat completions [fw-serverless-training].
  - Meta's doc conflicts with this: "Promote before the session is deleted. After that, the checkpoints are no longer reachable through this API." [meta-spark-open-post]
  - **UNVERIFIED** which statement holds.
- **Muse Spark Open LoRA:**
  - Available only through the Serverless Training API on base `accounts/fireworks/models/muse-spark-open-nvfp4`. "Managed fine-tuning in the Fireworks UI isn't available for this model yet. Fine-tuned models deploy on-demand." [fw-spark]
  - Rates: prefill $6.19, sample $15.48, train $18.58 per 1M [fw-pricing].
  - The account may need Fireworks to enable it [meta-spark-open-post].
  - Serving an 816B model on dedicated GPUs (NVFP4 "serves on a single 4-GPU NVIDIA Blackwell node" [meta-spark-open-doc]) does not fit a $100 budget.
- **Bottom line for the spec:**
  - A Glimmer LoRA on Fireworks is feasible to **train** (free, minutes).
  - Keeping it **live for judges** needs a paid on-demand deployment, plus retry handling for scale-to-zero, or the unverified sampler path.

### 7. Modal

- **Package version:** `modal` **1.6.3** is the latest release on PyPI, uploaded 2026-10-27 and requiring Python ≥3.10,<3.16. Pre-release 1.6.4.dev5 was uploaded 2026-11-02 [pypi-modal].
- **(a) Public FastAPI web endpoint**
  - Use `@modal.fastapi_endpoint(method="POST")` on an `@app.function`. The image needs `fastapi[standard]` [modal-web].
  - For a full FastAPI app with multiple routes, use `@modal.asgi_app()` returning the `FastAPI()` instance, optionally with `@modal.concurrent(max_inputs=100)` [modal-web] [modal-fastapi-ref].
  - `@modal.web_endpoint` was renamed to `fastapi_endpoint` in v0.73.82 [modal-fastapi-ref].
  - Signatures [modal-fastapi-ref] [modal-asgi-ref]:
    - `fastapi_endpoint(*, method="GET", label=None, custom_domains=None, docs=False, requires_proxy_auth=False)`
    - `asgi_app(*, label=None, custom_domains=None, requires_proxy_auth=False)`
  - `modal serve app.py` runs an ephemeral, live-reloading app on a public URL. `modal deploy app.py` creates a persistent one [modal-web].
  - URLs take the form `https://<source>--<label>.modal.run`, and `modal serve` URLs get a `-dev` suffix [modal-webhook-urls].
  - Web Functions are **public by default**. Set `requires_proxy_auth=True` to require `Modal-Key` / `Modal-Secret` headers [modal-proxy-auth].
  - `fastapi_endpoint` enables CORS automatically [modal-fastapi-ref].
  - **HTTP limit is 150 s for all web function types.** Longer requests return a 303 redirect to a result URL, and this "does not work with requests that require CORS" [modal-timeouts].
  - SSE works through FastAPI `StreamingResponse(media_type="text/event-stream")` [modal-streaming]. How the 150 s limit applies to long-lived SSE streams is **UNVERIFIED**.
- **(b) GPU functions**
  - Use `@app.function(gpu="A100")`. Accepted values are `T4`, `L4`, `A10`, `L40S`, `A100`, `A100-40GB`, `A100-80GB`, `RTX-PRO-6000`, `H100` / `H100!`, `H200`, `B200` / `B200+`, `B300`. Append `:n` for multiple GPUs, for example `"H100:8"` [modal-gpu].
  - A GPU requires a payment method on file [modal-gpu].
  - Per-second prices [modal-pricing]:

    | GPU | Price |
    |---|---|
    | H100 SXM5 | $0.001097/s (≈ $3.95/hr) |
    | A100 80GB | $0.000694/s (≈ $2.50/hr) |
    | A100 40GB | $0.000583/s |
    | L40S | $0.000542/s |
    | H200 | $0.001261/s |
    | B200 | $0.001736/s |
    | B300 | $0.001972/s |

  - The Starter plan includes $30/month in free credits [modal-pricing].
- **(c) Fan-out**
  - `for r in fn.map(inputs): ...` runs inputs in parallel, and results "are returned as an iterable with the results ordered in the same way as the inputs" [modal-scale].
  - `return_exceptions=True` collects errors instead of raising. `fn.starmap([(a, b), ...])` handles multiple arguments [modal-scale].
  - Hard limit: 4,000 concurrent containers per Function. Other limits depend on plan [modal-scale].
- **(d) CLI authentication**
  - `pip install modal`, then `modal setup` (or `python -m modal setup`) [modal-guide].
  - `modal token new` "Create[s] a new token by using an authenticated web session" and accepts `--expires-in` [modal-token].
  - `modal token set --token-id ... --token-secret ...` sets credentials non-interactively [modal-token].
- **Meta models on Modal Endpoints** (the "Endpoints" product the hackathon page links [cv-event]):
  - **Muse Spark Open is on a Shared Endpoint (per token):**
    - Create it with `modal endpoint create --shared --model meta-models/Muse-Spark-Open-816B-A42B`.
    - Pricing: $1.25 prompt / $0.15 cached / $4.25 completion per MTok. The endpoint is OpenAI-compatible [modal-lib-spark] [modal-supported].
    - Auth: create a proxy token with `modal workspace proxy-tokens create` and send `Authorization: Bearer <token_id>.<token_secret>` [modal-endpoints].
    - Concurrency limits are per model; requests over the limit get 429 [modal-shared].
  - **Muse Glimmer 30B (BF16 or NVFP4) is on Dedicated Endpoints:**
    - Billed for compute, and "An Endpoint scaled to zero does not incur compute charges" [modal-supported] [modal-dedicated].
    - Dedicated Endpoints also accept "compatible custom weights" from a Hugging Face repo or Modal Volume [modal-dedicated]. Whether a Fireworks-trained Glimmer LoRA can be exported and served this way is **UNVERIFIED**.

---

## Open items (UNVERIFIED)

- Event-specific required submission fields, demo video length limit, and repo visibility. The portal is login-gated [cv-submit] [cv-api].
- The Meta $150 Credit Terms and claim steps. The PDF link had expired [cv-rules].
- The partner credit redemption steps for Baseten, Modal and Fireworks. They are not published publicly; check the acceptance email or Discord.
- Whether Modal hackathon credits apply to Shared Endpoint usage [modal-shared].
- Fireworks GPU shape and count for a Glimmer LoRA deployment, and the queue wait for a training slot.
- Whether Fireworks serverless-training sampler checkpoints stay reachable after the session ends. Fireworks [fw-serverless-training] and Meta [meta-spark-open-post] disagree.
- Whether judges will exercise live URLs. Only implied [cv-rules].

## Sources

- [cv-event]: https://cerebralvalley.ai/e/meta-ai-developer-hackathon (server-rendered HTML and embedded page data, including the Official Rules text)
- [cv-event-md]: https://cerebralvalley.ai/e/meta-ai-developer-hackathon.md
- [cv-rules]: https://cerebralvalley.ai/e/meta-ai-developer-hackathon/waiver (Hackathon Terms & Conditions, "Official Rules", and Event Waiver)
- [cv-submit]: https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit (redirects to https://cerebralvalley.ai/auth/login when logged out)
- [cv-api]: https://api.cerebralvalley.ai/v1/event/78e32764-9651-4942-b1eb-4401af6a3209/hackathon (403 Unauthorized when logged out)
- [cv-js]: https://cerebralvalley.ai/_next/static/chunks/42b01vvcicuhg.js (Cerebral Valley web client UI strings, deployment of 2026-11-02)
- [meta-event]: https://dev.meta.ai/events/global-hackathon
- [meta-spark-open-page]: https://dev.meta.ai/models/muse-spark-open/
- [meta-glimmer-page]: https://dev.meta.ai/models/muse-glimmer/
- [meta-spark-open-doc]: https://dev.meta.ai/docs/muse-spark-open
- [meta-spark-open-deploy]: https://dev.meta.ai/docs/muse-spark-open/deploy
- [meta-spark-open-post]: https://dev.meta.ai/docs/muse-spark-open/post-training
- [meta-glimmer-doc]: https://dev.meta.ai/docs/muse-glimmer
- [meta-glimmer-deploy]: https://dev.meta.ai/docs/muse-glimmer/deploy
- [meta-pricing]: https://dev.meta.ai/docs/pricing-rate-limits
- [nist-dst]: https://www.nist.gov/pml/time-and-frequency-division/popular-links/daylight-saving-time-dst ("During 2026, daylight saving time is in effect from March 8 ... to November 1")
- [reconscribe]: https://reconscribe.com/meta-global-ai-developer-hackathon-2026/ (third party, published 2026-10-17, updated 2026-10-18; checked only for comparison)
- [bt-modelapis]: https://docs.baseten.co/inference/model-apis/overview
- [bt-limits]: https://docs.baseten.co/inference/model-apis/pricing-and-limits
- [bt-lib]: https://www.baseten.co/library/muse-spark-open/
- [bt-library]: https://www.baseten.co/library/
- [bt-blog]: https://www.baseten.co/blog/muse-spark-open-launch/
- [bt-pricing]: https://www.baseten.co/pricing/
- [bt-billing]: https://docs.baseten.co/organization/billing
- [bt-llms]: https://docs.baseten.co/llms.txt
- [fw-models-lib]: https://fireworks.ai/models (embedded model catalog data, `serverless` flags)
- [fw-spark]: https://fireworks.ai/models/fireworks/muse-spark-open
- [fw-glimmer]: https://fireworks.ai/models/fireworks/muse-glimmer-30b
- [fw-serverless-pricing]: https://docs.fireworks.ai/serverless/pricing
- [fw-pricing]: https://fireworks.ai/pricing
- [fw-ft-models]: https://docs.fireworks.ai/fine-tuning/models
- [fw-glimmer-cookbook]: https://docs.fireworks.ai/fine-tuning/training-api/cookbook/muse-glimmer
- [fw-serverless-training]: https://docs.fireworks.ai/fine-tuning/training-api/serverless
- [fw-deploy-lora]: https://docs.fireworks.ai/fine-tuning/deploying-loras
- [fw-autoscaling]: https://docs.fireworks.ai/deployments/autoscaling
- [fw-quickstart]: https://docs.fireworks.ai/getting-started/quickstart
- [fw-credit-redeem]: https://docs.fireworks.ai/tools-sdks/firectl/commands/credit-redemption-redeem
- [modal-endpoints]: https://modal.com/docs/guide/endpoints
- [modal-shared]: https://modal.com/docs/guide/shared-endpoints
- [modal-dedicated]: https://modal.com/docs/guide/dedicated-endpoints
- [modal-supported]: https://modal.com/docs/guide/supported-models
- [modal-lib-spark]: https://modal.com/library/meta/muse-spark-open
- [modal-web]: https://modal.com/docs/guide/webhooks
- [modal-webhook-urls]: https://modal.com/docs/guide/webhook-urls
- [modal-fastapi-ref]: https://modal.com/docs/sdk/py/latest/fastapi_endpoint
- [modal-asgi-ref]: https://modal.com/docs/sdk/py/latest/asgi_app
- [modal-timeouts]: https://modal.com/docs/guide/webhook-timeouts
- [modal-streaming]: https://modal.com/docs/guide/streaming-endpoints
- [modal-proxy-auth]: https://modal.com/docs/guide/webhook-proxy-auth
- [modal-gpu]: https://modal.com/docs/guide/gpu
- [modal-pricing]: https://modal.com/pricing
- [modal-scale]: https://modal.com/docs/guide/scale
- [modal-guide]: https://modal.com/docs/guide
- [modal-token]: https://modal.com/docs/cli/latest/token
- [modal-billing]: https://modal.com/docs/guide/billing
- [pypi-modal]: https://pypi.org/project/modal/ (metadata: https://pypi.org/pypi/modal/json)

[cv-event]: https://cerebralvalley.ai/e/meta-ai-developer-hackathon
[cv-event-md]: https://cerebralvalley.ai/e/meta-ai-developer-hackathon.md
[cv-rules]: https://cerebralvalley.ai/e/meta-ai-developer-hackathon/waiver
[cv-submit]: https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit
[cv-api]: https://api.cerebralvalley.ai/v1/event/78e32764-9651-4942-b1eb-4401af6a3209/hackathon
[cv-js]: https://cerebralvalley.ai/_next/static/chunks/42b01vvcicuhg.js
[meta-event]: https://dev.meta.ai/events/global-hackathon
[meta-spark-open-page]: https://dev.meta.ai/models/muse-spark-open/
[meta-glimmer-page]: https://dev.meta.ai/models/muse-glimmer/
[meta-spark-open-doc]: https://dev.meta.ai/docs/muse-spark-open
[meta-spark-open-deploy]: https://dev.meta.ai/docs/muse-spark-open/deploy
[meta-spark-open-post]: https://dev.meta.ai/docs/muse-spark-open/post-training
[meta-glimmer-doc]: https://dev.meta.ai/docs/muse-glimmer
[meta-glimmer-deploy]: https://dev.meta.ai/docs/muse-glimmer/deploy
[meta-pricing]: https://dev.meta.ai/docs/pricing-rate-limits
[nist-dst]: https://www.nist.gov/pml/time-and-frequency-division/popular-links/daylight-saving-time-dst
[reconscribe]: https://reconscribe.com/meta-global-ai-developer-hackathon-2026/
[bt-modelapis]: https://docs.baseten.co/inference/model-apis/overview
[bt-limits]: https://docs.baseten.co/inference/model-apis/pricing-and-limits
[bt-lib]: https://www.baseten.co/library/muse-spark-open/
[bt-library]: https://www.baseten.co/library/
[bt-blog]: https://www.baseten.co/blog/muse-spark-open-launch/
[bt-pricing]: https://www.baseten.co/pricing/
[bt-billing]: https://docs.baseten.co/organization/billing
[bt-llms]: https://docs.baseten.co/llms.txt
[fw-models-lib]: https://fireworks.ai/models
[fw-spark]: https://fireworks.ai/models/fireworks/muse-spark-open
[fw-glimmer]: https://fireworks.ai/models/fireworks/muse-glimmer-30b
[fw-serverless-pricing]: https://docs.fireworks.ai/serverless/pricing
[fw-pricing]: https://fireworks.ai/pricing
[fw-ft-models]: https://docs.fireworks.ai/fine-tuning/models
[fw-glimmer-cookbook]: https://docs.fireworks.ai/fine-tuning/training-api/cookbook/muse-glimmer
[fw-serverless-training]: https://docs.fireworks.ai/fine-tuning/training-api/serverless
[fw-deploy-lora]: https://docs.fireworks.ai/fine-tuning/deploying-loras
[fw-autoscaling]: https://docs.fireworks.ai/deployments/autoscaling
[fw-quickstart]: https://docs.fireworks.ai/getting-started/quickstart
[fw-credit-redeem]: https://docs.fireworks.ai/tools-sdks/firectl/commands/credit-redemption-redeem
[modal-endpoints]: https://modal.com/docs/guide/endpoints
[modal-shared]: https://modal.com/docs/guide/shared-endpoints
[modal-dedicated]: https://modal.com/docs/guide/dedicated-endpoints
[modal-supported]: https://modal.com/docs/guide/supported-models
[modal-lib-spark]: https://modal.com/library/meta/muse-spark-open
[modal-web]: https://modal.com/docs/guide/webhooks
[modal-webhook-urls]: https://modal.com/docs/guide/webhook-urls
[modal-fastapi-ref]: https://modal.com/docs/sdk/py/latest/fastapi_endpoint
[modal-asgi-ref]: https://modal.com/docs/sdk/py/latest/asgi_app
[modal-timeouts]: https://modal.com/docs/guide/webhook-timeouts
[modal-streaming]: https://modal.com/docs/guide/streaming-endpoints
[modal-proxy-auth]: https://modal.com/docs/guide/webhook-proxy-auth
[modal-gpu]: https://modal.com/docs/guide/gpu
[modal-pricing]: https://modal.com/pricing
[modal-scale]: https://modal.com/docs/guide/scale
[modal-guide]: https://modal.com/docs/guide
[modal-token]: https://modal.com/docs/cli/latest/token
[modal-billing]: https://modal.com/docs/guide/billing
[pypi-modal]: https://pypi.org/project/modal/
