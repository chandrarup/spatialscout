// A KPMP CODEX participant laid on its side: the image strip runs left to right across the screen. Every layer the
// adapter builds is drawn through one 90-degree model matrix, so section coordinates are never changed; a box drawn on
// screen maps back to section micrometres exactly (a quarter turn keeps boxes axis-aligned), and the protein audit
// receives the same box it would from the upright viewer.
import { type Layer, OrthographicView } from "@deck.gl/core";
import { PathLayer, PolygonLayer } from "@deck.gl/layers";
import DeckGL from "@deck.gl/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Region } from "../../contracts/generated";
import type { LoadedSection } from "../../datasets/adapter";

const DRIFT_PX_PER_S = 26;

export interface View {
  target: [number, number];
  zoom: number;
}

interface Props {
  section: LoadedSection;
  visible: ReadonlySet<string>;
  gain?: number;
  /** Draw a box instead of panning. */
  boxMode?: boolean;
  box?: Region | null;
  onBox?: (box: Region | null) => void;
  /** Drift slowly along the strip until the visitor touches it. */
  drift?: boolean;
  /** Fraction of the strip's width to fill when fitted (above 1 crops in). */
  fill?: number;
  /** Drift direction (1 or -1) and starting phase (0..1). */
  direction?: 1 | -1;
  phase?: number;
  /** Extra deck.gl layers in section coordinates (drawn through the same rotation). */
  overlays?: Layer[];
  /** Called with a click's section coordinates when not drawing a box. */
  onPick?: (x: number, y: number) => void;
  /** Fly here (section coordinates) whenever the key changes. */
  flyTo?: { key: number; region: Region } | null;
  className?: string;
}

/** Section (x, y) to screen-world (u, v): u = y, v = W - x, where W is the section's width. */
function rotation(width: number): Float32Array {
  return new Float32Array([0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, width, 0, 1]);
}

export function toSection(width: number, u: number, v: number): [number, number] {
  return [width - v, u];
}

export function toWorld(width: number, x: number, y: number): [number, number] {
  return [y, width - x];
}

