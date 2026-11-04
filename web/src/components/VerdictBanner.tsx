// The hypothesis verdict banner (revision 3): each sub-claim of the question with the verdict the frozen rule derived
// from its verified claims, always scoped to these sections and controls. It renders only computed verdicts.
import type { HypothesisVerdict } from "../contracts/generated";

const STYLES: Record<string, string> = {
  confirmed: "border-emerald-400/60 bg-emerald-400/10 text-emerald-200",
  refuted: "border-amber-400/60 bg-amber-400/10 text-amber-200",
  inconclusive: "border-line bg-raised text-ink-2",
};
const PREDICTION: Record<string, string> = {
  holds: "predicted to hold under stricter assignment",
  drops: "predicted to drop beyond random thinning",
};

export function VerdictBanner({ verdict, onClaim }: { verdict: HypothesisVerdict; onClaim?: (claimId: string) => void }) {
  return (
    <section aria-label="Hypothesis verdict" className="rounded-lg border border-line bg-panel p-3 text-sm">
      <h2 className="text-sm font-semibold text-ink">Hypothesis verdict</h2>
      <p className="mb-2 text-[11px] text-ink-3">{verdict.scope}</p>
      <ul className="space-y-2">
        {verdict.verdicts.map((v) => (
          <li key={v.sub_claim.text} data-testid="sub-claim-verdict" data-verdict={v.verdict} className="flex items-start gap-2">
            <span className={`mt-0.5 shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${STYLES[v.verdict] ?? ""}`}>
              {v.verdict}
            </span>
            <div className="min-w-0">
              <p className="text-ink">{v.sub_claim.text}</p>
              <p className="text-[11px] text-ink-3">
                {v.sub_claim.cell_type} · {v.sub_claim.genes.join("/")} · {PREDICTION[v.sub_claim.predicted]} · {v.dataset_id}
              </p>
              <p className="text-[11px] text-ink-2">
                {v.reason}
                {v.claim_ids.map((id) => (
                  <button key={id} type="button" onClick={() => onClaim?.(id)} className="ml-1 font-mono text-[10px] text-ink-3 underline hover:text-ink">
                    {id}
                  </button>
                ))}
              </p>
            </div>
          </li>
        ))}
      </ul>
      <details className="mt-2 text-[11px] text-ink-3">
        <summary className="cursor-pointer">Verdict rule</summary>
        {verdict.rule}
      </details>
    </section>
  );
}
