// A region the researcher selected on one tissue pane, carried unchanged from the pane to the calculation that uses
// it and to the assistant. Protein (KPMP CODEX) and RNA (GSE286184 Xenium) selections are different specimens and
// assays; neither is ever passed off as the other.
import type { Region } from "./contracts/generated";

export type Assay = "CODEX protein" | "Xenium RNA";

export interface RegionSelection {
  datasetId: string;
  /** The KPMP participant or the Xenium section the box is on. */
  sourceId: string;
  assay: Assay;
  /** Section coordinates, already mapped back from any on-screen rotation. */
  region: Region;
  units: "µm";
  markers: string[];
  /** Which pane it was drawn on, so paired selections stay apart. */
  pane: string;
  scope: "box" | "around a cell";
}

export function regionSize(r: Region): string {
  return `${Math.round(r.x1 - r.x0)} × ${Math.round(r.y1 - r.y0)} µm`;
}

export function describeSelection(s: RegionSelection): string {
  const r = s.region;
  return `${s.assay} · ${s.datasetId} ${s.sourceId} · ${regionSize(r)} at x ${Math.round(r.x0)}–${Math.round(r.x1)}, y ${Math.round(r.y0)}–${Math.round(r.y1)} ${s.units}`;
}

export function sameRegion(a: Region | null, b: Region | null): boolean {
  return !!a && !!b && a.section_id === b.section_id && a.x0 === b.x0 && a.y0 === b.y0 && a.x1 === b.x1 && a.y1 === b.y1;
}
