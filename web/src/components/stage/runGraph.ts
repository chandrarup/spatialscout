// The run canvas's graph, folded from an investigation's events in seq order. Nothing here is invented: every node is
// one event (or one tool call's start and finish), and every number on a node is copied from its event. The agent runs
// one step at a time, so the graph's branches are the question's sub-claims, not work running side by side.
import type { Claim, InvestigationEvent, ModelCallRecord, VerificationResult } from "../../contracts/generated";

export type NodeKind = "question" | "plan" | "tool" | "decision" | "claim" | "check" | "verdict";
export type NodeState = "active" | "done" | "failed";

export interface RunNode {
  id: string;
  kind: NodeKind;
  lane: number;
  column: number;
  state: NodeState;
  title: string;
  detail: string | null;
  /** The model calls that produced this node, as recorded. */
  calls: ModelCallRecord[];
  /** A finding id whose computed figure belongs on the node. */
  figureFindingId: string | null;
  /** A computed evidence label or verification status. */
  label: string | null;
  injected: boolean;
  /** The seq of the event that last changed this node. */
  seq: number;
  claim?: Claim;
  verification?: VerificationResult;
  focus?: { findingId: string } | null;
}

export interface RunEdge {
  id: string;
  source: string;
  target: string;
}

export interface RunGraph {
  nodes: RunNode[];
  edges: RunEdge[];
  lanes: string[];
  /** The node the newest event touched. */
  latest: string | null;
}

const TOOL_TITLES: Record<string, string> = {
  audit_population: "Audit a population",
  run_random_thinning_control: "Random-thinning control",
  run_label_sensitivity_check: "Label-sensitivity check",
  audit_section: "Audit a section",
};

export function toolTitle(tool: string): string {
  return TOOL_TITLES[tool] ?? tool.replaceAll("_", " ");
}

