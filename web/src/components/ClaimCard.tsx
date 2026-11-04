// The claim card: the sentence, every number it cites with its source field, and its three separate statuses.
// It names the controls the agent ran for the claim's finding, or says none ran: nothing runs a control for the agent.
// Ticket 10 adds the verification panel; ticket 11 adds review controls.
import type { Claim } from "../contracts/generated";

export function ClaimCard({ claim }: { claim: Claim }) {
  return (
    <article aria-label={`Claim ${claim.claim_id}`} className="rounded-lg border border-line bg-panel p-4">
      <header className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-ink">Claim</h2>
        <span className="font-mono text-xs text-ink-3">
          {claim.claim_id} · v{claim.version}
        </span>
      </header>
      {claim.injected.is_injected && (
        <p className="mb-2 rounded bg-red-500/15 px-2 py-1 text-xs font-medium text-red-300">
          Injected error ({claim.injected.kind}): deliberately altered to test verification
        </p>
      )}
      <p className="mb-3 text-sm leading-relaxed text-ink">{claim.text}</p>
      <div className="mb-3 flex flex-wrap gap-1.5">
        <Status label="Evidence" value={claim.evidence_status} />
        <Status label="Verification" value={claim.verification_status} />
        <Status label="Review" value={claim.review_status} />
      </div>
      <dl className="mb-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
        <dt className="text-ink-3">Random-thinning control</dt>
        <dd className="font-mono text-ink-2">{claim.controls.random_thinning ?? <span className="font-sans text-ink-3">none: the agent did not run one</span>}</dd>
        <dt className="text-ink-3">Label-sensitivity check</dt>
        <dd className="font-mono text-ink-2">{claim.controls.label_sensitivity ?? <span className="font-sans text-ink-3">none: the agent did not run one</span>}</dd>
      </dl>
      <table className="w-full text-xs">
        <caption className="mb-1 text-left text-ink-3">
          Cited numbers, from {claim.finding.finding_kind} result <span className="font-mono">{claim.finding.finding_id}</span>
        </caption>
        <tbody>
          {Object.entries(claim.cited).map(([name, number]) => (
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
