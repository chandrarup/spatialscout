// The tissue viewer: molecules as points coloured by gene, nuclei as rings coloured by cell type label,
// and structure outlines, in section micrometres. Drag to pan, scroll or pinch to zoom.
//
// A whole section (hundreds of thousands to a few million molecules) is drawn from typed arrays as deck.gl
// binary attributes. A highlight or filter change rebuilds flat buffers in one pass: grey background molecules
// underneath, coloured ones on top. No per-molecule objects are created and nothing is sorted.
//
// With a compared condition the viewer splits: the default condition on the left of a draggable divider and the
// compared condition on the right, both showing the same tissue at the same scale. The right side draws the
// molecules that condition excludes in yellow. `flyTo` animates over about 800 ms into a region.
import { OrthographicView, type PickingInfo } from "@deck.gl/core";
import { PathLayer, ScatterplotLayer } from "@deck.gl/layers";
import DeckGL from "@deck.gl/react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ConditionName, Region, StructureMask } from "../contracts/generated";
import { type SectionArrays, includedUnder } from "../packed";
import {
  CELL_TYPE_SLOTS,
  EVIDENCE_REGION,
  EXCLUDED_MOLECULE,
  GENE_SLOTS,
  type Highlight,
  OTHER_CELL,
  OTHER_MOLECULE,
  STRUCTURE_OUTLINE,
  rgbOf,
} from "../palette";

export const CONDITION_NAMES: Record<string, string> = {
  default: "default",
  nucleus_only: "nucleus-only",
  distance_cap_1um: "1 µm cap",
  distance_cap_2um: "2 µm cap",
  structure_constrained: "structure-constrained · SAM 3.1 proposal (exploratory)",
};

interface Props {
  section: SectionArrays;
  genes: Highlight;
  cellTypes: Highlight;
  /** Genes whose molecules are drawn; null draws every gene. */
  visibleGenes: ReadonlySet<string> | null;
  /** The condition shown right of the divider against the default condition; null shows one view. */
  compare: ConditionName | null;
  /** Fly into this region when `key` changes. */
  flyTo: { region: Region; key: number } | null;
  /** An evidence region to outline. */
  evidenceRegion: Region | null;
  /** With a focused finding, only molecules of this population's cells are drawn as excluded. */
  excludedCellType: string | null;
  /**
   * How `compare` is shown: one canvas under the usual rule, one canvas under the stricter rule (dropped molecules
   * hidden), one canvas with the dropped molecules in yellow, or the split. Without `compare`, always the usual rule.
   */
  display?: Display;
  /** Draw a box instead of panning. */
  boxMode?: boolean;
  box?: Region | null;
  onBox?: (box: Region | null) => void;
  /** Refit the whole section whenever this changes. */
  fitKey?: number;
}

export type Display = "usual" | "stricter" | "excluded" | "compare";

/** Molecules of one layer: positions, optional per-molecule colours, and each point's molecule index. */
interface MoleculeBuffer {
  length: number;
  positions: Float32Array;
  colours: Uint8Array | null;
  index: Uint32Array;
}

interface Camera {
  target: [number, number];
  zoom: number;
}

const BACKGROUND_ALPHA = 150;
const FLY_MS = 800;

