// One viewport of the dual-section viewer: a section's rendered channels from its dataset adapter on black, the
// region box the researcher drags, the gate readout for that box, recorded SAM boxes and a SAM 3.1 outline.
// The provenance label ("Rendered from molecules") is a fixed overlay that no toggle hides.
import { OrthographicView } from "@deck.gl/core";
import { PathLayer, PolygonLayer } from "@deck.gl/layers";
import DeckGL from "@deck.gl/react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { GateStatus, Region, StructureRun } from "../contracts/generated";
import type { LoadedSection } from "../datasets/adapter";
import { RECORDED_BOX, REGION_FAILING, REGION_PASSING, STRUCTURE_OUTLINE, rgbOf } from "../palette";

export interface Camera {
  target: [number, number];
  zoom: number;
}

export type Tool = "pan" | "box";

export interface GateReadout {
  status: GateStatus | null;
  /** Milliseconds from the box change to this readout. */
  latencyMs: number | null;
  pending: boolean;
  problem: string | null;
}

export interface SamState {
  run: StructureRun | null;
  busy: boolean;
  problem: string | null;
}

interface Props {
  side: "left" | "right";
  loaded: LoadedSection | null;
  loading: boolean;
  problem: string | null;
  camera: Camera | null;
  zoomRange: { min: number; max: number };
  onCamera: (camera: Camera) => void;
  onSize: (size: { width: number; height: number }) => void;
  tool: Tool;
  visibleChannels: ReadonlySet<string>;
  gain: number;
  box: Region | null;
  onBox: (box: Region | null) => void;
  gate: GateReadout;
  recordedBoxes: Region[];
  onPickRecorded: (box: Region) => void;
  sam: SamState;
  samMaxSideUm: number | null;
  onRunSam: () => void;
}

const MIN_BOX_UM = 4;

