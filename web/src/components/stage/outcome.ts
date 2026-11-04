// The measured behaviour of a sub-claim, from its verified claim's evidence label (frozen rule), in words a
// non-specialist can read. The recorded verdict (confirmed/refuted/inconclusive) is shown separately as the
// prediction check.
import type { Claim, SubClaimVerdict } from "../../contracts/generated";

export interface Outcome {
  title: string;
  tone: string;
  ring: string;
}

export const MORE_EVIDENCE: Outcome = { title: "More evidence needed", tone: "text-ink-2", ring: "ring-line" };

const OUTCOME: Record<string, Outcome> = {
  stable: { title: "Signal persists under tested rules", tone: "text-stable", ring: "ring-stable/40" },
  segmentation_sensitive: { title: "Sensitive to assignment choices", tone: "text-sensitive", ring: "ring-sensitive/40" },
  insufficient_evidence: MORE_EVIDENCE,
};

export function claimOf(v: SubClaimVerdict, claims: Claim[]): Claim | undefined {
  return v.claim_ids.map((id) => claims.find((c) => c.claim_id === id)).find(Boolean);
}

export function outcomeOf(claim: Claim | undefined): Outcome {
  return (claim && OUTCOME[claim.evidence_status]) ?? MORE_EVIDENCE;
}
