// What the researcher delegated, counted from the run's events and its lab record: analyses, executed and rejected
// controls, verified claims, the injected error the verifier caught, protein checks, literature read and figures.
// Recorded execution time, lab time, model cost and playback are kept apart; the researcher's part is one plan approval.
import type { InvestigationEvent, LabRun } from "../../contracts/generated";

function seconds(ms: number): string {
  return ms >= 60_000 ? `${Math.floor(ms / 60_000)} min ${Math.round((ms % 60_000) / 1000)} s` : `${Math.round(ms / 1000)} s`;
}

function span(times: string[]): number {
  const t = times.map((x) => Date.parse(x)).filter(Number.isFinite);
  return t.length ? Math.max(...t) - Math.min(...t) : 0;
}

function open(label: string) {
  const target = document.querySelector<HTMLElement>(`[aria-label="${label}"]`);
  if (!target) return;
  if (target instanceof HTMLDetailsElement) target.open = true;
  target.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
}

export function WorkSummary({ events, lab }: { events: InvestigationEvent[]; lab: LabRun | null }) {
  const finished = events.flatMap((e) => (e.type === "tool_finished" ? [e.tool] : []));
  const analyses = finished.filter((t) => t === "audit_population").length;
  const controls = finished.length - analyses;
  const rejected = events.flatMap((e) => (e.type === "agent_decision" ? e.requests.filter((r) => r.status !== "accepted") : [])).length;
  const verified = events.filter((e) => e.type === "claim_verified" && !e.claim.injected.is_injected && e.verification.verification_status === "verified").length;
  const caught = events.filter((e) => e.type === "claim_verified" && e.claim.injected.is_injected && e.verification.verification_status === "failed").length;
  const calls = events.flatMap((e) => (e.type === "model_call" ? [e.call] : []));
  const cost = calls.reduce((sum, c) => sum + (c.estimated_cost_usd ?? 0), 0);
  const runMs = span(events.map((e) => e.recorded_at_utc));

  const labCalls = lab ? lab.events.flatMap((e) => (e.type === "model_call" && e.call ? [e.call] : [])) : [];
  const labCost = labCalls.reduce((sum, c) => sum + (c.estimated_cost_usd ?? 0), 0);
  const labMs = lab ? Date.parse(lab.finished_at_utc) - Date.parse(lab.started_at_utc) : 0;
  const records = lab ? lab.literature.reduce((n, l) => n + l.records.length, 0) : 0;

  const items: { n: number | string; what: string; target: string }[] = [
    { n: analyses, what: `analys${analyses === 1 ? "is" : "es"} run on the RNA sections`, target: "Hypothesis verdict" },
    { n: controls, what: `control${controls === 1 ? "" : "s"} executed, each requested by the agent citing an earlier result`, target: "Checked claims" },
    { n: verified, what: `claim${verified === 1 ? "" : "s"} verified (structure, every number recomputed, figure read)`, target: "Checked claims" },
    { n: caught, what: `deliberately wrong claim${caught === 1 ? "" : "s"} caught by the verifier`, target: "Checked claims" },
  ];
  if (lab) {
    items.push(
      { n: lab.protein.length, what: `protein cross-check${lab.protein.length === 1 ? "" : "s"} on separate KPMP specimens`, target: "Lab" },
      { n: records, what: `literature titles and abstracts read; every citation checked against what was fetched`, target: "Lab" },
      { n: lab.figures.length, what: `journal-width figure${lab.figures.length === 1 ? "" : "s"} (SVG and PDF)`, target: "Lab" },
    );
  }

  return (
    <section aria-label="Work delegated" className="rounded-3xl bg-panel p-6">
      <h2 className="text-[20px] font-semibold tracking-tight">Work delegated</h2>
      <p className="mt-1 text-[13px] text-ink-3">Counted from this run's recorded events{lab ? " and its lab record" : ""}. Each line opens its output.</p>
      <ul className="mt-4 grid grid-cols-1 gap-2 md:grid-cols-2">
        {items.map((item) => (
          <li key={item.what}>
            <button type="button" onClick={() => open(item.target)} className="flex w-full items-baseline gap-3 rounded-2xl bg-raised px-4 py-3 text-left transition-colors hover:bg-[#2a2d32]">
              <span className="text-[24px] leading-none font-semibold tabular-nums">{item.n}</span>
              <span className="text-[14px] leading-snug text-ink-2">{item.what}</span>
            </button>
          </li>
        ))}
      </ul>
      {rejected > 0 && <p className="mt-3 text-[12px] text-ink-3">{rejected} further request{rejected === 1 ? " was" : "s were"} rejected by the registry check and not run.</p>}
      {!lab && <p className="mt-3 text-[12px] text-ink-3">The lab (protein cross-check, literature, figures) has not run for this investigation yet.</p>}
      <dl className="mt-5 grid grid-cols-2 gap-4 border-t border-line pt-4 md:grid-cols-4">
        <div>
          <dt className="text-[12px] text-ink-3">Recorded execution time</dt>
          <dd className="text-[18px] font-semibold">{seconds(runMs)}</dd>
          <dd className="text-[11px] text-ink-3">plan to evidence package</dd>
        </div>
        <div>
          <dt className="text-[12px] text-ink-3">Lab execution time</dt>
          <dd className="text-[18px] font-semibold">{lab ? seconds(labMs) : "–"}</dd>
          <dd className="text-[11px] text-ink-3">sub-agents in parallel</dd>
        </div>
        <div>
          <dt className="text-[12px] text-ink-3">Estimated model cost</dt>
          <dd className="text-[18px] font-semibold">${(cost + labCost).toFixed(2)}</dd>
          <dd className="text-[11px] text-ink-3">
            {calls.length + labCalls.length} model calls{lab ? `, lab $${labCost.toFixed(2)}` : ""}
          </dd>
        </div>
        <div>
          <dt className="text-[12px] text-ink-3">Your hands-on work</dt>
          <dd className="text-[18px] font-semibold">1 approval click</dd>
          <dd className="text-[11px] text-ink-3">approve the plan; the run does the rest</dd>
        </div>
      </dl>
      <p className="mt-3 text-[11px] text-ink-3">Playback on screen is compressed and is not the execution time.</p>
    </section>
  );
}
