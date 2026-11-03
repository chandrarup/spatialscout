// The tissue viewer: molecules as points coloured by gene, nuclei as rings coloured by cell type label,
// and structure outlines, in section micrometres. Drag to pan, scroll or pinch to zoom.
//
// A whole section (hundreds of thousands to a few million molecules) is drawn from typed arrays as deck.gl
// binary attributes. A highlight or filter change rebuilds two flat buffers in one pass: grey background
// molecules underneath, coloured ones on top. No per-molecule objects are created and nothing is sorted.
import { OrthographicView, type PickingInfo } from "@deck.gl/core";
import { PathLayer, ScatterplotLayer } from "@deck.gl/layers";
import DeckGL from "@deck.gl/react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { StructureMask } from "../contracts/generated";
import { type SectionArrays, includedUnder } from "../packed";
import {
  CELL_TYPE_SLOTS,
  GENE_SLOTS,
  type Highlight,
  OTHER_CELL,
  OTHER_MOLECULE,
  STRUCTURE_OUTLINE,
  rgbOf,
} from "../palette";

interface Props {
  section: SectionArrays;
  genes: Highlight;
  cellTypes: Highlight;
  /** Genes whose molecules are drawn; null draws every gene. */
  visibleGenes: ReadonlySet<string> | null;
}

/** Molecules of one layer: positions, optional per-molecule colours, and each point's molecule index. */
interface MoleculeBuffer {
  length: number;
  positions: Float32Array;
  colours: Uint8Array | null;
  index: Uint32Array;
}

const VIEW = new OrthographicView({ id: "section", flipY: true });
const BACKGROUND_ALPHA = 150;

export function Viewer({ section, genes, cellTypes, visibleGenes }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const size = useSize(container);
  const view = section.view;

  const initialViewState = useMemo(() => {
    const { x0, y0, x1, y1 } = view.region;
    const width = Math.max(x1 - x0, 1);
    const height = Math.max(y1 - y0, 1);
    const scale = size ? Math.min(size.width / width, size.height / height) * 0.9 : 1;
    const fit = Math.log2(scale);
    // From a little wider than the whole section down to single molecules (2^8 = 256x the fitted scale).
    return { target: [(x0 + x1) / 2, (y0 + y1) / 2, 0] as [number, number, number], zoom: fit, minZoom: fit - 2, maxZoom: fit + 8 };
  }, [view, size !== null]); // fit once the container has a size; afterwards the user pans and zooms

  const { background, highlighted } = useMemo(() => moleculeBuffers(section, genes, visibleGenes), [section, genes, visibleGenes]);
  const cellColours = useMemo(() => cellRingColours(section, cellTypes), [section, cellTypes]);

  const layers = [
    new PathLayer<StructureMask>({
      id: "structures",
      data: view.structures,
      getPath: (s) => [...s.outline, s.outline[0] ?? [0, 0]].map((point): [number, number] => [point[0] ?? 0, point[1] ?? 0]),
      getColor: [...rgbOf(STRUCTURE_OUTLINE), 230],
      getWidth: 2,
      widthUnits: "pixels",
      pickable: true,
    }),
    new ScatterplotLayer({
      id: "nuclei",
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
      id: "molecules-background",
      data: { length: background.length, attributes: { getPosition: { value: background.positions, size: 2 } } },
      getFillColor: [...rgbOf(OTHER_MOLECULE), BACKGROUND_ALPHA],
      getRadius: 0.45,
      radiusUnits: "common",
      radiusMinPixels: 1,
      pickable: true,
    }),
    new ScatterplotLayer({
      id: "molecules-highlighted",
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
  ];

  return (
    <div ref={container} className="relative h-full w-full overflow-hidden rounded-lg border border-line bg-surface">
      {size && (
        <DeckGL
          key={view.section_id}
          views={VIEW}
          initialViewState={initialViewState}
          controller={{ dragRotate: false }}
          layers={layers}
          getTooltip={(info) => tooltip(info, section, background, highlighted)}
        />
      )}
      <div className="pointer-events-none absolute bottom-2 left-3 text-xs text-ink-3">
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
): { background: MoleculeBuffer; highlighted: MoleculeBuffer } {
  const names = section.view.genes;
  const visible = names.map((gene) => visibleGenes === null || visibleGenes.has(gene));
  const slot = names.map((gene) => genes.indexOf(gene));
  const slotColour = GENE_SLOTS.map((hex) => rgbOf(hex));
  let highlightedCount = 0;
  let backgroundCount = 0;
  for (let i = 0; i < section.moleculeCount; i++) {
    const g = section.geneIndex[i] ?? 0;
    if (!visible[g]) continue;
    if ((slot[g] ?? -1) >= 0) highlightedCount++;
    else backgroundCount++;
  }
  const background = buffer(backgroundCount, false);
  const highlighted = buffer(highlightedCount, true);
  let b = 0;
  let h = 0;
  for (let i = 0; i < section.moleculeCount; i++) {
    const g = section.geneIndex[i] ?? 0;
    if (!visible[g]) continue;
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

function tooltip(info: PickingInfo, section: SectionArrays, background: MoleculeBuffer, highlighted: MoleculeBuffer): { text: string } | null {
  if (info.index < 0) return null;
  const view = section.view;
  const layer = info.layer?.id;
  if (layer === "molecules-background" || layer === "molecules-highlighted") {
    const i = (layer === "molecules-highlighted" ? highlighted : background).index[info.index];
    if (i === undefined) return null;
    const gene = view.genes[section.geneIndex[i] ?? 0] ?? "?";
    const cell = section.cellIndex[i] ?? -1;
    if (cell < 0) return { text: `${gene} molecule, unassigned` };
    const cellType = view.cell_types[section.cellTypeIndex[cell] ?? 0] ?? "?";
    const nuclear = includedUnder(section, i, "nucleus_only");
    const nucleus = nuclear === null ? "" : nuclear ? "\nover the nucleus" : "\noutside the nucleus: nucleus-only excludes it";
    return { text: `${gene} molecule\ncounted toward ${view.cells.cell_id[cell] ?? "?"} (${cellType})${nucleus}` };
  }
  if (layer === "nuclei") {
    const cellType = view.cell_types[section.cellTypeIndex[info.index] ?? 0] ?? "?";
    return { text: `${view.cells.cell_id[info.index] ?? "?"}: ${cellType}\nnucleus drawn as a circle (approximation)` };
  }
  const structure = info.object as StructureMask | undefined;
  return structure ? { text: `${structure.kind} outline (${structure.source})` } : null;
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
