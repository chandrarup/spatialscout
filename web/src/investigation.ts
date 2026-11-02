// The web app's view of one investigation, folded from its events in seq order.
import type {
  Claim,
  InvestigationEvent,
  InvestigationSnapshot,
  InvestigationStatus,
  PackageInfo,
  Plan,
  ReplayInfo,
  RunMode,
} from "./contracts/generated";

export interface InvestigationView {
  investigationId: string;
  question: string;
  runMode: RunMode;
  replay: ReplayInfo | null;
  status: InvestigationStatus;
  plan: Plan | null;
  claims: Claim[];
  pkg: PackageInfo | null;
  events: InvestigationEvent[];
  error: string | null;
}

export function fromSnapshot(snapshot: InvestigationSnapshot): InvestigationView {
  const base: InvestigationView = {
    investigationId: snapshot.investigation_id,
    question: snapshot.question,
    runMode: snapshot.run_mode,
    replay: snapshot.replay,
    status: snapshot.status,
    plan: null,
    claims: [],
    pkg: null,
    events: [],
    error: null,
  };
  return snapshot.events.reduce(applyEvent, base);
}

/** Apply one event. Events at or below the last seen seq are ignored, so a reconnect that overlaps is harmless. */
export function applyEvent(view: InvestigationView, event: InvestigationEvent): InvestigationView {
  const lastSeq = view.events.at(-1)?.seq ?? 0;
  if (event.seq <= lastSeq) return view;
  const next = { ...view, events: [...view.events, event] };
  switch (event.type) {
    case "plan_proposed":
      return { ...next, plan: event.plan, status: "awaiting_approval" };
    case "plan_approved":
      return {
        ...next,
        status: "running",
        plan: next.plan && { ...next.plan, status: "approved", plan_hash: event.plan_hash, approved_at_utc: event.recorded_at_utc },
      };
    case "tool_started":
    case "tool_finished":
      return next;
    case "claim_drafted":
      return { ...next, claims: [...next.claims, event.claim] };
    case "package_ready":
      return { ...next, pkg: event.package, status: "complete" };
    case "error":
      return { ...next, error: `${event.code}: ${event.message}`, status: "failed" };
  }
}

export function lastSeq(view: InvestigationView): number {
  return view.events.at(-1)?.seq ?? 0;
}
