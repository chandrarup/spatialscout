# Meta developer platform: capability probe for SpatialScout

Researched 2026-11-02 for the Meta Global AI Developer Hackathon (submissions due 2026-11-04, 9:00 PM ET).

> **Correction (Nov 2, after review):** the judging weights are official. They appear in the Official Rules on the event waiver page; see `hackathon-and-partners.md` §2. Statements below that call them unverified or third-party are superseded.

## How to read this

- **Verified (Y)** means the fact is stated in an official Meta source (dev.meta.ai docs, Meta GitHub repos, Meta's Hugging Face repos, Meta model cards) as fetched on 2026-11-02. **UNVERIFIED** means no official source stated it.
- No API key was created and no authenticated call was made. So "Y" means "documented", not "tested with a live key". Two unauthenticated probes were run:
  - `GET https://api.meta.ai/v1/status` returned `200` and `{"is_alive":true,"service_status":"operational",...}`.
  - `GET https://api.meta.ai/v1/models` with no key returned `401` and `{"error":{"code":"invalid_api_key","message":"Unauthorized","param":null,"type":"authentication_error"}}`, an OpenAI-style error envelope.
- Every doc page cited as `https://dev.meta.ai/docs/<path>` also has a Markdown version at `https://dev.meta.ai/docs/<path>.md`. The index is at https://dev.meta.ai/llms.txt.
- **First thing to do with a real key:** call `GET /v1/models` and confirm that `muse-wonder-1.0`, `muse-spark-1.3`, `sam-3.1` and `muse-voice-transcribe-1.0` are enabled for your team. A team without access to a model gets `404 model_not_found` (https://dev.meta.ai/docs/sam/segmenting, https://dev.meta.ai/docs/models).

## Verdict on each name in the project docs

| Name in the spec | Real? | Exact ID or real name | Source |
|---|---|---|---|
| Muse Wonder | Yes (preview) | `muse-wonder-1.0` | https://dev.meta.ai/docs/models |
| Muse Spark 1.3 | Yes | `muse-spark-1.3` (Standard mode), `muse-spark-1.3-contributor` (Contributor mode) | https://dev.meta.ai/docs/models |
| SAM 3.1 | Yes | `sam-3.1` in the docs. The marketing page's price table prints `sam-3-1` (see the discrepancy note below). | https://dev.meta.ai/docs/models, https://dev.meta.ai/models/sam-3-1/ |
| Muse Voice Transcribe | Yes | `muse-voice-transcribe-1.0` | https://dev.meta.ai/docs/models |
| Muse Code | Yes, but it is a CLI coding agent (the `muse` binary), **not a model ID** | n/a | https://dev.meta.ai/docs/muse-code |
| Muse Spark Open | Yes, open weights | `meta-models/Muse-Spark-Open-816B-A42B` on Hugging Face (816B total, 42B active) | https://dev.meta.ai/docs/muse-spark-open |
| Muse Glimmer | Yes, open weights | `meta-models/Muse-Glimmer-30B` on Hugging Face (30B dense) | https://dev.meta.ai/docs/muse-glimmer |
| "SAM 3.1 Video Tracking API" | **No separate API.** Video tracking is the same `POST /v1/responses` call with an `input_video` part. | `sam-3.1` | https://dev.meta.ai/docs/sam/segmenting |
| `muse-glimmer-lora` (spec §4 JSON) | **Not a Meta ID.** The project invented this string. | n/a | not in https://dev.meta.ai/llms.txt |
| "Standard Mode" | Real, but it is a pricing and data-use mode chosen by model ID, **not a request parameter** | `muse-spark-1.3` = Standard; `-contributor` suffix = Contributor | https://dev.meta.ai/docs/pricing-rate-limits |

**SAM ID discrepancy.** The product page https://dev.meta.ai/models/sam-3-1/ lists the model as `sam-3-1` in its price table. Every docs page, the rate-limit table and Meta's own cookbook code (`MODEL = "sam-3.1"` in https://github.com/meta-models/meta-model-cookbook/blob/main/07_sam/01_api_basics/python/sam_api.py) use `sam-3.1`. Use `sam-3.1` and confirm it with `GET /v1/models`.

## Model table

| Name | Exact ID | Modality | Endpoint | Price (pay-as-you-go) | Verified |
|---|---|---|---|---|---|
| Muse Wonder | `muse-wonder-1.0` | In: text, image, video, audio, PDF. Out: text. Context 1,048,576 tokens. | `POST /v1/responses`, `/v1/chat/completions`, `/v1/messages` | Input $4.00, cached input $0.20, output $20.00 per 1M tokens. Standard mode only. | Y ([models](https://dev.meta.ai/docs/models), [pricing](https://dev.meta.ai/docs/pricing-rate-limits)) |
| Muse Wonder Full | none on the API | as above | Muse Code subscription only (Power and Maximum Usage plans) | subscription | Y ([models](https://dev.meta.ai/docs/models)) |
| Muse Spark 1.3 | `muse-spark-1.3` | In: text, image, video, audio (degraded on 1.3), PDF. Out: text. Context 1,048,576 tokens. | same three endpoints | $1.25 / $0.15 cached / $4.25 per 1M tokens | Y ([models](https://dev.meta.ai/docs/models), [pricing](https://dev.meta.ai/docs/pricing-rate-limits)) |
| Muse Spark 1.3 Contributor | `muse-spark-1.3-contributor` | same | same | $0.10 / $0.002 cached / $0.20 per 1M tokens. Meta may train on your content. | Y ([pricing](https://dev.meta.ai/docs/pricing-rate-limits)) |
| Muse Spark 1.2 / 1.1 | `muse-spark-1.2`, `muse-spark-1.2-contributor`, `muse-spark-1.1` | same | same | same as Spark 1.3 | Y ([models](https://dev.meta.ai/docs/models)) |
| SAM 3.1 | `sam-3.1` | In: concept text prompt **or** box/point prompts, plus one image or video. Out: boxes and masks as special-token text. | `POST /v1/responses` (streaming recommended); clips can go through `POST /v1/files` | $2.50 per 1,000 images; $0.20 per 1,000 video frames, **minimum 50 frames billed per video request** | Y ([pricing](https://dev.meta.ai/docs/pricing-rate-limits), [segmenting](https://dev.meta.ai/docs/sam/segmenting)) |
| Muse Voice Transcribe | `muse-voice-transcribe-1.0` | In: audio (WAV file, or raw PCM over WebSocket). Out: transcript text. | `POST /v1/asr/transcribe` (multipart); `wss://api.meta.ai/v1/asr/realtime` | $0.18 per hour of audio, metered in whole seconds | Y ([speech-to-text](https://dev.meta.ai/docs/speech-to-text), [pricing](https://dev.meta.ai/docs/pricing-rate-limits)) |
| Muse Image (not in plan) | `muse-image-1.0` | In: text, image. Out: image. | `/v1/responses`, `/v1/images/generations`, `/v1/images/edits` | $0.01 per image | Y ([models](https://dev.meta.ai/docs/models)) |
| Muse Code | n/a (product) | CLI agent `muse`. Default model `muse-spark-1.2`. | terminal or CI | pay-as-you-go per model, or subscription | Y ([muse-code](https://dev.meta.ai/docs/muse-code)) |
| Muse Spark Open | HF `meta-models/Muse-Spark-Open-816B-A42B` (BF16, ~1.65 TB) and `-NVFP4` (~537 GB) | In: text, image, video, audio. Out: text. Context 1,048,576 tokens. | Not on Model API. Self-host, or use providers; Meta lists Baseten's model string as `meta-models/muse-spark-open` at `https://inference.baseten.co/v1`. | provider pricing (not checked here) | Y ([muse-spark-open](https://dev.meta.ai/docs/muse-spark-open), [deploy](https://dev.meta.ai/docs/muse-spark-open/deploy)) |
| Muse Glimmer | HF `meta-models/Muse-Glimmer-30B` (bf16, ~60 GB); `-GGUF`, `-assistant`, `-ExecuTorch-PTE` | In: text, image. Out: text. Context 128K by default. | Not on Model API. Self-host. Meta lists only Together AI (`meta-models/Muse-Glimmer-30B`) as a hosted provider. | n/a | Y ([muse-glimmer](https://dev.meta.ai/docs/muse-glimmer), [get-the-model](https://dev.meta.ai/docs/muse-glimmer/get-the-model), [deploy](https://dev.meta.ai/docs/muse-glimmer/deploy)) |
| SAM 3.1 (open weights) | HF `facebook/sam3.1`, file `sam3.1_multiplex.pt` (3,502,755,717 bytes) | video predictor with Object Multiplex | self-host with `facebookresearch/sam3` | free under the SAM License; **gated, manual approval** | Y ([HF API](https://huggingface.co/api/models/facebook/sam3.1), [repo](https://github.com/facebookresearch/sam3)) |

Muse Wonder's model card (released October 12, 2026) lists input as text, image, video and audio, and context as 1M tokens (https://research.meta.ai/static/muse-wonder-model-card). The docs add PDF as an input (https://dev.meta.ai/docs/models). Muse Wonder and Muse Wonder Full are not available in South Korea (https://dev.meta.ai/docs/models).

## 1. Authentication, OpenAI compatibility and SDKs

- **Base URL and header.** The base URL is `https://api.meta.ai/v1` and the header is `Authorization: Bearer $MODEL_API_KEY`. The docs use the env var name `MODEL_API_KEY` (https://dev.meta.ai/docs/api-reference).
- **Key format.** Keys start with `LLM_`, then a numeric ID and the secret, separated by underscores (https://dev.meta.ai/docs/authentication).
- **Creating keys.** In the Model API dashboard at https://dev.meta.ai/, go to **API keys**, then **Create API key**. The key is shown once (https://dev.meta.ai/docs/authentication).
- **Rate limits are shared.** Limits apply per team, not per key (https://dev.meta.ai/docs/authentication).
- **Keep keys server-side.** Don't put keys in browser code; proxy requests through your own server (https://dev.meta.ai/docs/authentication).
- **OpenAI compatible: yes, for text and vision.**
  - `POST /v1/responses` and `POST /v1/chat/completions` are documented as OpenAI-compatible.
  - `POST /v1/messages` is Anthropic Messages-compatible.
  - Errors use the OpenAI-style envelope `{error:{message,type,param,code}}`.
  - Source: https://dev.meta.ai/docs/api-reference
- **Not OpenAI-shaped:**
  - Speech-to-text uses custom endpoints (`/v1/asr/transcribe`, `/v1/asr/realtime`), not `/v1/audio/transcriptions` (https://dev.meta.ai/docs/speech-to-text).
  - SAM returns a custom token grammar inside the Responses `output_text` (https://dev.meta.ai/docs/sam/reading-segmentation).
- **Official SDK: no Meta-branded Model API SDK.** The docs say to use:
  - the OpenAI SDK: `pip install openai`, `npm install openai`
  - the Anthropic SDK, with `base_url="https://api.meta.ai"` and `auth_token=`
  - any OpenAI-compatible client such as LangChain, LlamaIndex, Vercel AI SDK or LiteLLM (`model="openai/muse-spark-1.3"`)

  None of them reads `MODEL_API_KEY` automatically, so pass the key explicitly (https://dev.meta.ai/docs/sdks). Current registry versions: `openai` 3.42.1 on PyPI (https://pypi.org/project/openai/) and `openai` 7.47.0 on npm (https://www.npmjs.com/package/openai). The docs pin no minimum version; the official SAM cookbook's `requirements.txt` says `openai>=1.0` (https://github.com/meta-models/meta-model-cookbook/tree/main/07_sam/01_api_basics).
- **Official Meta packages:**
  - SAM output parsers: `meta-sam-parser` 0.1.0 on PyPI, Python 3.10 or later (https://pypi.org/project/meta-sam-parser/). `@meta-sam/parser` 0.1.0, `@meta-sam/graphics` 0.1.13, `@meta-sam/video` 0.1.5 and `@meta-sam/react` 0.1.14 on npm (https://www.npmjs.com/package/@meta-sam/parser). Source repo: https://github.com/meta-models/meta-sam.
  - Muse Code TypeScript SDK: `@muse-code/sdk` 1.4.14 (https://www.npmjs.com/package/@muse-code/sdk, https://dev.meta.ai/docs/muse-code).
- **Muse Code reads a different variable.** It uses `META_API_KEY`, not `MODEL_API_KEY`. It installs with `curl -fsSL https://dev.meta.ai/install.sh | sh` and its default model is `muse-spark-1.2` (https://dev.meta.ai/docs/muse-code, https://dev.meta.ai/docs/muse-code/auth).

## 2. Muse Wonder and Muse Spark 1.3 requests

### Endpoints

- Wonder and Spark "take the same requests on the same endpoints", so switching between them is only a model ID change (https://dev.meta.ai/docs/models).
- The Chat Completions protocol page says it "serves the Muse Spark text models" (https://dev.meta.ai/docs/protocols/chat-completions). The models page lists Wonder on Responses, Chat Completions and Messages. **Use the Responses API for the Wonder planner.** It is the recommended path for agentic and tool loops and the only one that carries reasoning across turns (https://dev.meta.ai/docs/protocols/responses).

### Structured output (JSON Schema)

- **Chat Completions:** `response_format: {type: "json_schema", json_schema: {name, schema, strict?}}`.
- **Responses:** `text.format: {type: "json_schema", name, schema, strict?}`. Sending the other endpoint's parameter does not configure structured output, and `text.format` on Chat Completions returns 400.
- Decoding is constrained, so the output is guaranteed to match the schema. `strict` defaults to `false` and only controls extra validation of the schema itself.
- Recursive schemas return 400.
- Limits: nesting depth 10, 5,000 properties, 1,000 enum values.
- The OpenAI SDK's `beta.chat.completions.parse()` with a Pydantic model works.
- Sources: https://dev.meta.ai/docs/structured-output, https://dev.meta.ai/docs/api-reference/responses/schemas

### Tool calling

- Use OpenAI-style `tools`. On Chat Completions the fields nest under `function`; on Responses they are flat. Parallel tool calls default on (`parallel_tool_calls`).
- **`tool_choice` accepts only `"auto"`.** `"none"`, `"required"` and named choices return 400.
- **Tool-call arguments are "not guaranteed to validate" against the schema.** Validate them in your own code.
- Function names: at most one dot.
- Sources: https://dev.meta.ai/docs/tool-calling

### Image input

- **Responses:** `{"type":"input_image","image_url":"<https URL or data:image/...;base64,...>"}`, or `file_id`.
- **Chat Completions:** `{"type":"image_url","image_url":{"url":"<URL or data URL>"}}`.
- Images go in `user` messages only.
- Limits: 50 images per request, 50 MB per inline image, 1 GiB through the Files API.
- MIME types: `image/jpeg`, `image/jpg`, `image/png`, `image/gif`, `image/webp`, `image/x-icon`.
- Grounding coordinates come back on a normalized 0-1000 grid.
- Sources: https://dev.meta.ai/docs/image-understanding. Base64 PNG data URLs are used verbatim in https://dev.meta.ai/docs/cookbook/vision-input.

### Streaming

- `stream: true` returns server-sent events (SSE).
- Non-streaming requests have a server time limit and can return `504 gateway_timeout`; streaming requests are exempt. Responses also supports `background: true`, but not together with `stream: true` on creation.
- Sources: https://dev.meta.ai/docs/protocols/chat-completions, https://dev.meta.ai/docs/protocols/responses

### Context and reasoning

- **Context window:** 1,048,576 tokens. Input plus `max_completion_tokens`/`max_output_tokens` must fit inside it (https://dev.meta.ai/docs/models, https://dev.meta.ai/docs/error-handling).
- **`reasoning_effort` on Chat Completions, `reasoning.effort` on Responses.** Values: `minimal`, `low`, `medium`, `high`, `xhigh`, `max`.
  - `max` works only on `muse-wonder-1.0` and `muse-spark-1.3`, not on `-contributor`.
  - `"none"` returns 400.
  - Reasoning tokens are billed as output.
  - Source: https://dev.meta.ai/docs/reasoning
- **Unsupported parameters:**
  - Rejected with 400: `stop`, `n>1`, `logprobs`, `logit_bias`, `prediction`, `verbosity`, `modalities`, `audio`.
  - `frequency_penalty` and `presence_penalty` "can return an error".
  - `seed` is deprecated and determinism is not guaranteed.
  - Default `temperature` is 1.0 and Meta recommends leaving it.
  - Source: https://dev.meta.ai/docs/protocols/chat-completions

### "Standard Mode"

- Standard mode: your content is not used for training. Contributor mode: discounted, and your content may be used for training.
- On pay-as-you-go you pick the mode by model ID, for example `muse-spark-1.3` versus `muse-spark-1.3-contributor`.
- Muse Wonder on the API is Standard only.
- Sources: https://dev.meta.ai/docs/pricing-rate-limits, https://dev.meta.ai/docs/models

### Audio caveat

Audio understanding on Muse Spark 1.3 "is not fully supported". The docs recommend Spark 1.2 or Muse Voice Transcribe for audio (https://dev.meta.ai/docs/models).

## 3. SAM 3.1 hosted API

### Endpoint and request

- **Endpoint:** `POST https://api.meta.ai/v1/responses`, `model: "sam-3.1"`, with the same Bearer key (https://dev.meta.ai/docs/sam/overview).
- **Request shape:** one `user` message containing one `input_text` (the prompt) and one media part (https://dev.meta.ai/docs/sam/segmenting).
- **Media:**
  - `input_image` with `image_url` (public URL or base64 data URL).
  - `input_video` with `video_url` (URL or data URL) or `file_id` from `POST /v1/files` with `purpose=user_data`.
  - Video must be MP4 or MOV with H.264, H.265 or MPEG-4. VP9 and WebM are not accepted.
  - Source: https://dev.meta.ai/docs/sam/segmenting

### Prompts

Use one of two kinds per request, never both (https://dev.meta.ai/docs/sam/segmenting):

- **Concept prompt:** a short noun phrase.
  - One concept per request. Lists like `"bus, bicycle"` return zero matches.
  - Commands, questions, negation and spatial phrasing are unreliable.
  - Zero matches returns an empty `output_text` and is not an error.
- **Box and point prompts:** written in the same token grammar as the output, for example `<0f>1<|box;x1=..;y1=..;x2=..;y2=..;w=W;h=H|>,2<|point;x=..;y=..;w=W;h=H|>-<|point;...|>`.
  - A `-` before a point marks it negative.
  - Coordinates are in media pixels.
  - Up to 16 prompted objects.
  - In video, prompts can go on any frame (`<Nf>`).
  - `metadata.propagation_direction` is `both` (default), `forward` or `backward`.

### Metadata options (string values)

- `metadata.include_confidence: "true"` adds `c` (0-1) to each box and mask.
- `metadata.mask_encoding: "lossless"` (default, `~` marker) or `"one_bit"` (`!` marker, several times smaller). Box and point prompts always return `one_bit`.
- Source: https://dev.meta.ai/docs/sam/segmenting

### Output format

The output is special-token text in `output_text`: one line per frame (https://dev.meta.ai/docs/sam/reading-segmentation).

```text
<Nf>id<|box;x1=..;y1=..;x2=..;y2=..;w=<frameW>;h=<frameH>[;c=..]|><|mask;x=0;y=0[;c=..];data=<H>,<W>,<enc>payload|>,id<|box;...|><|mask;...|>
```

- **Boxes** are in source pixels. `x2` and `y2` are inclusive on the wire.
- **Masks:**
  - `data=H,W` is height then width.
  - The payload is **base85, not base64**.
  - The mask raster is smaller than the frame. In every documented example its H×W equals the box size (for example box 211..270 × 228..254 gives mask `27,60`), so masks appear to be box-local crops. The cookbook also writes each decoded SVG with a mask-sized `viewBox`.
  - **Inference, confirm on the first live call:** to place a mask in frame pixels, offset it by the box's `x1`/`y1`. FR-2.2's global-polygon stitching depends on this.
  - The parsers decode masks to a binary raster, to **COCO RLE** (`{size:[h,w],counts}`, column-major) or to an **SVG path** polygon: `decode_mask_to_raster`, `decode_mask_to_rle`, `decode_mask_to_svg_path` (https://dev.meta.ai/docs/sam/client-libraries).
- **Frames:** frames with no objects emit no line. Frame order can be non-ascending for box and point prompts.
- **Object IDs:** an ID is "a stable per-object id across frames". The docs add: "don't rely on the id across an object's entry, exit, or full occlusion, or over very long clips" (https://dev.meta.ai/docs/sam/reading-segmentation).

### Parsing gotcha from Meta's cookbook code

"The API streams `response.content_part.done` but not `response.output_text.done`, which the parser uses to close a lane, so synthesize it from the content part." The official `sam_api.py` shows how (https://github.com/meta-models/meta-model-cookbook/blob/main/07_sam/01_api_basics/python/sam_api.py).

### Limits

- Clips up to 15,000 frames (about 10 minutes).
- Video tracks **up to 16 objects per frame**. Image requests return every match.
- Inline media up to 50 MB; Files API uploads up to 1 GiB; 100 GiB storage per team; uploads don't expire unless you set `expires_after`.
- 3,000 RPM.
- Results "can vary slightly between runs".
- Sources: https://dev.meta.ai/docs/sam/segmenting, https://dev.meta.ai/docs/file-handling, https://dev.meta.ai/docs/pricing-rate-limits

### Price

- Image: $2.50 per 1,000 images.
- Video: $0.20 per 1,000 frames, with a minimum of 50 frames billed per video request. `usage.video_frames_processed` reports the frames billed.
- Streaming and non-streaming cost the same.
- Source: https://dev.meta.ai/docs/pricing-rate-limits

## 4. Muse Voice Transcribe

- **File endpoint:** `POST https://api.meta.ai/v1/asr/transcribe`, `multipart/form-data` with two parts (https://dev.meta.ai/docs/api-reference/voice/transcribe):
  - `request`: JSON, for example `{"model":"muse-voice-transcribe-1.0","audioEncoding":"WAV","mode":"PUSH_TO_TALK"}`.
  - `audio`: the WAV file.
  - The `Accept` header picks the response: JSON (default), SSE (`text/event-stream`) or `text/plain`.
- **Accepted audio: WAV only.** `audioEncoding` takes only `WAV`: a RIFF/WAVE container with mono 16-bit integer PCM at 16 kHz or 24 kHz.
  - Maximum 10 minutes per file (400 above that); maximum body 32 MB (413 above that).
  - Source: https://dev.meta.ai/docs/api-reference/voice/schemas, https://dev.meta.ai/docs/speech-to-text
- **Browser recordings need converting.** Browser MediaRecorder output (webm/opus) is not an accepted format. Convert it server-side with Meta's documented command: `ffmpeg -i input.m4a -ac 1 -ar 24000 -c:a pcm_s16le -map_metadata -1 output.wav` (https://dev.meta.ai/docs/speech-to-text).
- **Realtime endpoint:** `wss://api.meta.ai/v1/asr/realtime`.
  - The key goes in the first JSON handshake frame (`authorization.accessToken: "Bearer <key>"`), which must arrive within 10 seconds. The HTTP `Authorization` header is ignored.
  - Audio is sent as binary frames of raw s16le mono PCM (`PCM_24KHZ` or `PCM_16KHZ`), paced at real time.
  - The docs say: "Decode WAV, MP3, Opus, or other containers before streaming."
  - End the stream with `{"type":"endStream"}`. Sessions last up to 60 minutes.
  - Sources: https://dev.meta.ai/docs/api-reference/voice/realtime, https://dev.meta.ai/docs/speech-to-text
  - Because the key travels in the handshake, a browser client must go through your server proxy (https://dev.meta.ai/docs/authentication).
- **Modes:**
  - `PUSH_TO_TALK` (default)
  - `ENDPOINTING` (turn detection)
  - `DIARIZATION` (speaker labels A, B, …)
  - Options: `keywords` (vocabulary biasing), `languageBias` (25 languages).
  - Timestamps are turn-level only, not word-level.
  - Source: https://dev.meta.ai/docs/speech-to-text
- **Price:** $0.18 per hour ($3.00 per 1,000 minutes). Billed in whole seconds, rounded down. Requests that fail before producing a transcript, and 429s, are not billed (https://dev.meta.ai/docs/speech-to-text, https://dev.meta.ai/models/muse-voice-transcribe/).
- **Limits:** 256 concurrent streams and 16,000 streams per hour per team, shared by both endpoints. A rejected file request returns 429; a rejected realtime stream closes with code 1013 (https://dev.meta.ai/docs/pricing-rate-limits).

## 5. Rate limits, pricing and hackathon credits

### Rate limits

Limits are per team and per model (https://dev.meta.ai/docs/pricing-rate-limits).

| Model | RPM | TPM | Other |
|---|---|---|---|
| `muse-wonder-1.0` | 3,000 | 4,000,000 | |
| `muse-spark-1.3`, `-1.2`, `-1.1` | 3,000 | 4,000,000 | |
| `muse-spark-1.3-contributor`, `-1.2-contributor` | 150 | 3,000,000 | |
| `sam-3.1` | 3,000 | none | |
| `muse-image-1.0` | 150 | none | |
| `muse-voice-transcribe-1.0` | none | none | 256 concurrent streams; 16,000 streams per hour |

- Background responses are limited to 600 submissions per minute per team.
- `x-ratelimit-*` headers come back on token-based responses, not on transcription responses.
- Retry 429s with exponential backoff and honor `Retry-After`.
- Source: https://dev.meta.ai/docs/pricing-rate-limits

### Other charges

- Web search grounding: $2.50 per 1,000 queries.
- Meta's injected steering tokens are not billed.
- Source: https://dev.meta.ai/docs/pricing-rate-limits

### Billing

- Charges accrue as you use the API and are charged at a payment threshold or on the 1st of the month (https://dev.meta.ai/help/billing/api-bill).
- **There is no hard spend cap**, only an email alert (https://dev.meta.ai/help/billing/spend-limit-alert).

### Hackathon credits

- **Meta Model API credit amount (spec says $150): UNVERIFIED.** It is not stated on https://dev.meta.ai/events/global-hackathon or https://cerebralvalley.ai/e/meta-ai-developer-hackathon. How credits are applied to a Meta account is also UNVERIFIED; no official page describes it.
- **Partner credits.** These are "to select participants", per https://cerebralvalley.ai/e/meta-ai-developer-hackathon:
  - Baseten: $100 and 2M TPM rate limits, for Meta's open-weights models.
  - Modal: $100, for Meta's open-weights models through Endpoints, plus serverless GPUs, sandboxes and training tools.
  - **Fireworks: $100.** The spec says $25.
- **Official judging criteria are qualitative.** Indie track: "creativity, technical ambition, and whether it works". Startup track: "technical execution and whether it holds up in production" (https://dev.meta.ai/events/global-hackathon). The spec's percentage weights come from a third-party site (reconscribe.com) and are **UNVERIFIED**. Both event pages say "Official Rules will be published before the Hackathon begins on October 26, 2026"; no public rules URL was found.

## 6. SAM 3.1 open weights

- **Checkpoint:** yes. `facebook/sam3.1` on Hugging Face holds `sam3.1_multiplex.pt` (3,502,755,717 bytes) plus config and tokenizer files. It was released 2026-03-27 with Object Multiplex for joint multi-object tracking.
  - Sources: https://huggingface.co/api/models/facebook/sam3.1/tree/main, https://github.com/facebookresearch/sam3/blob/main/RELEASE_SAM3p1.md
  - The model card says there is "no Hugging Face Transformers integration" (https://huggingface.co/facebook/sam3.1).
- **Gated with manual approval.**
  - The HF API reports `"gated": "manual"` (https://huggingface.co/api/models/facebook/sam3.1).
  - Under manual approval, requests "have to be approved manually by the authors, which can take more time" (https://huggingface.co/docs/hub/models-gated).
  - The repo README says to request access, then `hf auth login` (https://github.com/facebookresearch/sam3).
  - **Two days before the deadline, this is a schedule risk.**
- **Licence:** the SAM License (last updated November 19, 2025). It grants use, modification and redistribution; the HF tag reads `license:other` (https://github.com/facebookresearch/sam3/blob/main/LICENSE).
- **Video predictor API:** yes.
  - `build_sam3_predictor(version="sam3.1")` or `build_sam3_multiplex_video_predictor()` returns a predictor with `handle_request` / `handle_stream_request`.
  - Request types: `start_session`, `add_prompt` (text, points, boxes), `propagate_in_video`, `remove_object`, `reset_session`, `close_session`.
  - Outputs include `out_binary_masks`.
  - Default `max_num_objects=16`.
  - Sources: https://github.com/facebookresearch/sam3/blob/main/sam3/model_builder.py, https://github.com/facebookresearch/sam3/blob/main/examples/sam3.1_video_predictor_example.ipynb
- **Fine-tuning or training code:**
  - **SAM 3 image fine-tuning is supported.** `sam3/train/train.py` with Hydra configs (Roboflow-100VL full fine-tune, ODinW13) builds `build_sam3_image_model`, which by default downloads the SAM 3 checkpoint from `facebook/sam3`, not 3.1. The example config sets `gpus_per_node: 2` (https://github.com/facebookresearch/sam3/blob/main/README_TRAIN.md, https://github.com/facebookresearch/sam3/blob/main/sam3/train/configs/roboflow_v100/roboflow_v100_full_ft_100_images.yaml).
  - **SAM 3.1 fine-tuning has no official recipe.** No SAM 3.1 or multiplex training config exists in the repo tree.
  - `facebook/sam3` is also gated with manual approval (https://huggingface.co/api/models/facebook/sam3).
- **Minimum GPU: UNVERIFIED.** No official minimum VRAM is stated. What the sources do say:
  - Prerequisites: Python 3.12 or later, PyTorch 2.7 or later, a CUDA GPU with CUDA 12.6 or later. SAM 3 has 848M parameters. The ~7x speedup figure was measured on one H100 (https://github.com/facebookresearch/sam3, RELEASE_SAM3p1.md).
  - The SAM 3.1 builders default to `use_fa3=True`. The FA3 path imports `flash_attn_interface` and casts to `float8_e4m3fn` (https://github.com/facebookresearch/sam3/blob/main/sam3/perflib/fa3.py). FlashAttention-3 requires an H100/H800 and CUDA 12.3 or later (https://github.com/Dao-AILab/flash-attention).
  - **Inference from the code, not tested:** on an A100, or without FA3 installed, pass `use_fa3=False`.

## 7. Meta open-weight Muse models (Meta sources only)

- **Muse Spark Open**
  - What it is: 816B-parameter sparse MoE with 42B active, multimodal input, 1,048,576 context.
  - Checkpoints: BF16 (~1.65 TB, about 8×B300) and NVFP4 (~537 GB, one 4-GPU Blackwell node).
  - Licence and access: Muse Model License; the HF repos are gated with manual approval.
  - Sources: https://dev.meta.ai/docs/muse-spark-open, https://dev.meta.ai/docs/muse-spark-open/get-the-model, https://huggingface.co/api/models/meta-models/Muse-Spark-Open-816B-A42B
  - Hosted providers listed by Meta, with model strings:
    - Baseten: `meta-models/muse-spark-open` at `https://inference.baseten.co/v1`
    - Fireworks: `accounts/fireworks/models/muse-spark-open`
    - Also Together, Groq, Nebius, Modal and OpenRouter
    - Source: https://dev.meta.ai/docs/muse-spark-open/deploy
  - Hosted LoRA: Meta documents Fireworks serverless LoRA on `accounts/fireworks/models/muse-spark-open-nvfp4` (https://dev.meta.ai/docs/muse-spark-open/post-training).
- **Muse Glimmer**
  - What it is: 30B dense multimodal model (text and image in), distilled from Muse Spark, 128K context by default.
  - Licence and access: Apache 2.0, **not gated**.
  - Builds: bf16 ~60 GB; a Q4_K_M GGUF of ~17 GB that "fits under 24 GB VRAM".
  - Sources: https://dev.meta.ai/docs/muse-glimmer, https://dev.meta.ai/docs/muse-glimmer/get-the-model, https://huggingface.co/api/models/meta-models/Muse-Glimmer-30B
  - Post-training: Meta documents Axolotl (QLoRA verified on 1×H100) and TRL, both run on your own GPUs (https://dev.meta.ai/docs/muse-glimmer/post-training).
  - Hosted provider listed by Meta: only Together AI (https://dev.meta.ai/docs/muse-glimmer/deploy). Fireworks appears only in the "launch partners" list (https://dev.meta.ai/docs/muse-glimmer).
  - **Meta's docs do not describe a Fireworks LoRA for Glimmer.** The other agent is checking Fireworks directly.

## 8. Request examples

### 8a. Chat completion with JSON-schema output

Verbatim from https://dev.meta.ai/docs/structured-output:

```shell
curl -X POST "https://api.meta.ai/v1/chat/completions" \
  -H "Authorization: Bearer $MODEL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "model": "muse-spark-1.3",
  "messages": [
    {
      "role": "system",
      "content": "Extract the address from the user input into the specified JSON format."
    },
    {
      "role": "user",
      "content": "Please format this address: 1 Hacker Wy Menlo Park CA 94025"
    }
  ],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "Address",
      "schema": {
        "type": "object",
        "properties": {
          "street": {
            "type": "string"
          },
          "city": {
            "type": "string"
          },
          "state": {
            "type": "string",
            "description": "2-letter state abbreviation"
          },
          "zip": {
            "type": "string",
            "description": "5-digit zip code"
          }
        },
        "required": [
          "street",
          "city",
          "state",
          "zip"
        ]
      }
    }
  }
}'
```

The JSON string comes back in `choices[0].message.content`. On the Responses API, use `text: {format: {type: "json_schema", name, schema, strict}}` instead (https://dev.meta.ai/docs/api-reference/responses/schemas).

### 8b. Vision call with an image

Verbatim from https://dev.meta.ai/docs/image-understanding (Chat Completions, image URL):

```shell
curl -X POST "https://api.meta.ai/v1/chat/completions" \
  -H "Authorization: Bearer $MODEL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "model": "muse-spark-1.3",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "Describe what you see in this image."
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c9/Avocado_Hass_-_single_and_halved.jpg/1280px-Avocado_Hass_-_single_and_halved.jpg"
          }
        }
      ]
    }
  ]
}'
```

For a local file, the same page shows passing `f"data:image/jpeg;base64,{base64_image}"` as `image_url.url`. The cookbook uses `data:image/png;base64,...` the same way (https://dev.meta.ai/docs/cookbook/vision-input).

**Composed from two documented examples, not a single doc example:** a base64 PNG plot plus a JSON-schema verdict. The docs state that structured output combines with image understanding (https://dev.meta.ai/docs/structured-output).

```python
import base64, os
from openai import OpenAI

client = OpenAI(base_url="https://api.meta.ai/v1", api_key=os.environ["MODEL_API_KEY"])
png_b64 = base64.b64encode(open("plot.png", "rb").read()).decode()
resp = client.chat.completions.create(
    model="muse-spark-1.3",
    messages=[{"role": "user", "content": [
        {"type": "text", "text": "Does this plot support the claim? <claim JSON here>"},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{png_b64}"}},
    ]}],
    response_format={"type": "json_schema", "json_schema": {"name": "PlotVerdict", "strict": True, "schema": {
        "type": "object", "additionalProperties": False,
        "properties": {"direction_matches": {"type": "boolean"}, "outlier_driven": {"type": "boolean"},
                       "rationale": {"type": "string"}},
        "required": ["direction_matches", "outlier_driven", "rationale"]}}},
)
print(resp.choices[0].message.content)
```

### 8c. SAM 3.1 call

Verbatim from https://dev.meta.ai/docs/sam/segmenting (image, concept prompt, streaming):

```shell
curl -N -X POST "https://api.meta.ai/v1/responses" \
  -H "Authorization: Bearer $MODEL_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
  "model": "sam-3.1",
  "input": [
    {
      "type": "message",
      "role": "user",
      "content": [
        {
          "type": "input_text",
          "text": "glasses"
        },
        {
          "type": "input_image",
          "image_url": "https://example.com/photo.png"
        }
      ]
    }
  ],
  "stream": true
}'
```

Optional metadata, verbatim from the same page: `"metadata": { "include_confidence": "true" }` or `"metadata": { "mask_encoding": "one_bit" }`.

For video, swap in `{"type":"input_video","video_url":"https://example.com/clip.mp4"}` or `{"type":"input_video","file_id":"file-abc123"}`.

For a Python parser, see `segment_image()` and `stream_events()` in Meta's https://github.com/meta-models/meta-model-cookbook/blob/main/07_sam/01_api_basics/python/sam_api.py. It uses `openai.AsyncOpenAI` and `meta_sam_parser.parse_responses_stream(...)`.

### 8d. Transcription call

Verbatim from https://dev.meta.ai/docs/api-reference/voice/transcribe:

```shell
curl -X POST "https://api.meta.ai/v1/asr/transcribe" \
  -H "Authorization: Bearer $MODEL_API_KEY" \
  -H "Accept: application/json" \
  -F 'request={"model":"muse-voice-transcribe-1.0","audioEncoding":"WAV","mode":"PUSH_TO_TALK"};type=application/json' \
  -F "audio=@recording.wav;type=audio/wav"
```

Convert first, verbatim from https://dev.meta.ai/docs/speech-to-text: `ffmpeg -i input.m4a -ac 1 -ar 24000 -c:a pcm_s16le -map_metadata -1 output.wav`. The response JSON contains `sessionId`, `transcript`, `audioDurationMs` and `turns[]`.

## 9. Spec claims that conflict with the sources

| Spec claim (`spatialscout_prd_srs_spec.md`) | What the sources say |
|---|---|
| $150 Meta Model API credits | UNVERIFIED; not on the official event pages. |
| Fireworks AI $25 | The event page says Fireworks offers **$100** to select participants ([CV](https://cerebralvalley.ai/e/meta-ai-developer-hackathon)). |
| `POST /api/voice` accepts the audio blob for Muse Voice Transcribe | Only WAV (mono s16 PCM, 16 or 24 kHz) or raw PCM over WebSocket. Browser webm/opus must be transcoded server-side ([speech-to-text](https://dev.meta.ai/docs/speech-to-text)). |
| "SAM 3.1 Video Tracking API" | Same `/v1/responses` call with `input_video` ([segmenting](https://dev.meta.ai/docs/sam/segmenting)). |
| One SAM call for glomeruli and tubules | One concept per request: send two requests, or use box and point prompts ([segmenting](https://dev.meta.ai/docs/sam/segmenting)). |
| 16-tile "snake video" keeps object IDs across seams | The tiles must be encoded as MP4/MOV. Docs: IDs are stable "while the object stays in frame — don't rely on the id across an object's entry, exit, or full occlusion". Behaviour across tile jumps is UNVERIFIED; test it. Video tracks at most 16 objects per frame ([reading](https://dev.meta.ai/docs/sam/reading-segmentation), [segmenting](https://dev.meta.ai/docs/sam/segmenting)). |
| Seed SAM box prompts from Muse Spark boxes (FR-2.2 step 2) | Spark returns coordinates on a normalized 0-1000 grid ([image-understanding](https://dev.meta.ai/docs/image-understanding)). SAM prompts need media pixels, with `w`/`h` set to the media size. A `w`/`h` with the wrong aspect ratio returns 400 ([segmenting](https://dev.meta.ai/docs/sam/segmenting)). Convert the coordinates first. |
| SAM video at $0.20 per 1,000 frames | Correct, but a 16-frame clip is billed as 50 frames ([pricing](https://dev.meta.ai/docs/pricing-rate-limits)). |
| Meta API "Standard Mode" | Chosen by model ID; there is no request flag ([pricing](https://dev.meta.ai/docs/pricing-rate-limits)). |
| `muse-glimmer-lora` model string | Not a Meta ID. |
| Muse Glimmer LoRA on Fireworks | Meta documents Fireworks LoRA for Muse Spark Open NVFP4, not Glimmer. Glimmer fine-tuning in Meta's docs is self-run with Axolotl or TRL ([glimmer post-training](https://dev.meta.ai/docs/muse-glimmer/post-training)). |
| SAM 3.1 pathology head fine-tune on Modal | No SAM 3.1 training recipe exists. The official trainer fine-tunes the SAM 3 image model. Both checkpoints are gated with manual approval ([sam3 repo](https://github.com/facebookresearch/sam3)). |
| "Muse Code" sub-agents as a model | Muse Code is a CLI agent; its default model is `muse-spark-1.2` ([muse-code](https://dev.meta.ai/docs/muse-code)). |
| 100% of agent claims pass schema validation | Structured output is guaranteed by the decoder. Tool-call arguments are not guaranteed, and `tool_choice` accepts only `"auto"` ([tool-calling](https://dev.meta.ai/docs/tool-calling)). |
| Deterministic replay | `seed` is deprecated and not deterministic; SAM output "can vary slightly between runs". Cache responses ([chat-completions](https://dev.meta.ai/docs/protocols/chat-completions), [segmenting](https://dev.meta.ai/docs/sam/segmenting)). |
| Judging weights (25/25/20/…) | From reconscribe.com, a third-party site. The official criteria are qualitative ([event page](https://dev.meta.ai/events/global-hackathon)). |

## 10. Still UNVERIFIED

- The Meta Model API hackathon credit amount and how credits are applied.
- The official rules document and the numeric judging weights.
- Whether `sam-3.1` and `muse-wonder-1.0` are enabled for this team. Check with `GET /v1/models` once a key exists.
- Whether SAM 3.1 keeps object IDs across tile-seam "jumps" in a synthetic tile video.
- The minimum GPU or VRAM for SAM 3.1 open-weight inference, and whether the 3.1 checkpoint can be fine-tuned with the official trainer.
- SAM-specific image size or format limits. Only the general 50 MB inline limit and the image MIME list are documented.
