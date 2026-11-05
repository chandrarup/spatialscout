// The run canvas: the investigation as a graph that grows one recorded event at a time. Pan, zoom and drag freely;
// the camera follows the newest step until the researcher takes over. Each card shows its event's own text and the
// model calls behind it with their recorded latency and cost, and a finding's computed figure where Muse Spark read it.
import {
  Background,
  BackgroundVariant,
  type Edge,
  Handle,
  type Node,
  type NodeProps,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/base.css";
import { memo, useEffect, useMemo, useState } from "react";
import { api } from "../../api";
import type { ModelCallRecord } from "../../contracts/generated";
import { type RunGraph, type RunNode, modelName } from "./runGraph";

const COLUMN = 360;
const LANE = 470;
const WIDTH = 300;

type CardData = { node: RunNode; latest: boolean; investigationId: string; onFocus: (findingId: string) => void } & Record<string, unknown>;

export const KIND_LINE: Record<RunNode["kind"], string> = {
  question: "Your question",
  plan: "Planner",
  tool: "Analysis engine",
  decision: "Agent",
  claim: "Claim writer",
  check: "Verifier",
  verdict: "Frozen verdict rule",
};

export function labelTone(label: string | null): string {
  switch (label) {
    case "stable":
    case "verified":
    case "approved":
    case "confirmed":
      return "bg-[#222a10] text-stable";
    case "segmentation_sensitive":
    case "disputed":
    case "refuted":
    case "awaiting approval":
    case "checking":
      return "bg-[#2b2414] text-sensitive";
    case "failed":
    case "rejected":
    case "error":
    case "tool failed":
      return "bg-[#2c1a20] text-bad";
    default:
      return "bg-raised text-ink-2";
  }
}

function seconds(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${ms} ms`;
}

function CallLine({ call }: { call: ModelCallRecord }) {
  return (
    <li className="flex items-baseline justify-between gap-2 text-[12px]">
      <span className="truncate text-ink">
        {modelName(call)}
        <span className="text-ink-3"> · {call.served_by ?? call.provider}</span>
      </span>
      <span className="shrink-0 text-ink-3">
        {call.latency_ms > 0 ? seconds(call.latency_ms) : "stored"}
        {call.estimated_cost_usd !== null && ` · $${call.estimated_cost_usd.toFixed(4)}`}
      </span>
    </li>
  );
}

// A finding's figure is written when the verifier reads it, near the end of a live run. Until then the file does not
// exist: say so and look again every few seconds instead of showing a broken image.
const FIGURE_RETRY_MS = 4000;
function FigureThumb({ url, findingId }: { url: string; findingId: string }) {
  const [attempt, setAttempt] = useState(0);
  const [missing, setMissing] = useState(false);
  useEffect(() => {
    if (!missing) return;
    const timer = window.setTimeout(() => {
      setMissing(false);
      setAttempt((a) => a + 1);
    }, FIGURE_RETRY_MS);
    return () => window.clearTimeout(timer);
  }, [missing]);
  return (
    <>
      <img
        key={attempt}
        src={attempt ? `${url}?try=${attempt}` : url}
        alt={`Computed figure for ${findingId}`}
        className={`block w-full bg-white ${missing ? "hidden" : ""}`}
        loading="lazy"
        onError={() => setMissing(true)}
      />
      {missing && <span className="block rounded-lg bg-raised px-3 py-2.5 text-left text-[12px] text-ink-3">Figure appears when the verifier reads it</span>}
    </>
  );
}

const Card = memo(function Card({ data }: NodeProps<Node<CardData>>) {
  const { node, latest, investigationId, onFocus } = data;
  const [open, setOpen] = useState(false);
  const isQuestion = node.kind === "question";
  const purpose = node.calls[0]?.purpose.replaceAll("_", " ");
  return (
    <div
      className={`node-in rounded-2xl p-4 text-left transition-colors ${isQuestion ? "bg-white text-black" : "bg-panel"} ${
        latest && node.state === "active" ? "ring-1 ring-stable/60" : ""
      } ${node.injected ? "ring-1 ring-sensitive/70" : ""}`}
      style={{ width: WIDTH }}
    >
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !border-0 !bg-[#3a3d44]" />
      <div className="mb-1 flex items-center justify-between gap-2 text-[12px]">
        <span className={isQuestion ? "text-black/60" : "text-ink-3"}>
          {KIND_LINE[node.kind]}
          {purpose && ` · ${purpose}`}
        </span>
        {node.state === "active" && <span className="h-2 w-2 animate-pulse rounded-full bg-stable" aria-label="in progress" />}
      </div>
      {node.injected && (
        <p className="mb-1 rounded-md bg-[#2b2414] px-2 py-1 text-[12px] font-medium text-sensitive">
          Injected error: a deliberately altered copy of the claim, put through the same checks
        </p>
      )}
      <h3 className={`font-semibold leading-snug ${isQuestion ? "text-[17px]" : "text-[15px] text-ink"}`}>{node.title}</h3>
      {node.detail && (
        <button type="button" onClick={() => setOpen((o) => !o)} className="nodrag mt-1.5 block w-full cursor-pointer text-left">
          <p className={`text-[13px] leading-relaxed whitespace-pre-line text-ink-2 ${open ? "" : "line-clamp-4"}`}>{node.detail}</p>
        </button>
      )}
      {node.figureFindingId && (
        <button
          type="button"
          onClick={() => onFocus(node.figureFindingId!)}
          className={`nodrag relative mt-3 block w-full overflow-hidden rounded-lg ${node.kind === "check" && latest ? "scan" : ""}`}
          title="Open this finding's evidence region on its section"
        >
          <FigureThumb url={api.investigationFigureUrl(investigationId, node.figureFindingId)} findingId={node.figureFindingId} />
        </button>
      )}
      {node.calls.length > 0 && <ul className="mt-3 space-y-1 rounded-lg bg-raised px-2.5 py-2">{node.calls.map((c) => <CallLine key={c.call_id} call={c} />)}</ul>}
      {node.label && (
        <span className={`mt-3 inline-block rounded-full px-2.5 py-0.5 text-[12px] font-medium ${labelTone(node.label)}`}>{node.label.replaceAll("_", " ")}</span>
      )}
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !border-0 !bg-[#3a3d44]" />
    </div>
  );
});

const nodeTypes = { card: Card };

interface Props {
  graph: RunGraph;
  investigationId: string;
  /** Pixels of the canvas's right edge covered by the assistant drawer. */
  rightInset: number;
  onFocus: (findingId: string) => void;
  follow: boolean;
  onFollow: (follow: boolean) => void;
  /** The zoom the camera follows at; smaller in a narrow rail. */
  zoom?: number;
  /** Fit every card in view whenever this changes. */
  fitKey?: number;
}

function Canvas({ graph, investigationId, rightInset, onFocus, follow, onFollow, zoom: followZoom = 0.9, fitKey = 0 }: Props) {
  const flow = useReactFlow();
  const laneCount = Math.max(1, graph.lanes.length);
  const centre = ((laneCount - 1) / 2) * LANE;

  const placed = useMemo(
    () =>
      graph.nodes.map((n): { id: string; x: number; y: number } => ({
        id: n.id,
        x: n.column * COLUMN,
        y: n.kind === "question" || n.kind === "plan" || n.kind === "verdict" ? centre : n.lane * LANE,
      })),
    [graph.nodes, centre],
  );
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});

  const nodes = useMemo<Node<CardData>[]>(
    () =>
      graph.nodes.map((n) => {
        const p = placed.find((q) => q.id === n.id)!;
        return {
          id: n.id,
          type: "card",
          position: positions[n.id] ?? { x: p.x, y: p.y },
          data: { node: n, latest: n.id === graph.latest, investigationId, onFocus },
        };
      }),
    [graph, placed, positions, investigationId, onFocus],
  );
  const edges = useMemo<Edge[]>(
    () =>
      graph.edges.map((e) => {
        const target = graph.nodes.find((n) => n.id === e.target);
        return { id: e.id, source: e.source, target: e.target, type: "smoothstep", className: target?.state === "active" ? "live" : "" };
      }),
    [graph],
  );

  useEffect(() => {
    if (!follow || !graph.latest) return;
    const p = placed.find((q) => q.id === graph.latest);
    if (!p) return;
    const zoom = followZoom;
    void flow.setCenter(p.x + WIDTH / 2 + rightInset / 2 / zoom, p.y + 200, { zoom, duration: 900 });
  }, [follow, graph.latest, placed, flow, rightInset, followZoom]);
  useEffect(() => {
    if (fitKey) void flow.fitView({ padding: 0.15, duration: 500 });
  }, [fitKey, flow]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodesChange={(changes) => {
        for (const c of changes) if (c.type === "position" && c.position) setPositions((all) => ({ ...all, [c.id]: c.position! }));
      }}
      onMoveStart={(event) => {
        if (event) onFollow(false);
      }}
      minZoom={0.2}
      maxZoom={1.6}
      defaultViewport={{ x: 80, y: 120, zoom: 0.9 }}
      proOptions={{ hideAttribution: true }}
      nodesConnectable={false}
      colorMode="dark"
    >
      <Background variant={BackgroundVariant.Dots} gap={28} size={1} color="#1f2125" />
    </ReactFlow>
  );
}

export function RunCanvas(props: Props) {
  return (
    <ReactFlowProvider>
      <Canvas {...props} />
    </ReactFlowProvider>
  );
}
