// The plan stepper: what will run, each step's progress, any plan the validator rejected (with the reason), and the
// Approve and Reject buttons. Approving freezes the plan; its hash is shown once approved.
import type { InvestigationEvent, InvestigationStatus, Plan, PlanRejectedEvent } from "../contracts/generated";

interface Props {
  plan: Plan | null;
  events: InvestigationEvent[];
  status: InvestigationStatus;
  busy: boolean;
  onApprove: () => void;
  onReject: () => void;
}

type StepState = "waiting" | "running" | "done" | "failed";

function stepStates(events: InvestigationEvent[]): Map<string, StepState> {
  const states = new Map<string, StepState>();
  for (const event of events) {
    if (event.type === "tool_started") states.set(event.step_id, "running");
    else if (event.type === "tool_finished") states.set(event.step_id, "done");
    else if (event.type === "tool_failed") states.set(event.step_id, "failed");
  }
  return states;
}

const MARK: Record<StepState, { glyph: string; style: string; label: string }> = {
  waiting: { glyph: "○", style: "text-ink-3", label: "waiting" },
  running: { glyph: "◐", style: "text-accent", label: "running" },
  done: { glyph: "●", style: "text-emerald-400", label: "done" },
  failed: { glyph: "✕", style: "text-red-400", label: "failed" },
};

export function PlanCard({ plan, events, status, busy, onApprove, onReject }: Props) {
  const rejections = events.filter((e): e is PlanRejectedEvent => e.type === "plan_rejected" && e.by === "validator");
  if (!plan && rejections.length === 0) return null;
  const states = stepStates(events);
  const awaiting = status === "awaiting_approval" && plan !== null;
  return (
    <section aria-labelledby="plan-title" className="rounded-lg border border-line bg-panel p-4">
      <header className="mb-2 flex items-baseline justify-between gap-2">
        <h2 id="plan-title" className="text-sm font-semibold text-ink">
          Plan
        </h2>
        {plan && <span className="text-xs text-ink-3">proposed by {plan.proposed_by}</span>}
      </header>
      {rejections.map((r) => (
        <p key={r.seq} className="mb-2 rounded border border-amber-500/40 bg-amber-500/10 px-2 py-1.5 text-xs text-amber-200">
          {r.attempt === 1 ? "First proposal" : "Re-plan"} rejected ({r.tools.join(", ") || "no tools"}): {r.reason}
        </p>
      ))}
      {plan && (
        <>
          <p className="mb-3 text-sm text-ink-2">{plan.summary}</p>
          <dl className="mb-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
            <dt className="text-ink-3">Contrast</dt>
            <dd className="text-ink-2">{plan.contrast ? `${plan.contrast.disease} vs ${plan.contrast.control}` : "none (audit only)"}</dd>
            <dt className="text-ink-3">Cell types</dt>
            <dd className="text-ink-2">{plan.cell_types.join(", ")}</dd>
            <dt className="text-ink-3">Conditions</dt>
            <dd className="text-ink-2">{plan.conditions.map((c) => c.replaceAll("_", "-")).join(", ")}</dd>
            <dt className="text-ink-3">Budget</dt>
            <dd className="text-ink-2">{plan.budget.max_tool_calls} tool calls, follow-ups included</dd>
          </dl>
          <ol className="mb-3 space-y-2">
            {plan.steps.map((step, index) => {
              const state = MARK[states.get(step.step_id) ?? "waiting"];
              return (
                <li key={step.step_id} className="flex gap-2 rounded border border-line bg-raised p-2 text-xs">
                  <span aria-label={state.label} className={`mt-px ${state.style}`}>
                    {state.glyph}
                  </span>
                  <div className="min-w-0">
                    <div className="font-mono text-ink">
                      {index + 1}. {step.tool}
                    </div>
                    <div className="mt-0.5 break-all font-mono text-ink-3">{JSON.stringify(step.arguments)}</div>
                    <div className="mt-1 text-ink-2">{step.rationale}</div>
                  </div>
                </li>
              );
            })}
          </ol>
          <p className="mb-3 text-xs text-ink-3">
            Controls are not plan steps: after each result, the agent decides which controls it needs.
          </p>
        </>
      )}
      {awaiting ? (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onApprove}
            disabled={busy}
            className="flex-1 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            Approve plan
          </button>
          <button
            type="button"
            onClick={onReject}
            disabled={busy}
            className="rounded-md border border-line px-4 py-2 text-sm text-ink-2 hover:bg-raised disabled:opacity-50"
          >
            Reject
          </button>
        </div>
      ) : plan?.status === "approved" ? (
        <p className="text-xs text-ink-2">
          Approved and frozen · plan hash <span className="font-mono">{plan.plan_hash?.slice(0, 12)}</span>
        </p>
      ) : plan?.status === "rejected" ? (
        <p className="text-xs text-ink-2">Rejected by the researcher; nothing ran.</p>
      ) : null}
    </section>
  );
}
