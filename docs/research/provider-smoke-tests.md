# Provider smoke tests (live, Nov 2 2026)

Ground truth from the project's own credentials, not from docs. Probe scripts were read-only listing calls plus one tiny chat call per provider. No keys were printed or committed.

## Models visible to our keys

| Provider | Endpoint | Meta models visible |
| --- | --- | --- |
| Meta Model API | `GET https://api.meta.ai/v1/models` (Bearer) | `muse-wonder-1.0`, `muse-spark-1.3`, `muse-spark-1.3-contributor`, `muse-spark-1.2`, `muse-spark-1.2-contributor`, `muse-spark-1.1`, `sam-3.1`, `muse-voice-transcribe-1.0`, `muse-image-1.0` |
| Baseten Model APIs | `GET https://inference.baseten.co/v1/models` (Bearer) | `meta-models/muse-spark-open` (20 models total, the rest non-Meta) |
| Fireworks serverless | `GET https://api.fireworks.ai/inference/v1/models` (Bearer) | `accounts/fireworks/models/muse-spark-open` |
| Fireworks catalogue | `GET https://api.fireworks.ai/v1/accounts/fireworks/models` | `muse-glimmer-30b` (HF base model, `supportsLora=true`, not in the serverless list), `muse-spark-open` (`supportsLora=false`), `muse-spark-open-nvfp4` (816B-A42B, `supportsLora=true`), `kalshi-glimmer-decision-v1` (an existing LoRA add-on on Muse Glimmer 30B) |
| Modal | `modal app list` with `MODAL_TOKEN_ID`/`MODAL_TOKEN_SECRET` env vars | Auth OK; workspace has no apps yet |

Implications:

- Every hosted model named in the PRD exists for our key. `muse-image-1.0` is also available but unused so far.
- "Muse Glimmer" exists on Fireworks as `muse-glimmer-30b`, a LoRA-capable base model. It is **not** serverless, so serving a LoRA on it likely needs an on-demand deployment (GPU-hour billing against the $25 credit). Treat the Glimmer LoRA annotator as a stretch goal.
- Fireworks serverless `muse-spark-open` does not support LoRA; only the NVFP4 variant does.

## Chat completions behaviour

All four LLM endpoints accept the OpenAI chat-completions schema at `<base>/chat/completions` with `Authorization: Bearer <key>`, and honour `response_format: {"type": "json_schema", "json_schema": {..., "strict": true}}`.

| Model | Latency (tiny prompt) | Returned JSON | Notes |
| --- | --- | --- | --- |
| `muse-spark-1.3` (Meta) | 2.4 s | `{"higher_group":"disease","ok":true}` | Reasoning model: 247 reasoning tokens |
| `muse-wonder-1.0` (Meta) | 2.8 s | valid | Reasoning model: 121 reasoning tokens |
| `meta-models/muse-spark-open` (Baseten) | 2.1 s | valid | Returns `reasoning_content`; speculative decoding stats in usage |
| `accounts/fireworks/models/muse-spark-open` (Fireworks) | 5.5 s | valid | Returns `reasoning_content` |

Gotchas:

- **All of them are reasoning models.** With `max_tokens: 200` every model spent the whole budget on reasoning and returned empty content (`finish_reason: length`). Use a generous `max_tokens` (2,000+) and `reasoning_effort: "low"` for routine calls. `reasoning_effort` is accepted by all four.
- Baseten and Fireworks expose the chain of thought in `message.reasoning_content`; Meta does not.

## SAM 3.1 (live, synthetic image)

Probe: a 640×480 PNG with three filled circles at known positions, concept prompt `circle`, streamed `POST /v1/responses` with `model: sam-3.1`, parsed with Meta's `meta-sam-parser` following the cookbook's `stream_events` workaround (synthesise `response.output_text.done` from `response.content_part.done`).

- Completed in **2.4 s**; 3 objects, 6 records (box + mask each), no parser diagnostics.
- **Boxes are frame pixels with exclusive right/bottom in the parsed record**: the circle drawn over x 70..170 came back as `left=70, right=171`.
- **Masks are box-local crops** whose size equals the box (101×101, 141×141, 81×81). Global pixel = `(box.left + mask_x, box.top + mask_y)`. This settles the open question in `meta-platform.md` §3.
- Mask areas match the drawn circles (7,982 px measured vs π·50.5² ≈ 8,012 expected).

Not yet tested live: `muse-voice-transcribe-1.0`, image input to `muse-spark-1.3`, and SAM on real tissue images.