export function SectionPane(props: Props) {
  const { loaded, camera, box, tool } = props;
  const container = useRef<HTMLDivElement>(null);
  const size = useSize(container);
  const onSize = props.onSize;
  useEffect(() => {
    if (size) onSize(size);
  }, [size, onSize]);

  const gateMatchesBox = props.gate.status !== null && sameBox(props.gate.status.roi ?? null, box);
  const failing = gateMatchesBox && !!props.gate.status && !(props.gate.status.passes_population_gate && props.gate.status.passes_molecule_gate);
  const boxColour = failing ? REGION_FAILING : REGION_PASSING;

  const exposureZoom = camera ? Math.round(camera.zoom * 8) / 8 : 0; // exposure steps in eighths of a zoom level
  const channelLayers = useMemo(
    () => (loaded ? loaded.layers({ idPrefix: props.side, visibleChannels: props.visibleChannels, gain: props.gain, zoom: exposureZoom }) : []),
    [loaded, props.side, props.visibleChannels, props.gain, exposureZoom],
  );

  const overlayLayers = [
    new PathLayer<Region>({
      id: `${props.side}-recorded-boxes`,
      data: props.recordedBoxes,
      getPath: boxPath,
      getColor: [...rgbOf(RECORDED_BOX), 200],
      getWidth: 1,
      widthUnits: "pixels",
      visible: tool === "box",
    }),
    new PathLayer({
      id: `${props.side}-sam-outline`,
      data: props.sam.run?.structures ?? [],
      getPath: (s: { outline: number[][] }) => [...s.outline, s.outline[0] ?? [0, 0]].map((p): [number, number] => [p[0] ?? 0, p[1] ?? 0]),
      getColor: [...rgbOf(STRUCTURE_OUTLINE), 255],
      getWidth: 2,
      widthUnits: "pixels",
    }),
    ...(box
      ? [
          new PolygonLayer<Region>({
            id: `${props.side}-region-fill`,
            data: [box],
            getPolygon: boxPath,
            getFillColor: [...rgbOf(boxColour), failing ? 34 : 18],
            stroked: false,
          }),
          new PathLayer<Region>({
            id: `${props.side}-region-outline`,
            data: [box],
            getPath: boxPath,
            getColor: [...rgbOf(boxColour), 255],
            getWidth: failing ? 2 : 1.5,
            widthUnits: "pixels",
            updateTriggers: { getColor: boxColour, getWidth: failing },
          }),
        ]
      : []),
  ];

  // Screen to section micrometres for the box tool: an orthographic view with y down.
  const toWorld = (clientX: number, clientY: number): [number, number] | null => {
    const rect = container.current?.getBoundingClientRect();
    if (!rect || !camera) return null;
    const scale = 2 ** camera.zoom;
    return [camera.target[0] + (clientX - rect.left - rect.width / 2) / scale, camera.target[1] + (clientY - rect.top - rect.height / 2) / scale];
  };
  const drag = useRef<{ mode: "draw" | "move"; start: [number, number]; origin: Region | null } | null>(null);
  const [dragging, setDragging] = useState(false);

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (tool !== "box" || !loaded || e.button !== 0) return;
    if ((e.target as HTMLElement).closest("[data-pane-control]")) return;
    const point = toWorld(e.clientX, e.clientY);
    if (!point) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    const inside = box && point[0] >= box.x0 && point[0] <= box.x1 && point[1] >= box.y0 && point[1] <= box.y1;
    drag.current = { mode: inside ? "move" : "draw", start: point, origin: box };
    setDragging(true);
  };
  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const d = drag.current;
    if (!d || !loaded) return;
    const point = toWorld(e.clientX, e.clientY);
    if (!point) return;
    if (d.mode === "move" && d.origin) {
      const dx = point[0] - d.start[0];
      const dy = point[1] - d.start[1];
      props.onBox(round({ ...d.origin, x0: d.origin.x0 + dx, x1: d.origin.x1 + dx, y0: d.origin.y0 + dy, y1: d.origin.y1 + dy }));
    } else {
      const x0 = Math.min(d.start[0], point[0]);
      const x1 = Math.max(d.start[0], point[0]);
      const y0 = Math.min(d.start[1], point[1]);
      const y1 = Math.max(d.start[1], point[1]);
      if (x1 - x0 >= MIN_BOX_UM && y1 - y0 >= MIN_BOX_UM) props.onBox(round({ section_id: loaded.sectionId, x0, y0, x1, y1 }));
    }
  };
  const endDrag = () => {
    drag.current = null;
    setDragging(false);
  };

  const viewState = camera
    ? { target: [camera.target[0], camera.target[1], 0] as [number, number, number], zoom: camera.zoom, minZoom: props.zoomRange.min, maxZoom: props.zoomRange.max }
    : undefined;
  const view = useMemo(
    () => new OrthographicView({ id: props.side, flipY: true, controller: { dragPan: tool === "pan", dragRotate: false, doubleClickZoom: tool === "pan" } }),
    [props.side, tool],
  );

  const side = box ? Math.max(box.x1 - box.x0, box.y1 - box.y0) : 0;
  const samTooLarge = props.samMaxSideUm !== null && side > props.samMaxSideUm;

  return (
    <div
      ref={container}
      data-testid={`pane-${props.side}`}
      data-zoom={camera?.zoom}
      data-target={camera ? camera.target.join(",") : undefined}
      className={`relative h-full min-h-[22rem] w-full overflow-hidden rounded-md border border-line bg-black ${tool === "box" ? "cursor-crosshair" : "cursor-grab"}`}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
    >
      {size && viewState && loaded && (
        <DeckGL
          views={view}
          viewState={viewState}
          onViewStateChange={({ viewState: next }) => {
            const v = next as unknown as { target: number[]; zoom: number };
            props.onCamera({ target: [v.target[0] ?? 0, v.target[1] ?? 0], zoom: v.zoom });
          }}
          layers={[...channelLayers, ...overlayLayers]}
          controller={{ dragPan: tool === "pan", dragRotate: false }}
        />
      )}

      {/* Title, top left */}
      <div className="pointer-events-none absolute left-2 top-2 flex max-w-[60%] flex-col gap-0.5">
        <span className="truncate text-[13px] font-semibold text-ink">{loaded?.title ?? (props.loading ? "Loading section…" : "")}</span>
        {loaded?.group && (
          <span
            className={`w-fit rounded px-1.5 py-px text-[10px] font-semibold uppercase tracking-wider ${
              loaded.group.toLowerCase() === "control" ? "bg-sky-500/20 text-sky-200" : "bg-rose-500/20 text-rose-200"
            }`}
          >
            {loaded.group}
          </span>
        )}
      </div>

      {/* Provenance, top right: always visible */}
      {loaded && (
        <div
          data-testid={`provenance-${props.side}`}
          title={loaded.provenanceDetail}
          className="pointer-events-none absolute right-2 top-2 rounded border border-white/15 bg-black/70 px-2 py-0.5 text-[11px] font-medium tracking-wide text-ink-2"
        >
          {loaded.provenance}
        </div>
      )}

      {(props.loading || props.problem) && (
        <div
          role={props.problem ? "alert" : "status"}
          className={`absolute left-2 top-14 max-w-[85%] rounded border px-2 py-1 text-xs ${
            props.problem ? "border-red-500/40 bg-red-950/80 text-red-200" : "border-line bg-panel/90 text-ink-2"
          }`}
        >
          {props.problem ?? "Loading the whole section…"}
        </div>
      )}

      {/* Scale bar, bottom right */}
      {camera && <ScaleBar zoom={camera.zoom} />}

      {/* Gate readout and SAM, bottom left */}
      {loaded && (
        <div data-pane-control className="absolute bottom-2 left-2 flex max-w-[calc(100%-7rem)] flex-col gap-1.5">
          <GateCard gate={props.gate} box={box} failing={failing} dragging={dragging} />
          {box && props.samMaxSideUm !== null && (
            <div className="flex flex-wrap items-center gap-1.5">
              <button
                type="button"
                disabled={props.sam.busy || samTooLarge}
                onClick={props.onRunSam}
                title={samTooLarge ? `SAM 3.1 takes boxes up to ${props.samMaxSideUm} µm on a side` : undefined}
                className="rounded border border-cyan-300/50 bg-cyan-400/10 px-2 py-0.5 text-[11px] font-medium text-cyan-100 hover:bg-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {props.sam.busy ? "Running SAM 3.1…" : "Run SAM on this box"}
              </button>
              {samTooLarge && <span className="text-[11px] text-ink-3">box over {props.samMaxSideUm} µm</span>}
            </div>
          )}
          {props.sam.problem && <p className="rounded border border-red-500/40 bg-red-950/80 px-2 py-1 text-[11px] text-red-200">{props.sam.problem}</p>}
          {props.sam.run && <SamCard run={props.sam.run} />}
          {tool === "box" && props.recordedBoxes.length > 0 && (
            <div className="flex flex-wrap items-center gap-1 text-[11px] text-ink-3">
              Recorded SAM boxes:
              {props.recordedBoxes.map((b, i) => (
                <button
                  key={`${b.x0},${b.y0}`}
                  type="button"
                  onClick={() => props.onPickRecorded(b)}
                  className="rounded border border-line bg-black/60 px-1.5 py-px text-ink-2 hover:border-ink-3 hover:text-ink"
                >
                  {i + 1}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function GateCard({ gate, box, failing, dragging }: { gate: GateReadout; box: Region | null; failing: boolean; dragging: boolean }) {
  const s = gate.status;
  if (!s) return gate.problem ? <p className="rounded bg-red-950/80 px-2 py-1 text-[11px] text-red-200">{gate.problem}</p> : null;
  const forBox = sameBox(s.roi ?? null, box);
  const passes = s.passes_population_gate && s.passes_molecule_gate;
  const verdict = passes ? "passes both gates" : !s.passes_population_gate ? "fails the population gate" : "fails the molecule gate";
  return (
    <div
      data-testid="gate-readout"
      data-gate-latency-ms={gate.latencyMs !== null ? Math.round(gate.latencyMs) : undefined}
      data-gate-passes={passes ? "true" : "false"}
      className={`rounded border px-2 py-1 text-[11px] leading-snug backdrop-blur ${
        !forBox ? "border-line bg-black/70 text-ink-2" : failing ? "border-red-400/70 bg-red-950/80 text-red-100" : "border-emerald-400/50 bg-emerald-950/70 text-emerald-50"
      }`}
    >
      <div className="flex items-center gap-2">
        <span className="font-semibold uppercase tracking-wider">
          {s.roi ? (forBox ? (passes ? "Box passes" : "Box fails gates") : "Updating…") : "Whole section"}
        </span>
        {gate.latencyMs !== null && forBox && (
          <span className="font-mono text-[10px] opacity-70">{Math.round(gate.latencyMs)} ms</span>
        )}
        {(gate.pending || dragging) && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current opacity-70" />}
      </div>
      <div className="font-mono">
        {s.cells.toLocaleString()} {s.cell_type} cells · {s.molecules.toLocaleString()} {s.genes.join("/")} molecules
      </div>
      <div className="opacity-80">
        {verdict} (gates: ≥{s.population_gate_min_cells} cells, ≥{s.molecule_gate_min_molecules} molecules)
      </div>
    </div>
  );
}

function SamCard({ run }: { run: StructureRun }) {
  return (
    <div data-testid="sam-card" className="rounded border border-cyan-300/50 bg-black/80 px-2 py-1 text-[11px] text-cyan-50">
      <span className="mr-1.5 rounded bg-cyan-400/20 px-1 py-px font-semibold text-cyan-100">{run.badge}</span>
      {run.proposals.map((p) => {
        const sam = p.comparisons.find((c) => c.shape === "sam_outline");
        return (
          <span key={p.seed.seed_id}>
            {p.status}
            {p.fragments > 1 ? ` (${p.fragments} pieces)` : ""}
            {sam?.area_um2 != null ? ` · ${Math.round(sam.area_um2).toLocaleString()} µm²` : ""}
            {sam?.seed_box_coverage != null ? ` · covers ${Math.round(sam.seed_box_coverage * 100)}% of the box` : ""}
            {p.reason ? ` · ${p.reason}` : ""}
          </span>
        );
      })}
      <span className="ml-1 opacity-70">· {run.run_mode === "live" ? "live call" : "stored response"}</span>
    </div>
  );
}

function ScaleBar({ zoom }: { zoom: number }) {
  const umPerPx = 1 / 2 ** zoom;
  const target = umPerPx * 110;
  const magnitude = 10 ** Math.floor(Math.log10(target));
  const nice = [1, 2, 5, 10].map((m) => m * magnitude).filter((v) => v <= target).pop() ?? magnitude;
  const px = nice / umPerPx;
  const label = nice >= 1000 ? `${nice / 1000} mm` : `${nice} µm`;
  return (
    <div className="pointer-events-none absolute bottom-2 right-2 flex flex-col items-end gap-0.5 text-[10px] text-ink-2">
      <span className="font-mono">{label}</span>
      <div className="h-1 border-x border-b border-ink-2" style={{ width: px }} />
    </div>
  );
}

function boxPath(r: Region): [number, number][] {
  return [[r.x0, r.y0], [r.x1, r.y0], [r.x1, r.y1], [r.x0, r.y1], [r.x0, r.y0]];
}

function round(r: Region): Region {
  const q = (v: number) => Math.round(v * 10) / 10;
  return { section_id: r.section_id, x0: q(r.x0), y0: q(r.y0), x1: q(r.x1), y1: q(r.y1) };
}

export function sameBox(a: Region | null, b: Region | null): boolean {
  if (a === null || b === null) return a === b;
  return a.section_id === b.section_id && a.x0 === b.x0 && a.y0 === b.y0 && a.x1 === b.x1 && a.y1 === b.y1;
}

function useSize(ref: React.RefObject<HTMLDivElement | null>): { width: number; height: number } | null {
  const [size, setSize] = useState<{ width: number; height: number } | null>(null);
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => {
      if (entry && entry.contentRect.width > 0 && entry.contentRect.height > 0) {
        setSize({ width: entry.contentRect.width, height: entry.contentRect.height });
      }
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [ref]);
  return size;
}
