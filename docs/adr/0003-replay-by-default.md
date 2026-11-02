# The public URL plays a labelled replay; live mode is gated

The Meta Model API has no hard spend cap, the $150 hackathon credit lasts ten days and may lapse during judging (Nov 4–8), and judges reward a demo that "holds up live". So every model call is cached by a content hash of its request, whole investigations are recorded as event streams, and the public URL plays a recorded investigation by default, labelled as a replay. Live mode needs a passcode and stops at a daily spend budget enforced in the backend. Live and replayed runs use the same code path; only the model gateway's source of responses differs.

## Run modes and persisted state (amended Nov 2 after review)

Every investigation persists `state.json` (status, run mode, approved-plan hash) and `events.jsonl` (one event per line with a monotonic `seq` and its original `recorded_at_utc`), independent of any HTTP connection. Approval is idempotent, and clients reconnect with `after_seq`, which also carries long runs across Modal's 150-second request limit. Three run modes are always labelled: `immutable_replay` streams recorded events verbatim with their original timestamps; `cached_tool_rerun` re-executes the deterministic tools with stored model responses, keyed by provider, model, inputs, schema version, tool version and artifact checksum; `live` makes fresh calls under a file-locked daily budget reservation.

## Consequences

- Model responses are not deterministic (Meta deprecated `seed`; SAM results "can vary slightly"), so reproducibility comes from stored responses, not reruns.
- The audit log records whether each model response was live or replayed.
