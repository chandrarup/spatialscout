# Review response: traceability (Nov 2 2026)

How spec and ticket revision 2 answer the reviewer's audit (`reviews/plan-review.md`) and the agent directive (`reviews/agent-directive-winning-upgrades.md`). The directive's Section 4 is adopted; the right-hand column lists where it was corrected to stay within ADR-0001–0007.

| Source | Requirement | Adopted | Correction |
| --- | --- | --- | --- |
| Reviewer 1 | Donor independence gates inference | Contrasts are descriptive only; IgAN vs Control recorded as "conditionally donor-distinct by published counts, unconfirmed"; donors never inferred from expression; PyDESeq2 off the primary path (ADR-0007) | The directive omits this point and still runs section-level PyDESeq2 with leave-one-section-out |
| Reviewer 2, directive 2.1 | Separate evidence types; label circularity | `Finding` is a union of audit result and contrast result; NPHS1-anchored podocyte rule that does not use LRP2/CUBN | Not "zero circularity": the anchored rule can admit tubule cells carrying stray NPHS1, so both label rules are reported (label-sensitivity check) and that check is a required control. The panel has no NPHS2, PODXL or WT1. Claim wording is population-scoped |
| Reviewer 3, directive 2.2 | Unblock the critical path | 09a runs on audit results after 03 + 05; 09b adds contrasts after 06; 07 and 08 never gate 12; click review without voice | Sensitive findings are shown only if the pipeline produces them |
| Reviewer 4, directive 2.3 | SAM out of primary labels | Exploratory condition, badged "SAM 3.1 proposal (exploratory)", visible in table, slider and figures (ADR-0006) | Added: seed-box and convex-hull baselines; coverage and retention beside enrichment; empty or rejected proposals allowed; mask version and run id; a test that the exploratory condition changes no label |
| Reviewer 5, directive 2.4 | Tighter sensitivity rules; random-thinning control | Closed-form cell-matched thinning expectation and excess drop | Added a home-matched expectation, because nuclear fraction varies by gene (UMOD in TAL 0.34 vs NPHS1 in podocytes 0.75), so cytoplasmic genes would otherwise look admixed; fixed populations; the hero measure's own expectation; one frozen rule set (gate precedence, ±0.1 near-zero band, at least two valid primary conditions, leave-one-section-out across all of them); the spike's 0.2 threshold retired |
| Reviewer 6, directive 2.5 | Persisted state, honest replay | `state.json` + `events.jsonl` with `seq`; idempotent approval; `after_seq` reconnect; three run modes; cache key with tool version and artifact checksum; file-locked budget (ADR-0003 amended) | Added seam-2 tests: refresh at approval, duplicate approval, reconnect mid-run, concurrent budget reservations |
| Directive upgrade 1 | Agent-chosen controls | Muse Spark 1.3 requests the thinning control and the label-sensitivity check, citing the observation | The verifier fails a claim missing a required control; the orchestrator never runs controls on the agent's behalf, so the agent's choice carries weight |
| Directive upgrade 2 | Two-panel vision check | Composite figure: per-section panel plus tissue crop; Spark 1.3 checks both | Panel B no longer asks whether excluded molecules lie outside the nucleus, which nucleus-only guarantees by construction. It asks whether the crop shows the neighbour pattern the claim states, backed by the computed neighbour-proximity share for excluded vs retained molecules. New injected error kind "misstated spatial pattern" measures whether Panel B can disagree |
| Directive upgrade 3 | Challenge the verifier | Recorded injected variants per hero claim, swapped in under 100 ms at no model cost | Options are named by error kind only; the UI shows the recorded outcome, including misses, never a predicted one |
| Directive upgrade 4 | Fly to evidence | Ranked 150 µm evidence regions; about 800 ms fly-to with gene filter locked | Ranking rule shown on screen; ranks 2 and 3 browsable, so the top region does not read as cherry-picked |
| ADR-0001 | Computed numbers only | All new measures are computed | Removed the directive's predicted outcomes (UMOD in B cells "drops far below", LRP2/CUBN "≈"); tickets 05 and 12 now say no outcome is written in advance |
| ADR-0002 | Flag-derived conditions | Unchanged | Integer counts are an input format, not statistical validity (wording fixed) |
| ADR-0004 | Single Modal deployable | Investigation state on a Modal Volume, one web container | |
| ADR-0005 | SAM box prompts | Still the method | Scope narrowed by ADR-0006 |
| Reviewer cleanup | Supersede the old PRD; reconcile notes; freeze marker pairs; state recompute scope; qualify the hash chain | PRD banner added; research notes corrected; pairs frozen from GSE271188 (`docs/research/marker-pairs.md`); recompute covers every cited number; head hash exported and the golden path's committed | |

## What the agent and vision now do that a dashboard cannot

- **Choosing controls.** Muse Spark 1.3 reads an observation and chooses the control it needs (random thinning, label sensitivity), citing why. Verification enforces that it chose correctly.
- **Two-panel vision check.** Muse Spark 1.3 checks one claim against a statistical chart and a sub-cellular tissue crop together.
- **Challenge the verifier.** Judges can probe the verifier themselves with recorded injected errors.
- **Planning and drafting.** Muse Wonder plans within the capability report, Muse Spark Open drafts claims in parallel, and SAM 3.1 outlines glomeruli on an image made from RNA.
