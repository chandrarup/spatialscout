# Golden path anchor

The demo's golden path is one live investigation, recorded on 2026-11-04 at 02:53:50 UTC and replayed verbatim by the public URL (immutable replay). This file anchors its audit log outside the log itself: if any entry of the recorded log changes, its hash chain no longer ends at these hashes.

| Field | Value |
| --- | --- |
| Recording | `fixtures/recordings/gse286184-two-part-hypothesis/` (origin `live`, nothing retried or edited) |
| Investigation | `inv-22e74f687b16` |
| Question | "My hypothesis: the podocytes this atlas calls 'endocytic' really carry LRP2, and the UMOD seen in B cells is spillover from neighbouring thick ascending limb cells. Does each part hold up under stricter assignment?" |
| Audit log | 42 entries; head hash `593c557c66bd714ffdda42124f8f92fb41f6263b4779bdd8b09c01aa285651a1` (entry 42, `package_exported`) |
| Evidence package | `pkg-2ee010516003`; its manifest records the head hash at export, `d5e55048600b2b2b37f53e56920905a8768cc4ffb18ad4253791e740e0116579` (entry 41) |
| Model calls | 18, estimated $0.29 at list prices, 167 s of model latency, 179 s from plan to package |

Check it:

```bash
uv run python -c "from spatialscout.audit import verify_chain; print(verify_chain(open('fixtures/recordings/gse286184-two-part-hypothesis/investigation/audit_log.jsonl').read()))"
```

The second recorded live run, `fixtures/recordings/gse286184-hero-lrp2-cubn/` (the spec's hero question, `inv-9d567ce7bd9d`), is replayable too.
