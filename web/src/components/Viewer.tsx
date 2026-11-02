// The tissue viewer: molecules as points coloured by gene, nuclei as rings coloured by cell type label,
// and structure outlines, in section micrometres. Drag to pan, scroll or pinch to zoom.
import { OrthographicView, type PickingInfo } from "@deck.gl/core";
import { PathLayer, ScatterplotLayer } from "@deck.gl/layers";
import DeckGL from "@deck.gl/react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { RegionView, StructureMask } from "../contracts/generated";
import {
  CELL_TYPE_SLOTS,
  GENE_SLOTS,
  type Highlight,
  OTHER_CELL,
  OTHER_MOLECULE,
  STRUCTURE_OUTLINE,
  colourOf,
  rgbOf,
} from "../palette";

interface MoleculeRow {
  x: number;
  y: number;
  gene: string;
  cell: number;
  keptByNucleusOnly: boolean | null;
}

interface CellRow {
  cellId: string;
  x: number;
  y: number;
  radius: number;
  cellType: string;
}

interface Props {
  view: RegionView;
  genes: Highlight;
  cellTypes: Highlight;
}

const VIEW = new OrthographicView({ id: "section", flipY: true });

export function Viewer({ view, genes, cellTypes }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const size = useSize(container);
  const { molecules, cells } = useMemo(() => rows(view), [view]);

  const initialViewState = useMemo(() => {
    const { x0, y0, x1, y1 } = view.region;
    const width = Math.max(x1 - x0, 1);
    const height = Math.max(y1 - y0, 1);
    const scale = size ? Math.min(size.width / width, size.height / height) * 0.9 : 1;
    const fit = Math.log2(scale);
    // From a little wider than the whole region down to single molecules (2^6 = 64x the fitted scale).
    return { target: [(x0 + x1) / 2, (y0 + y1) / 2, 0] as [number, number, number], zoom: fit, minZoom: fit - 2, maxZoom: fit + 6 };
  }, [view, size !== null]); // fit once the container has a size; afterwards the user pans and zooms

  const highlighted = (gene: string) => genes.includes(gene);
  const ordered = useMemo(
    () => [...molecules].sort((a, b) => Number(highlighted(a.gene)) - Number(highlighted(b.gene))),
    [molecules, genes], // eslint-disable-line react-hooks/exhaustive-deps
  );

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
    new ScatterplotLayer<CellRow>({
      id: "nuclei",
      data: cells,
      getPosition: (c) => [c.x, c.y],
      getRadius: (c) => c.radius,
      radiusUnits: "common",
      filled: true,
      stroked: true,
      getFillColor: (c) => [...rgbOf(colourOf(cellTypes, CELL_TYPE_SLOTS, c.cellType, OTHER_CELL)), 45],
      getLineColor: (c) => [...rgbOf(colourOf(cellTypes, CELL_TYPE_SLOTS, c.cellType, OTHER_CELL)), 255],
      getLineWidth: 1.5,
      lineWidthUnits: "pixels",
      pickable: true,
      updateTriggers: { getFillColor: cellTypes, getLineColor: cellTypes },
    }),
    new ScatterplotLayer<MoleculeRow>({
      id: "molecules",
      data: ordered,
      getPosition: (m) => [m.x, m.y],
      getRadius: 0.45,
      radiusUnits: "common",
      radiusMinPixels: 1.75,
      getFillColor: (m) =>
        highlighted(m.gene) ? [...rgbOf(colourOf(genes, GENE_SLOTS, m.gene, OTHER_MOLECULE)), 255] : [...rgbOf(OTHER_MOLECULE), 170],
      pickable: true,
      updateTriggers: { getFillColor: genes },
    }),
  ];

  return (
    <div ref={container} className="relative h-full w-full overflow-hidden rounded-lg border border-line bg-surface">
      {size && (
        <DeckGL
          views={VIEW}
          initialViewState={initialViewState}
          controller={{ dragRotate: false }}
          layers={layers}
          getTooltip={(info) => tooltip(info, cells)}
        />
      )}
      <div className="pointer-events-none absolute bottom-2 left-3 text-xs text-ink-3">
        {view.section_id} · micrometres · drag to pan, scroll to zoom
      </div>
    </div>
  );
}

function rows(view: RegionView): { molecules: MoleculeRow[]; cells: CellRow[] } {
  const m = view.molecules;
  const nucleusOnly = m.included["nucleus_only"];
  const molecules = m.x.map((x, i) => ({
    x,
    y: m.y[i] ?? 0,
    gene: view.genes[m.gene_index[i] ?? -1] ?? "?",
    cell: m.cell_index[i] ?? -1,
    keptByNucleusOnly: nucleusOnly ? nucleusOnly[i] === 1 : null,
  }));
  const c = view.cells;
  const cells = c.cell_id.map((cellId, i) => ({
    cellId,
    x: c.x[i] ?? 0,
    y: c.y[i] ?? 0,
    radius: c.nucleus_radius[i] ?? 1,
    cellType: view.cell_types[c.cell_type_index[i] ?? -1] ?? "?",
  }));
  return { molecules, cells };
}

function tooltip(info: PickingInfo, cells: CellRow[]): { text: string } | null {
  const object = info.object as MoleculeRow | CellRow | StructureMask | undefined;
  if (!object) return null;
  if (info.layer?.id === "molecules") {
    const molecule = object as MoleculeRow;
    const cell = cells[molecule.cell];
    if (!cell) return { text: `${molecule.gene} molecule, unassigned` };
    const nucleus = molecule.keptByNucleusOnly === null ? "" : molecule.keptByNucleusOnly ? "\nover the nucleus" : "\noutside the nucleus: nucleus-only excludes it";
    return { text: `${molecule.gene} molecule\ncounted toward ${cell.cellId} (${cell.cellType})${nucleus}` };
  }
  if (info.layer?.id === "nuclei") {
    const cell = object as CellRow;
    return { text: `${cell.cellId}: ${cell.cellType}\nnucleus drawn as a circle (approximation)` };
  }
  const structure = object as StructureMask;
  return { text: `${structure.kind} outline (${structure.source})` };
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
