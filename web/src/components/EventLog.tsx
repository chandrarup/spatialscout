// The event log: every investigation event in seq order, as it streams. The reasoning timeline groups the agent loop.
import type { InvestigationEvent } from "../contracts/generated";

export function EventLog({ events }: { events: InvestigationEvent[] }) {
  return (
    <section aria-labelledby="events-title" className="rounded-lg border border-line bg-panel p-4">
      <h2 id="events-title" className="mb-2 text-sm font-semibold text-ink">
        Events
      </h2>
      {events.length === 0 ? (
        <p className="text-xs text-ink-3">Events appear here as the investigation runs.</p>
      ) : (
        <ol aria-live="polite" className="space-y-1.5 text-xs">
          {events.map((event) => (
            <li key={event.seq} className="grid grid-cols-[2rem_7.5rem_1fr] gap-2">
              <span className="text-right font-mono text-ink-3">{event.seq}</span>
              <span className={event.type === "error" ? "font-medium text-red-400" : "font-medium text-ink"}>
                {event.type.replace("_", " ")}
              </span>
              <span className="text-ink-2">{describe(event)}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function describe(event: InvestigationEvent): string {
  switch (event.type) {
    case "plan_proposed":
      return `${event.plan.steps.length} step(s) awaiting approval`;
    case "plan_approved":
      return `frozen, hash ${event.plan_hash.slice(0, 12)}`;
    case "tool_started":
      return event.tool;
    case "tool_finished":
      return event.summary;
    case "claim_drafted":
      return `claim ${event.claim.claim_id} on ${event.claim.finding.finding_kind} result ${event.claim.finding.finding_id}`;
    case "package_ready":
      return `evidence package ${event.package.package_id}`;
    case "model_call": {
      const call = event.call;
      const where = call.failover_from ? `${call.served_by} (failover from ${call.failover_from})` : (call.served_by ?? call.provider);
      const origin = call.source === "live" ? "live" : "stored";
      return `${call.purpose}: ${call.model} on ${where}, ${origin}, ${call.latency_ms} ms${call.error_code ? `, ${call.error_code}` : ""}`;
    }
    case "plan_rejected":
      return `${event.by === "researcher" ? "rejected by the researcher" : `rejected (attempt ${event.attempt})`}: ${event.reason}`;
    case "tool_failed":
      return `${event.tool} failed: ${event.error}`;
    case "agent_decision":
      return `read ${event.observation_id}: ${event.requests.length} follow-up request(s)`;
    case "budget_exhausted":
      return `budget spent (${event.tool_calls_used}/${event.max_tool_calls}); ${event.open_questions.length} open question(s)`;
    case "claim_rejected":
      return `claim draft on ${event.finding_id} rejected: ${event.problems.join("; ")}`;
    case "claim_verified": {
      const injected = event.claim.injected;
      const what = injected.is_injected ? `injected error (${injected.kind}) on claim` : "claim";
      return `${what} ${event.claim.claim_id}: ${event.verification.verification_status}`;
    }
    case "review_decided":
      return `${event.decision.reviewer} marked ${event.decision.claim_id} v${event.decision.claim_version} ${event.decision.decision.replaceAll("_", " ")}`;
    case "verdict":
      return event.verdict.verdicts.map((v) => `${v.sub_claim.text}: ${v.verdict}`).join("; ") || "no sub-claims";
    case "error":
      return `${event.code}: ${event.message}`;
  }
}