export function CodexView({ section, visible, gain = 1.2, boxMode = false, box = null, onBox, drift = false, fill = 1, direction = 1, phase = 0, overlays = [], onPick, flyTo = null, className = "" }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState<{ width: number; height: number } | null>(null);
  const [view, setView] = useState<View | null>(null);
  const [touched, setTouched] = useState(false);
  const width = section.extent.x1 - section.extent.x0;
  const length = section.extent.y1 - section.extent.y0;

  useEffect(() => {
    const el = container.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => {
      if (entry) setSize({ width: entry.contentRect.width, height: entry.contentRect.height });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const fitted = useMemo((): View | null => {
    if (!size) return null;
    const scale = Math.min(size.width / length, size.height / width) * fill * 0.96;
    return { target: [length / 2, width / 2], zoom: Math.log2(scale) };
  }, [size, length, width, fill]);

  useEffect(() => {
    if (fitted) setView((v) => v ?? fitted);
  }, [fitted]);

  // A slow pan along the strip and back at a constant screen speed, for the first screen; it stops for good once the
  // visitor takes over. `direction` lets two strips drift opposite ways.
  useEffect(() => {
    if (!drift || touched || !fitted || !size) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const scale = 2 ** fitted.zoom;
    const visibleLength = size.width / scale;
    const span = Math.max(0, (length - visibleLength) / 2);
    if (span === 0) return;
    const worldPerSecond = DRIFT_PX_PER_S / scale;
    const period = (4 * span) / worldPerSecond;
    const start = performance.now() - period * phase;
    let frame = 0;
    const tick = (now: number) => {
      const t = (((now - start) / 1000) % period) / period; // 0..1
      const tri = t < 0.5 ? 4 * t - 1 : 3 - 4 * t; // -1..1..-1
      setView({ target: [length / 2 + tri * span * direction, width / 2], zoom: fitted.zoom });
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [drift, touched, fitted, size, length, width, direction, phase]);

  useEffect(() => {
    if (!flyTo || !size) return;
    setTouched(true);
    const r = flyTo.region;
    const a = toWorld(width, r.x0, r.y0);
    const b = toWorld(width, r.x1, r.y1);
    const w = Math.abs(b[0] - a[0]) * 1.6;
    const h = Math.abs(b[1] - a[1]) * 1.6;
    const zoom = Math.min(4, Math.log2(Math.min(size.width / Math.max(w, 1), size.height / Math.max(h, 1))));
    setView({ target: [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2], zoom });
  }, [flyTo?.key]); // eslint-disable-line react-hooks/exhaustive-deps

  const matrix = useMemo(() => rotation(width), [width]);
  const channelLayers = useMemo(
    () =>
      section
        .layers({ idPrefix: "codex", visibleChannels: visible, gain, zoom: view ? Math.round(view.zoom * 4) / 4 : 0 })
        .map((layer) => layer.clone({ modelMatrix: matrix })),
    [section, visible, gain, view, matrix],
  );

  const boxPath = (r: Region): [number, number][] => {
    const a = toWorld(width, r.x0, r.y0);
    const b = toWorld(width, r.x1, r.y1);
    return [
      [a[0], a[1]],
      [b[0], a[1]],
      [b[0], b[1]],
      [a[0], b[1]],
      [a[0], a[1]],
    ];
  };
  const boxLayers = box
    ? [
        new PolygonLayer<Region>({ id: "codex-box-fill", data: [box], getPolygon: boxPath, getFillColor: [255, 255, 255, 18], stroked: false }),
        new PathLayer<Region>({ id: "codex-box", data: [box], getPath: boxPath, getColor: [255, 255, 255, 230], getWidth: 1.5, widthUnits: "pixels" }),
      ]
    : [];

  const screenToWorld = useCallback(
    (clientX: number, clientY: number): [number, number] | null => {
      const rect = container.current?.getBoundingClientRect();
      if (!rect || !view) return null;
      const scale = 2 ** view.zoom;
      return [view.target[0] + (clientX - rect.left - rect.width / 2) / scale, view.target[1] + (clientY - rect.top - rect.height / 2) / scale];
    },
    [view],
  );
  const start = useRef<[number, number] | null>(null);
  const [draft, setDraft] = useState<Region | null>(null);
  const toRegion = (a: [number, number], b: [number, number]): Region => {
    const p = toSection(width, a[0], a[1]);
    const q = toSection(width, b[0], b[1]);
    const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
    return {
      section_id: section.sectionId,
      x0: clamp(Math.min(p[0], q[0]), section.extent.x0, section.extent.x1),
      x1: clamp(Math.max(p[0], q[0]), section.extent.x0, section.extent.x1),
      y0: clamp(Math.min(p[1], q[1]), section.extent.y0, section.extent.y1),
      y1: clamp(Math.max(p[1], q[1]), section.extent.y0, section.extent.y1),
    };
  };

  return (
    <div
      ref={container}
      className={`relative h-full w-full overflow-hidden bg-black ${boxMode ? "cursor-crosshair" : "cursor-grab active:cursor-grabbing"} ${className}`}
      onPointerDown={(e) => {
        setTouched(true);
        if (!boxMode || e.button !== 0) return;
        const p = screenToWorld(e.clientX, e.clientY);
        if (!p) return;
        e.currentTarget.setPointerCapture(e.pointerId);
        start.current = p;
      }}
      onPointerMove={(e) => {
        if (!boxMode || !start.current) return;
        const p = screenToWorld(e.clientX, e.clientY);
        if (p) setDraft(toRegion(start.current, p));
      }}
      onPointerUp={(e) => {
        if (!boxMode || !start.current) return;
        const p = screenToWorld(e.clientX, e.clientY);
        const s = start.current;
        start.current = null;
        setDraft(null);
        if (!p) return;
        const region = toRegion(s, p);
        const big = region.x1 - region.x0 > 8 && region.y1 - region.y0 > 8;
        onBox?.(big ? region : null);
      }}
      onWheel={() => setTouched(true)}
    >
      {view && (
        <DeckGL
          views={new OrthographicView({ id: "codex", flipY: true })}
          pickingRadius={8}
          viewState={{ ...view, minZoom: (fitted?.zoom ?? -6) - 1, maxZoom: 4 }}
          controller={boxMode ? false : { dragPan: true, scrollZoom: true, doubleClickZoom: true, inertia: false }}
          onViewStateChange={({ viewState, interactionState }) => {
            if (interactionState?.isDragging || interactionState?.isZooming || interactionState?.isPanning) setTouched(true);
            const next = viewState as unknown as View;
            setView({ target: [next.target[0], next.target[1]], zoom: next.zoom });
          }}
          onClick={(info) => {
            if (boxMode || !onPick || !info.coordinate) return;
            const [x, y] = toSection(width, info.coordinate[0]!, info.coordinate[1]!);
            onPick(x, y);
          }}
          layers={[...channelLayers, ...overlays.map((layer) => layer.clone({ modelMatrix: matrix })), ...(draft ? [] : boxLayers), ...(draft ? [new PathLayer<Region>({ id: "codex-draft", data: [draft], getPath: boxPath, getColor: [255, 255, 255, 200], getWidth: 1, widthUnits: "pixels" })] : [])]}
          style={{ position: "absolute", inset: "0" }}
        />
      )}
    </div>
  );
}