export function modelName(call: ModelCallRecord): string {
  const model = call.model.replace(/^meta-models\//, "");
  const pretty = model
    .split("-")
    .map((part) => (/^\d/.test(part) ? part : part.charAt(0).toUpperCase() + part.slice(1)))
    .join(" ");
  return pretty;
}

function laneKey(args: Record<string, unknown>): string {
  const cell = typeof args.cell_type === "string" ? args.cell_type : "";
  const genes = Array.isArray(args.genes) ? (args.genes as string[]).join("/") : "";
  return `${cell}${genes ? ` · ${genes}` : ""}`;
}

export function buildGraph(question: string, events: InvestigationEvent[]): RunGraph {
  const nodes = new Map<string, RunNode>();
  const edges: RunEdge[] = [];
  const lanes: string[] = [];
  const laneOf = new Map<string, number>(); // observation id or finding id -> lane
  const tail = new Map<number, string>(); // lane -> last node id
  const columnOf = new Map<number, number>(); // lane -> next column
  let pendingCalls: ModelCallRecord[] = [];
  let latest: string | null = null;
  let planId: string | null = null;
  const draftCalls: ModelCallRecord[] = [];
  let lastVerifiedLane = 0;
  // Model calls left over after a claim's own check are its injected copies being checked; they get their own node,
  // never the verdict's (a frozen rule calls no model).
  const flushChallenges = (seq: number) => {
    if (pendingCalls.length === 0) return;
    place({
      id: `challenges-${seq}`,
      kind: "check",
      lane: lastVerifiedLane,
      state: "done",
      title: "Checks injected copies",
      detail: "Muse Spark reads the figure again for deliberately altered copies of the claim. Results lists which ones the verifier caught.",
      calls: pendingCalls,
      figureFindingId: null,
      label: null,
      injected: true,
      seq,
    });
    pendingCalls = [];
  };

  const lane = (key: string): number => {
    let index = lanes.indexOf(key);
    if (index < 0) {
      lanes.push(key);
      index = lanes.length - 1;
    }
    return index;
  };
  const link = (source: string | null, target: string) => {
    if (source && !edges.some((e) => e.source === source && e.target === target)) edges.push({ id: `${source}->${target}`, source, target });
  };
  const place = (node: Omit<RunNode, "column">): RunNode => {
    const column = columnOf.get(node.lane) ?? 2;
    columnOf.set(node.lane, column + 1);
    const placed = { ...node, column };
    nodes.set(node.id, placed);
    link(tail.get(node.lane) ?? planId, node.id);
    tail.set(node.lane, node.id);
    return placed;
  };

  nodes.set("question", {
    id: "question",
    kind: "question",
    lane: 0,
    column: 0,
    state: "done",
    title: question,
    detail: null,
    calls: [],
    figureFindingId: null,
    label: null,
    injected: false,
    seq: 0,
  });
  latest = "question";

  for (const event of events) {
    switch (event.type) {
      case "model_call":
        if (event.call.purpose === "claim_draft" || event.call.purpose === "claim_redraft") draftCalls.push(event.call);
        else pendingCalls.push(event.call);
        break;
      case "plan_proposed":
        planId = "plan";
        nodes.set("plan", {
          id: "plan",
          kind: "plan",
          lane: 0,
          column: 1,
          state: "active",
          title: "Plan",
          detail: event.plan.summary,
          calls: pendingCalls,
          figureFindingId: null,
          label: "awaiting approval",
          injected: false,
          seq: event.seq,
        });
        pendingCalls = [];
        link("question", "plan");
        latest = "plan";
        break;
      case "plan_approved": {
        const plan = nodes.get("plan");
        if (plan) nodes.set("plan", { ...plan, state: "done", label: "approved", seq: event.seq });
        latest = "plan";
        break;
      }
      case "plan_rejected": {
        const plan = nodes.get("plan");
        if (plan) nodes.set("plan", { ...plan, state: "failed", label: "rejected", seq: event.seq });
        latest = "plan";
        break;
      }
      case "tool_started": {
        const key = laneKey(event.arguments);
        const cited = event.cites_observation_id ? laneOf.get(event.cites_observation_id) : undefined;
        const l = cited ?? lane(key || event.tool);
        if (event.observation_id) laneOf.set(event.observation_id, l);
        const node = place({
          id: `tool-${event.step_id}`,
          kind: "tool",
          lane: l,
          state: "active",
          title: toolTitle(event.tool),
          detail: event.reason,
          calls: [],
          figureFindingId: null,
          label: null,
          injected: false,
          seq: event.seq,
        });
        latest = node.id;
        break;
      }
      case "tool_finished":
      case "tool_failed": {
        const id = `tool-${event.step_id}`;
        const node = nodes.get(id);
        if (node) {
          const finished = event.type === "tool_finished";
          const findingId = finished && event.artifact_id.startsWith("fnd-") ? event.artifact_id : null;
          if (findingId) laneOf.set(findingId, node.lane);
          nodes.set(id, {
            ...node,
            state: finished ? "done" : "failed",
            detail: finished ? event.summary : node.detail,
            figureFindingId: findingId,
            label: finished ? (event.label ?? null) : "tool failed",
            seq: event.seq,
            focus: findingId ? { findingId } : null,
          });
          latest = id;
        }
        break;
      }
      case "agent_decision": {
        const l = laneOf.get(event.observation_id) ?? 0;
        const accepted = event.requests.filter((r) => r.status === "accepted").length;
        const node = place({
          id: `decision-${event.observation_id}`,
          kind: "decision",
          lane: l,
          state: "done",
          title: "Reads the result",
          detail: event.reading,
          calls: pendingCalls,
          figureFindingId: null,
          label: accepted ? `asks for ${accepted} follow-up${accepted === 1 ? "" : "s"}` : "no follow-up",
          injected: false,
          seq: event.seq,
        });
        pendingCalls = [];
        latest = node.id;
        break;
      }
      case "claim_drafted": {
        const l = laneOf.get(event.claim.finding.finding_id) ?? 0;
        const node = place({
          id: `claim-${event.claim.claim_id}`,
          kind: "claim",
          lane: l,
          state: "active",
          title: "Drafts a claim",
          detail: event.claim.text,
          calls: draftCalls.splice(0, 1),
          figureFindingId: null,
          label: "checking",
          injected: false,
          seq: event.seq,
          claim: event.claim,
        });
        latest = node.id;
        break;
      }
      case "claim_rejected": {
        const l = laneOf.get(event.finding_id) ?? 0;
        const node = place({
          id: `rejected-${event.seq}`,
          kind: "claim",
          lane: l,
          state: "failed",
          title: "Claim dropped",
          detail: event.problems.join("; "),
          calls: draftCalls.splice(0),
          figureFindingId: null,
          label: "failed its check twice",
          injected: false,
          seq: event.seq,
        });
        latest = node.id;
        break;
      }
      case "claim_verified": {
        const injected = event.claim.injected.is_injected;
        const findingId = event.verification.figure?.finding_id ?? event.verification.finding_id ?? event.claim.finding.finding_id;
        const l = laneOf.get(event.claim.finding.finding_id) ?? 0;
        const claimNode = nodes.get(`claim-${event.claim.claim_id}`);
        if (claimNode && !injected) {
          nodes.set(claimNode.id, { ...claimNode, state: "done", label: event.verification.verification_status, claim: event.claim, verification: event.verification });
        }
        const node = place({
          id: `check-${event.claim.claim_id}`,
          kind: "check",
          lane: l,
          state: event.verification.verification_status === "verified" ? "done" : "failed",
          title: injected ? "Checks an injected copy" : "Checks the claim",
          detail: event.verification.visual?.explanation ?? null,
          calls: pendingCalls,
          figureFindingId: findingId,
          label: event.verification.verification_status,
          injected,
          seq: event.seq,
          claim: event.claim,
          verification: event.verification,
        });
        pendingCalls = [];
        if (!injected) lastVerifiedLane = l;
        latest = node.id;
        break;
      }
      case "verdict": {
        flushChallenges(event.seq);
        const column = Math.max(2, ...[...columnOf.values()]);
        nodes.set("verdict", {
          id: "verdict",
          kind: "verdict",
          lane: Math.max(0, (lanes.length - 1) / 2),
          column,
          state: "done",
          title: "Verdict",
          detail: event.verdict.verdicts.map((v) => `${v.sub_claim.cell_type} · ${v.sub_claim.genes.join("/")}: ${v.verdict}`).join("\n"),
          calls: [],
          figureFindingId: null,
          label: null,
          injected: false,
          seq: event.seq,
        });
        for (const last of tail.values()) link(last, "verdict");
        latest = "verdict";
        break;
      }
      case "error": {
        flushChallenges(event.seq);
        nodes.set("error", {
          id: "error",
          kind: "verdict",
          lane: 0,
          column: Math.max(2, ...[...columnOf.values()]),
          state: "failed",
          title: "Stopped",
          detail: `${event.code}: ${event.message}`,
          calls: [],
          figureFindingId: null,
          label: "error",
          injected: false,
          seq: event.seq,
        });
        latest = "error";
        break;
      }
      default:
        break;
    }
  }
  return { nodes: [...nodes.values()], edges, lanes, latest };
}

/** How long to wait before showing the next recorded event: the recorded gap, held to a pace a presenter can talk
 * over (about two to four seconds per visible step at 1x), and divided by the speed. A model call shows nothing of its
 * own on the canvas (it attaches to the step it produced), so it passes at once. */
export function playbackDelay(previous: InvestigationEvent | undefined, next: InvestigationEvent, speed: number): number {
  if (next.type === "model_call") return 60;
  if (!previous) return 900;
  const gap = Date.parse(next.recorded_at_utc) - Date.parse(previous.recorded_at_utc);
  const paced = Number.isFinite(gap) ? Math.min(4200, Math.max(2200, gap / 4)) : 2600;
  return paced / speed;
}

/** Whether an event is a step the presenter steps through (model calls ride along with the next step). */
export function isStep(event: InvestigationEvent): boolean {
  return event.type !== "model_call";
}
