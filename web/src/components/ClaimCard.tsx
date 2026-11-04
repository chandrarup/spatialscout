// The claim card: the sentence, every number it cites with its source field, and its three separate statuses.
// It names the controls the agent ran for the claim's finding, or says none ran: nothing runs a control for the agent.
// The verification panel shows each check's recorded result and reasons. "Challenge the verifier" swaps in one of the
// claim's recorded injected variants, named only by its error kind, with its recorded verification: the diff and the
// actual outcome, misses included. Nothing is recomputed and no model is called. The review buttons record the
// researcher's decision on this claim version in the audit log.
import { useEffect, useState } from "react";
import { api } from "../api";
import type { Claim, ClaimChallenge, ClaimChallenges, FieldChange, ReviewRequest, VerificationResult } from "../contracts/generated";

interface Props {
  claim: Claim;
  verification?: VerificationResult;
  investigationId?: string;
  /** Record a review decision; absent when the claim cannot be reviewed (an injected variant, a recorded replay). */
  onReview?: (decision: ReviewRequest["decision"]) => Promise<void>;
}

const DECISIONS: [ReviewRequest["decision"], string][] = [
  ["accepted_for_follow_up", "Accept for follow-up"],
  ["needs_investigation", "Needs investigation"],
  ["unresolved", "Unresolved"],
];

