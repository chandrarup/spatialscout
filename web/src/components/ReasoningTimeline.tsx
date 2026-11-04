// The agent's reasoning as it happens: each observation, what Muse Spark 1.3 read in it, the follow-ups it chose
// (with the observation each one cites and why), and each follow-up's own result. Everything shown comes from events.
import type {
  AgentDecisionEvent,
  BudgetExhaustedEvent,
  FollowUpRequest,
  InvestigationEvent,
  ToolFailedEvent,
  ToolFinishedEvent,
  ToolStartedEvent,
} from "../contracts/generated";

interface Observation {
  id: string;
  started: ToolStartedEvent;
  finished: ToolFinishedEvent | null;
  failed: ToolFailedEvent | null;
  decision: AgentDecisionEvent | null;
}

function observations(events: InvestigationEvent[]): Observation[] {
  const byId = new Map<string, Observation>();
  for (const event of events) {
    if (event.type === "tool_started" && event.observation_id) {
      byId.set(event.observation_id, { id: event.observation_id, started: event, finished: null, failed: null, decision: null });
    } else if (event.type === "tool_finished" && event.observation_id) {
      const o = byId.get(event.observation_id);
      if (o) o.finished = event;
    } else if (event.type === "tool_failed") {
      const o = byId.get(event.observation_id);
      if (o) o.failed = event;
    } else if (event.type === "agent_decision") {
      const o = byId.get(event.observation_id);
      if (o) o.decision = event;
    }
  }
  return [...byId.values()];
}

const STATUS_STYLE: Record<FollowUpRequest["status"], string> = {
  accepted: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  rejected: "border-red-500/40 bg-red-500/10 text-red-300",
  over_budget: "border-amber-500/40 bg-amber-500/10 text-amber-300",
};

export function ReasoningTimeline({ events }: { events: InvestigationEvent[] }) {
  const items = observations(events);
  const exhausted = events.find((e): e is BudgetExhaustedEvent => e.type === "budget_exhausted");
  const lastDecision = [...events].reverse().find((e): e is AgentDecisionEvent => e.type === "agent_decision");
  if (items.length === 0) return null;
  return (
    <section aria-labelledby="reasoning-title" className="rounded-lg border border-line bg-panel p-4">
      <header className="mb-3 flex items-baseline justify-between gap-2">
        <h2 id="reasoning-title" className="text-sm font-semibold text-ink">
          Agent reasoning
        </h2>
        {lastDecision && (
          <span className="text-xs text-ink-3">
            {items.length} of {lastDecision.max_tool_calls} tool calls used
          </span>
        )}
      </header>
      <ol aria-live="polite" className="space-y-3">
        {items.map((o) => (
          <li key={o.id} className="rounded border border-line bg-raised p-3 text-xs">
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
              <span className="font-mono font-medium text-ink">{o.id}</span>
              <span className="font-mono text-ink-2">{o.started.tool}</span>
              <span className="text-ink-3">{o.started.request_id ? `follow-up ${o.started.request_id}` : `plan ${o.started.step_id}`}</span>
              {o.finished?.label && (
                <span className="rounded border border-line px-1.5 py-0.5 text-ink-2">{o.finished.label.replaceAll("_", " ")}</span>
              )}
            </div>
            {o.started.cites_observation_id && (
              <p className="mt-1 text-ink-2">
                <span className="text-ink-3">Chosen after </span>
                <span className="font-mono">{o.started.cites_observation_id}</span>
                <span className="text-ink-3">: </span>
                {o.started.reason}
              </p>
            )}
            <p className="mt-1.5 leading-relaxed text-ink-2">
              {o.failed ? (
                <span className="text-red-300">Failed: {o.failed.error}</span>
              ) : o.finished ? (
                o.finished.summary
              ) : (
                <span className="text-ink-3">running…</span>
              )}
            </p>
            {o.decision && <Decision decision={o.decision} />}
          </li>
        ))}
      </ol>
      {exhausted && (
        <div role="status" className="mt-3 rounded border border-amber-500/40 bg-amber-500/10 p-3 text-xs">
          <p className="font-medium text-amber-200">
            Budget spent ({exhausted.tool_calls_used} of {exhausted.max_tool_calls} tool calls). Claims use the evidence gathered so
            far; these questions stay open:
          </p>
          <ul className="mt-1.5 list-disc space-y-1 pl-4 text-ink-2">
            {exhausted.open_questions.map((q, i) => (
              <li key={i}>{q.text}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function Decision({ decision }: { decision: AgentDecisionEvent }) {
  return (
    <div className="mt-2 border-l-2 border-accent/60 pl-3">
      <p className="text-ink-3">Muse Spark 1.3 read {decision.observation_id}:</p>
      <p className="mt-0.5 leading-relaxed text-ink">{decision.reading}</p>
      {decision.requests.length === 0 ? (
        <p className="mt-1 text-ink-3">No follow-up requested.</p>
      ) : (
        <ul className="mt-1.5 space-y-1.5">
          {decision.requests.map((r) => (
            <li key={r.request_id}>
              <div className="flex flex-wrap items-baseline gap-x-2">
                <span className={`rounded border px-1.5 py-0.5 ${STATUS_STYLE[r.status]}`}>{r.status.replace("_", " ")}</span>
                <span className="font-mono text-ink">{r.request_id}</span>
                <span className="font-mono text-ink-2">{r.tool}</span>
                <span className="text-ink-3">cites {r.cites_observation_id}</span>
              </div>
              <p className="mt-0.5 text-ink-2">{r.reason}</p>
              {r.rejection_reason && <p className="mt-0.5 text-ink-3">Not run: {r.rejection_reason}</p>}
            </li>
          ))}
        </ul>
      )}
      {decision.open_questions.length > 0 && (
        <ul className="mt-1.5 list-disc pl-4 text-ink-2">
          {decision.open_questions.map((q, i) => (
            <li key={i}>Open question: {q}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
