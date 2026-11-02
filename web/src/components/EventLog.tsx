// The event log: every investigation event in seq order, as it streams. Ticket 09a adds the reasoning timeline.
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
    case "error":
      return `${event.code}: ${event.message}`;
  }
}