export function Viewer({
  section,
  genes,
  cellTypes,
  visibleGenes,
  compare: compared,
  flyTo,
  evidenceRegion,
  excludedCellType,
  display = "compare",
  boxMode = false,
  box = null,
  onBox,
  fitKey = 0,
}: Props) {
  const container = useRef<HTMLDivElement>(null);
  const size = useSize(container);
  const view = section.view;
  const [camera, setCamera] = useState<Camera | null>(null);
  const [split, setSplit] = useState(0.5);
  const zoomRange = useRef<{ min: number; max: number }>({ min: -10, max: 10 });
  const compare = compared && display === "compare" ? compared : null;
  const single = compared && display !== "compare" ? display : "usual";

  // Fit the whole section once the container has a size, whenever another section opens (not when the same section
  // reloads under another label rule, so a fly-to survives it), and on an explicit Fit. A resize keeps the camera.
  useEffect(() => {
    if (!size) return;
    const { x0, y0, x1, y1 } = view.region;
    const scale = Math.min(size.width / Math.max(x1 - x0, 1), size.height / Math.max(y1 - y0, 1)) * 0.9;
    const fit = Math.log2(scale);
    zoomRange.current = { min: fit - 2, max: fit + 8 };
    setCamera({ target: [(x0 + x1) / 2, (y0 + y1) / 2], zoom: fit });
  }, [view.section_id, size !== null, fitKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fly into a region: ease the shared camera over FLY_MS so both halves of the split stay aligned throughout.
  const cameraRef = useRef(camera);
  cameraRef.current = camera;
  useEffect(() => {
    if (!flyTo || !size || flyTo.region.section_id !== view.section_id) return;
    const start = cameraRef.current;
    if (!start) return;
    const { x0, y0, x1, y1 } = flyTo.region;
    const span = Math.max(x1 - x0, y1 - y0, 1);
    const end: Camera = {
      target: [(x0 + x1) / 2, (y0 + y1) / 2],
      zoom: Math.min(Math.log2(Math.min(size.width, size.height) / (span * 2)), zoomRange.current.max),
    };
    const began = performance.now();
    let frame = 0;
    const step = (now: number) => {
      const t = Math.min((now - began) / FLY_MS, 1);
      const e = t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;
      setCamera({
        target: [start.target[0] + (end.target[0] - start.target[0]) * e, start.target[1] + (end.target[1] - start.target[1]) * e],
        zoom: start.zoom + (end.zoom - start.zoom) * e,
      });
      if (t < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [flyTo?.key, view.section_id, size !== null, camera !== null]); // eslint-disable-line react-hooks/exhaustive-deps -- camera: a viewer mounted by the fly-to itself flies once it has fitted

  const keepUnder = single === "stricter" ? compared : null;
  const { background, highlighted } = useMemo(() => moleculeBuffers(section, genes, visibleGenes, keepUnder), [section, genes, visibleGenes, keepUnder]);
  const excludedUnder = compare ?? (single === "excluded" ? compared : null);
  const excluded = useMemo(
    () => (excludedUnder ? excludedBuffer(section, excludedUnder, visibleGenes, excludedCellType) : buffer(0, false)),
    [section, excludedUnder, visibleGenes, excludedCellType],
  );
  const cellColours = useMemo(() => cellRingColours(section, cellTypes), [section, cellTypes]);

  const width = size?.width ?? 1;
  const splitX = compare ? Math.round(width * split) : width;
  const views = compare
    ? [
        new OrthographicView({ id: "left", x: 0, width: splitX, flipY: true, controller: { dragRotate: false } }),
        new OrthographicView({ id: "right", x: splitX, width: width - splitX, flipY: true, controller: { dragRotate: false } }),
      ]
    : [new OrthographicView({ id: "left", flipY: true, controller: { dragRotate: false } })];

  // Each view's own target, so a world point lands on the same screen pixel in both halves.
  const viewState = camera
    ? Object.fromEntries(
        views.map((v) => {
          const x = v.id === "right" ? splitX : 0;
          const w = v.id === "right" ? width - splitX : splitX;
          const shift = (x + w / 2 - width / 2) / 2 ** camera.zoom;
          return [v.id, { target: [camera.target[0] + shift, camera.target[1], 0] as [number, number, number], zoom: camera.zoom, minZoom: zoomRange.current.min, maxZoom: zoomRange.current.max }];
        }),
      )
    : undefined;

  const onViewStateChange = ({ viewId, viewState: next }: { viewId: string; viewState: { target: number[]; zoom: number } }) => {
    const x = viewId === "right" ? splitX : 0;
    const w = viewId === "right" ? width - splitX : splitX;
    const zoom = Math.min(Math.max(next.zoom, zoomRange.current.min), zoomRange.current.max);
    const shift = (x + w / 2 - width / 2) / 2 ** zoom;
    setCamera({ target: [(next.target[0] ?? 0) - shift, next.target[1] ?? 0], zoom });
  };

  const sharedLayers = (side: string) => [
    new PathLayer<StructureMask>({
      id: `${side}-structures`,
      data: view.structures,
      getPath: (s) => [...s.outline, s.outline[0] ?? [0, 0]].map((point): [number, number] => [point[0] ?? 0, point[1] ?? 0]),
      getColor: [...rgbOf(STRUCTURE_OUTLINE), 230],
      getWidth: 2,
      widthUnits: "pixels",
      pickable: true,
    }),
    new ScatterplotLayer({
      id: `${side}-nuclei`,
      data: {
        length: section.cellCount,
        attributes: {
          getPosition: { value: section.cellPositions, size: 2 },
          getRadius: { value: section.nucleusRadius, size: 1 },
          getLineColor: { value: cellColours, size: 4, normalized: true },
        },
      },
      radiusUnits: "common",
      filled: false,
      stroked: true,
      getLineWidth: 1.25,
      lineWidthUnits: "pixels",
      pickable: true,
    }),
    new ScatterplotLayer({
      id: `${side}-molecules-background`,
      data: { length: background.length, attributes: { getPosition: { value: background.positions, size: 2 } } },
      getFillColor: [...rgbOf(OTHER_MOLECULE), BACKGROUND_ALPHA],
      getRadius: 0.45,
      radiusUnits: "common",
      radiusMinPixels: 1,
      pickable: true,
    }),
    new ScatterplotLayer({
      id: `${side}-molecules-highlighted`,
      data: {
        length: highlighted.length,
        attributes: {
          getPosition: { value: highlighted.positions, size: 2 },
          getFillColor: { value: highlighted.colours ?? new Uint8Array(0), size: 4, normalized: true },
        },
      },
      getRadius: 0.45,
      radiusUnits: "common",
      radiusMinPixels: 1.75,
      pickable: true,
    }),
    ...(evidenceRegion && evidenceRegion.section_id === view.section_id
      ? [
          new PathLayer<Region>({
            id: `${side}-evidence-region`,
            data: [evidenceRegion],
            getPath: (r) => [[r.x0, r.y0], [r.x1, r.y0], [r.x1, r.y1], [r.x0, r.y1], [r.x0, r.y0]],
            getColor: [...rgbOf(EVIDENCE_REGION), 220],
            getWidth: 1.5,
            widthUnits: "pixels",
          }),
        ]
      : []),
    ...(box && box.section_id === view.section_id
      ? [
          new PathLayer<Region>({
            id: `${side}-user-box`,
            data: [box],
            getPath: (r) => [[r.x0, r.y0], [r.x1, r.y0], [r.x1, r.y1], [r.x0, r.y1], [r.x0, r.y0]],
            getColor: [255, 255, 255, 240],
            getWidth: 2,
            widthUnits: "pixels",
          }),
        ]
      : []),
  ];
  const excludedLayer = (side: string) =>
    new ScatterplotLayer({
      id: `${side}-molecules-excluded`,
      data: { length: excluded.length, attributes: { getPosition: { value: excluded.positions, size: 2 } } },
      getFillColor: [...rgbOf(EXCLUDED_MOLECULE), 255],
      getRadius: 0.55,
      radiusUnits: "common",
      radiusMinPixels: 2,
      pickable: true,
    });

  const layers = [
    ...sharedLayers("left"),
    ...(single === "excluded" ? [excludedLayer("left")] : []),
    ...(compare ? [...sharedLayers("right"), excludedLayer("right")] : []),
  ];

  // Box drawing on the left (or only) view, from screen pixels to section micrometres through that view's camera.
  const toSection = (clientX: number, clientY: number): [number, number] | null => {
    const rect = container.current?.getBoundingClientRect();
    const left = viewState?.left;
    if (!rect || !left || !camera) return null;
    const scale = 2 ** camera.zoom;
    return [left.target[0] + (clientX - rect.left - splitX / 2) / scale, left.target[1] + (clientY - rect.top - rect.height / 2) / scale];
  };
  const drag = useRef<[number, number] | null>(null);
  const [draft, setDraft] = useState<Region | null>(null);
  const boxOf = (a: [number, number], b: [number, number]): Region => {
    const { x0, y0, x1, y1 } = view.region;
    const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
    return {
      section_id: view.section_id,
      x0: clamp(Math.min(a[0], b[0]), x0, x1),
      x1: clamp(Math.max(a[0], b[0]), x0, x1),
      y0: clamp(Math.min(a[1], b[1]), y0, y1),
      y1: clamp(Math.max(a[1], b[1]), y0, y1),
    };
  };
  const singleLabel =
    single === "stricter"
      ? `Stricter assignment · ${CONDITION_NAMES[compared ?? ""] ?? compared}: only molecules it still counts toward a cell`
      : single === "excluded"
        ? `Usual assignment · ${excluded.length.toLocaleString()} molecules the ${CONDITION_NAMES[compared ?? ""] ?? compared} rule drops, in yellow${excludedCellType ? ` (in ${excludedCellType} cells)` : ""}`
        : compared
          ? "Usual assignment (default)"
          : null;

  return (
    <div ref={container} className="relative h-full w-full overflow-hidden rounded-lg border border-line bg-surface">
      {size && viewState && (
        <DeckGL
          key={view.section_id}
          views={views}
          viewState={viewState}
          onViewStateChange={onViewStateChange as never}
          layers={layers}
          layerFilter={({ layer, viewport }) => layer.id.startsWith(`${viewport.id}-`)}
          getTooltip={(info) => tooltip(info, section, background, highlighted, excluded, compared)}
        />
      )}
      {boxMode && (
        <div
          data-testid="rna-box-overlay"
          className="absolute inset-y-0 left-0 z-10 cursor-crosshair touch-none"
          style={{ width: splitX }}
          onPointerDown={(e) => {
            const p = toSection(e.clientX, e.clientY);
            if (!p || e.button !== 0) return;
            e.currentTarget.setPointerCapture(e.pointerId);
            drag.current = p;
          }}
          onPointerMove={(e) => {
            const p = drag.current && toSection(e.clientX, e.clientY);
            if (drag.current && p) setDraft(boxOf(drag.current, p));
          }}
          onPointerUp={(e) => {
            const s = drag.current;
            drag.current = null;
            setDraft(null);
            const p = s && toSection(e.clientX, e.clientY);
            if (!s || !p) return;
            const r = boxOf(s, p);
            onBox?.(r.x1 - r.x0 > 2 && r.y1 - r.y0 > 2 ? r : null);
          }}
        >
          {draft && camera && viewState?.left && (
            <div
              className="pointer-events-none absolute border border-white/90 bg-white/10"
              style={{
                left: splitX / 2 + (draft.x0 - viewState.left.target[0]) * 2 ** camera.zoom,
                top: (size?.height ?? 0) / 2 + (draft.y0 - viewState.left.target[1]) * 2 ** camera.zoom,
                width: (draft.x1 - draft.x0) * 2 ** camera.zoom,
                height: (draft.y1 - draft.y0) * 2 ** camera.zoom,
              }}
            />
          )}
        </div>
      )}
      {singleLabel && (
        <div data-testid="rna-display-label" className="pointer-events-none absolute left-3 top-2 max-w-[80%] rounded bg-panel/85 px-2 py-0.5 text-xs text-ink-2">
          {single === "excluded" && <span style={{ color: EXCLUDED_MOLECULE }}>● </span>}
          {singleLabel}
        </div>
      )}
      {compare && size && (
        <>
          <div
            role="slider"
            aria-label="Split between the default condition and the compared condition"
            aria-valuemin={10}
            aria-valuemax={90}
            aria-valuenow={Math.round(split * 100)}
            tabIndex={0}
            className="absolute top-0 z-10 h-full w-3 -translate-x-1/2 cursor-ew-resize"
            style={{ left: splitX }}
            onKeyDown={(e) => {
              if (e.key === "ArrowLeft") setSplit((s) => Math.max(0.1, s - 0.05));
              if (e.key === "ArrowRight") setSplit((s) => Math.min(0.9, s + 0.05));
            }}
            onPointerDown={(e) => {
              const box = container.current?.getBoundingClientRect();
              if (!box) return;
              (e.target as HTMLElement).setPointerCapture(e.pointerId);
              const move = (event: PointerEvent) => setSplit(Math.min(0.9, Math.max(0.1, (event.clientX - box.left) / box.width)));
              const up = () => {
                window.removeEventListener("pointermove", move);
                window.removeEventListener("pointerup", up);
              };
              window.addEventListener("pointermove", move);
              window.addEventListener("pointerup", up);
            }}
          >
            <div className="mx-auto h-full w-0.5 bg-ink-2/80" />
          </div>
          <div className="pointer-events-none absolute top-2 left-1/2 -translate-x-1/2 rounded bg-panel/85 px-2 py-0.5 text-[11px] text-ink-3">Same section, different counting rules</div>
          <div className="pointer-events-none absolute left-3 top-8 rounded bg-panel/80 px-2 py-0.5 text-xs text-ink-2">usual (default)</div>
          <div className="pointer-events-none absolute right-3 top-8 rounded bg-panel/80 px-2 py-0.5 text-xs text-ink-2">
            {CONDITION_NAMES[compare] ?? compare} · <span style={{ color: EXCLUDED_MOLECULE }}>●</span>{" "}
            {excluded.length.toLocaleString()} excluded molecules shown
            {excludedCellType ? ` (in ${excludedCellType} cells)` : ""}
          </div>
        </>
      )}
      <div className="pointer-events-none absolute bottom-2 left-3 text-xs text-ink-3">
        <span className="font-medium text-ink-2">Rendered from molecules{view.synthetic ? " · synthetic section" : ""}</span> ·{" "}
        {view.section_name ? `${view.section_name} (${view.section_id})` : view.section_id} ·{" "}
        {section.moleculeCount.toLocaleString()} molecules · micrometres · drag to pan, scroll to zoom
      </div>
    </div>
  );
}

function moleculeBuffers(
  section: SectionArrays,
  genes: Highlight,
  visibleGenes: ReadonlySet<string> | null,
  keepUnder: ConditionName | null,
): { background: MoleculeBuffer; highlighted: MoleculeBuffer } {
  const names = section.view.genes;
  const visible = names.map((gene) => visibleGenes === null || visibleGenes.has(gene));
  const slot = names.map((gene) => genes.indexOf(gene));
  const slotColour = GENE_SLOTS.map((hex) => rgbOf(hex));
  const keepBit = keepUnder === null ? undefined : (section.view.molecules.condition_bits as Record<string, number | undefined>)[keepUnder];
  const kept = (i: number) => keepBit === undefined || (((section.inclusionBits[i] ?? 0) >> keepBit) & 1) === 1;
  let highlightedCount = 0;
  let backgroundCount = 0;
  for (let i = 0; i < section.moleculeCount; i++) {
    const g = section.geneIndex[i] ?? 0;
    if (!visible[g] || !kept(i)) continue;
    if ((slot[g] ?? -1) >= 0) highlightedCount++;
    else backgroundCount++;
  }
  const background = buffer(backgroundCount, false);
  const highlighted = buffer(highlightedCount, true);
  let b = 0;
  let h = 0;
  for (let i = 0; i < section.moleculeCount; i++) {
    const g = section.geneIndex[i] ?? 0;
    if (!visible[g] || !kept(i)) continue;
    const s = slot[g] ?? -1;
    const x = section.positions[2 * i] ?? 0;
    const y = section.positions[2 * i + 1] ?? 0;
    if (s >= 0) {
      highlighted.positions[2 * h] = x;
      highlighted.positions[2 * h + 1] = y;
      const [r, gr, bl] = slotColour[s] ?? [255, 255, 255];
      highlighted.colours?.set([r, gr, bl, 255], 4 * h);
      highlighted.index[h++] = i;
    } else {
      background.positions[2 * b] = x;
      background.positions[2 * b + 1] = y;
      background.index[b++] = i;
    }
  }
  return { background, highlighted };
}

/** Molecules the default condition counts toward a cell and `condition` does not, among the visible genes. */
function excludedBuffer(
  section: SectionArrays,
  condition: ConditionName,
  visibleGenes: ReadonlySet<string> | null,
  cellType: string | null,
): MoleculeBuffer {
  const bits = section.view.molecules.condition_bits as Record<string, number | undefined>;
  const defaultBit = bits.default;
  const conditionBit = bits[condition];
  if (defaultBit === undefined || conditionBit === undefined) return buffer(0, false);
  const visible = section.view.genes.map((gene) => visibleGenes === null || visibleGenes.has(gene));
  const typeIndex = cellType === null ? -1 : section.view.cell_types.indexOf(cellType);
  const isExcluded = (i: number) => {
    const value = section.inclusionBits[i] ?? 0;
    if (((value >> defaultBit) & 1) !== 1 || ((value >> conditionBit) & 1) !== 0 || !(visible[section.geneIndex[i] ?? 0] ?? false)) return false;
    return typeIndex < 0 || section.cellTypeIndex[section.cellIndex[i] ?? 0] === typeIndex;
  };
  let count = 0;
  for (let i = 0; i < section.moleculeCount; i++) if (isExcluded(i)) count++;
  const out = buffer(count, false);
  let n = 0;
  for (let i = 0; i < section.moleculeCount; i++) {
    if (!isExcluded(i)) continue;
    out.positions[2 * n] = section.positions[2 * i] ?? 0;
    out.positions[2 * n + 1] = section.positions[2 * i + 1] ?? 0;
    out.index[n++] = i;
  }
  return out;
}

function buffer(length: number, coloured: boolean): MoleculeBuffer {
  return {
    length,
    positions: new Float32Array(length * 2),
    colours: coloured ? new Uint8Array(length * 4) : null,
    index: new Uint32Array(length),
  };
}

function cellRingColours(section: SectionArrays, cellTypes: Highlight): Uint8Array {
  const palette = section.view.cell_types.map((name) => {
    const slot = cellTypes.indexOf(name);
    return slot >= 0 ? [...rgbOf(CELL_TYPE_SLOTS[slot] ?? OTHER_CELL), 255] : [...rgbOf(OTHER_CELL), 110];
  });
  const colours = new Uint8Array(section.cellCount * 4);
  for (let i = 0; i < section.cellCount; i++) colours.set(palette[section.cellTypeIndex[i] ?? 0] ?? [0, 0, 0, 0], 4 * i);
  return colours;
}

function tooltip(
  info: PickingInfo,
  section: SectionArrays,
  background: MoleculeBuffer,
  highlighted: MoleculeBuffer,
  excluded: MoleculeBuffer,
  compare: ConditionName | null,
): { text: string } | null {
  if (info.index < 0) return null;
  const view = section.view;
  const layer = (info.layer?.id ?? "").replace(/^(left|right)-/, "");
  if (layer.startsWith("molecules-")) {
    const source = layer === "molecules-highlighted" ? highlighted : layer === "molecules-excluded" ? excluded : background;
    const i = source.index[info.index];
    if (i === undefined) return null;
    const gene = view.genes[section.geneIndex[i] ?? 0] ?? "?";
    const cell = section.cellIndex[i] ?? -1;
    if (cell < 0) return { text: `${gene} molecule, unassigned` };
    const cellType = view.cell_types[section.cellTypeIndex[cell] ?? 0] ?? "?";
    const condition = compare ?? "nucleus_only";
    const kept = includedUnder(section, i, condition);
    const name = CONDITION_NAMES[condition] ?? condition;
    const status = kept === null ? "" : kept ? `\nkept under ${name}` : `\nexcluded under ${name}`;
    return { text: `${gene} molecule\ncounted toward ${view.cells.cell_id[cell] ?? "?"} (${cellType}) by default${status}` };
  }
  if (layer === "nuclei") {
    const cellType = view.cell_types[section.cellTypeIndex[info.index] ?? 0] ?? "?";
    return { text: `${view.cells.cell_id[info.index] ?? "?"}: ${cellType}\nnucleus drawn as a circle (approximation)` };
  }
  const structure = info.object as StructureMask | undefined;
  return structure?.kind ? { text: `${structure.kind} outline (${structure.source})` } : null;
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
