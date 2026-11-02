// The plan card: what will run, and the Approve button that freezes it. Ticket 09a turns it into a stepper.
import type { InvestigationStatus, Plan } from "../contracts/generated";

interface Props {
  plan: Plan;
  status: InvestigationStatus;
  approving: boolean;
  onApprove: () => void;
}

export function PlanCard({ plan, status, approving, onApprove }: Props) {
  const awaiting = status === "awaiting_approval";
  return (
    <section aria-labelledby="plan-title" className="rounded-lg border border-line bg-panel p-4">
      <header className="mb-2 flex items-baseline justify-between gap-2">
        <h2 id="plan-title" className="text-sm font-semibold text-ink">
          Plan
        </h2>
        <span className="text-xs text-ink-3">proposed by {plan.proposed_by}</span>
      </header>
      <p className="mb-3 text-sm text-ink-2">{plan.summary}</p>
      <dl className="mb-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
        <dt className="text-ink-3">Contrast</dt>
        <dd className="text-ink-2">{plan.contrast ? `${plan.contrast.disease} vs ${plan.contrast.control}` : "none (audit only)"}</dd>
        <dt className="text-ink-3">Cell types</dt>
        <dd className="text-ink-2">{plan.cell_types.join(", ")}</dd>
        <dt className="text-ink-3">Conditions</dt>
        <dd className="text-ink-2">{plan.conditions.map((c) => c.replace("_", "-")).join(", ")}</dd>
        <dt className="text-ink-3">Budget</dt>
        <dd className="text-ink-2">{plan.budget.max_tool_calls} tool calls</dd>
      </dl>
      <ol className="mb-3 space-y-2">
        {plan.steps.map((step) => (
          <li key={step.step_id} className="rounded border border-line bg-raised p-2 text-xs">
            <div className="font-mono text-ink">{step.tool}</div>
            <div className="mt-0.5 break-all font-mono text-ink-3">{JSON.stringify(step.arguments)}</div>
            <div className="mt-1 text-ink-2">{step.rationale}</div>
          </li>
        ))}
      </ol>
      {awaiting ? (
        <button
          type="button"
          onClick={onApprove}
          disabled={approving}
          className="w-full rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {approving ? "Approving…" : "Approve plan"}
        </button>
      ) : (
        plan.status === "approved" && (
          <p className="text-xs text-ink-2">
            Approved and frozen · plan hash <span className="font-mono">{plan.plan_hash?.slice(0, 12)}</span>
          </p>
        )
      )}
    </section>
  );
}