export function ClaimCard({ claim, verification, investigationId, onReview }: Props) {
  const [reviewing, setReviewing] = useState(false);
  const [reviewProblem, setReviewProblem] = useState<string | null>(null);
  const [challenges, setChallenges] = useState<ClaimChallenges | null>(null);
  const [chosen, setChosen] = useState<string>("");

  useEffect(() => {
    if (!investigationId || !verification || claim.injected.is_injected) return;
    let live = true;
    api
      .claimChallenges(investigationId, claim.claim_id)
      .then((loaded) => live && setChallenges(loaded))
      .catch(() => live && setChallenges(null));
    return () => {
      live = false;
    };
  }, [investigationId, claim.claim_id, claim.injected.is_injected, verification]);

  const variant: ClaimChallenge | undefined = challenges?.variants.find((v) => v.kind === chosen);
  const shown = variant ? variant.claim : claim;
  const shownVerification = variant ? variant.verification : verification;

  return (
    <article id={`claim-${claim.claim_id}`} aria-label={`Claim ${claim.claim_id}`} className="rounded-lg border border-line bg-panel p-4">
      <header className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-ink">Claim</h2>
        <span className="font-mono text-xs text-ink-3">
          {shown.claim_id} · v{shown.version}
        </span>
      </header>
      {challenges && challenges.variants.length > 0 && (
        <label className="mb-2 flex flex-wrap items-center gap-2 text-xs text-ink-2">
          Challenge the verifier
          <select
            className="rounded border border-line bg-raised px-2 py-1 text-xs text-ink"
            value={chosen}
            onChange={(event) => setChosen(event.target.value)}
          >
            <option value="">Original claim</option>
            {challenges.variants.map((v) => (
              <option key={v.kind} value={v.kind}>
                {kindLabel(v.kind)}
              </option>
            ))}
          </select>
        </label>
      )}
      {shown.injected.is_injected && (
        <p className="mb-2 rounded bg-red-500/15 px-2 py-1 text-xs font-medium text-red-300">
          Injected error ({kindLabel(shown.injected.kind ?? "")}): deliberately altered to test verification
        </p>
      )}
      <p className="mb-3 text-sm leading-relaxed text-ink">{shown.text}</p>
      <div className="mb-3 flex flex-wrap gap-1.5">
        <Status label="Evidence" value={shown.evidence_status} />
        <Status label="Verification" value={shown.verification_status} />
        <Status label="Review" value={shown.review_status} />
      </div>
      {onReview && !variant && (
        <div className="mb-3 flex flex-wrap items-center gap-1.5 text-xs" role="group" aria-label="Review decision">
          <span className="text-ink-3">Review</span>
          {DECISIONS.map(([decision, label]) => (
            <button
              key={decision}
              type="button"
              disabled={reviewing}
              aria-pressed={claim.review_status === decision}
              onClick={() => {
                setReviewing(true);
                setReviewProblem(null);
                onReview(decision)
                  .catch((e: unknown) => setReviewProblem(String(e)))
                  .finally(() => setReviewing(false));
              }}
              className={`rounded border px-2 py-0.5 ${claim.review_status === decision ? "border-accent bg-accent/20 text-ink" : "border-line text-ink-2 hover:text-ink"}`}
            >
              {label}
            </button>
          ))}
          {reviewProblem && <span className="text-red-300">{reviewProblem}</span>}
        </div>
      )}
      {variant && <ChallengeOutcome variant={variant} />}
      {shownVerification && <VerificationPanel verification={shownVerification} />}
      <dl className="mb-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
        <dt className="text-ink-3">Random-thinning control</dt>
        <dd className="font-mono text-ink-2">{shown.controls.random_thinning ?? <span className="font-sans text-ink-3">none: the agent did not run one</span>}</dd>
        <dt className="text-ink-3">Label-sensitivity check</dt>
        <dd className="font-mono text-ink-2">{shown.controls.label_sensitivity ?? <span className="font-sans text-ink-3">none: the agent did not run one</span>}</dd>
      </dl>
      <table className="w-full text-xs">
        <caption className="mb-1 text-left text-ink-3">
          Cited numbers, from {shown.finding.finding_kind} result <span className="font-mono">{shown.finding.finding_id}</span>
        </caption>
        <tbody>
          {Object.entries(shown.cited).map(([name, number]) => (
            <tr key={name} className="border-t border-line">
              <th scope="row" className="py-1 pr-2 text-left font-normal text-ink-2">
                {name.replaceAll("_", " ")}
              </th>
              <td className="py-1 pr-2 text-right font-mono text-ink">{formatNumber(number.value)}</td>
              <td className="py-1 font-mono text-ink-3">{number.source}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </article>
  );
}

function ChallengeOutcome({ variant }: { variant: ClaimChallenge }) {
  return (
    <section aria-label="Recorded outcome of the injected error" className="mb-3 rounded border border-line bg-raised p-2 text-xs">
      <h3 className="mb-1 font-semibold text-ink">What the injected error changed</h3>
      {variant.changes.length === 0 ? (
        <p className="text-ink-3">Nothing: the original claim had nothing this kind of error could alter.</p>
      ) : (
        <ul className="mb-2 space-y-1">
          {variant.changes.map((change) => (
            <li key={change.field}>
              <span className="font-mono text-ink-2">{change.field}</span>: <Value change={change} side="before" /> →{" "}
              <Value change={change} side="after" />
            </li>
          ))}
        </ul>
      )}
      <h3 className="mb-1 font-semibold text-ink">Recorded outcome: {variant.verification.verification_status.replaceAll("_", " ")}</h3>
      {variant.detected ? (
        <ul className="list-disc pl-4 text-ink-2">
          {variant.new_reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      ) : (
        <p className="text-amber-300">Missed: no check found a problem the original claim did not already have.</p>
      )}
    </section>
  );
}

function Value({ change, side }: { change: FieldChange; side: "before" | "after" }) {
  const value: unknown = change[side];
  const text = value === null || value === undefined ? "none" : typeof value === "object" ? JSON.stringify(value) : String(value);
  return <span className={side === "before" ? "text-ink-3 line-through" : "text-ink"}>{text}</span>;
}

function VerificationPanel({ verification }: { verification: VerificationResult }) {
  return (
    <section aria-label="Verification" className="mb-3 text-xs">
      {!verification.in_validated_summary && (
        <p className="mb-1 text-red-300">Blocked from the validated summary; kept in history.</p>
      )}
      <ul className="space-y-1">
        {verification.checks.map((check) => (
          <li key={check.kind}>
            <span className="text-ink-3">{check.kind}: </span>
            <span className="text-ink">{check.status}</span>
            {check.reasons.length > 0 && (
              <ul className="list-disc pl-4 text-ink-2">
                {check.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            )}
            {check.reasons.length === 0 && check.kind === "visual" && <span className="text-ink-2"> · {check.details}</span>}
          </li>
        ))}
      </ul>
    </section>
  );
}

function kindLabel(kind: string): string {
  return kind.replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase());
}

function Status({ label, value }: { label: string; value: string }) {
  return (
    <span className="rounded border border-line bg-raised px-2 py-0.5 text-xs">
      <span className="text-ink-3">{label}: </span>
      <span className="text-ink">{value.replaceAll("_", " ")}</span>
    </span>
  );
}

function formatNumber(value: number | null): string {
  if (value === null) return "missing";
  return Number.isInteger(value) ? String(value) : value.toFixed(3);
}
