// Decode a packed region view (base64 little-endian columns) into typed arrays that deck.gl draws directly,
// without one JavaScript object per molecule.
import type { PackedColumn, PackedRegionView } from "./contracts/generated";

export interface SectionArrays {
  view: PackedRegionView;
  moleculeCount: number;
  /** Interleaved x, y per molecule, micrometres. */
  positions: Float32Array;
  geneIndex: Uint8Array;
  /** Index into the cells, -1 for an unassigned molecule. */
  cellIndex: Int32Array;
  inclusionBits: Uint8Array;
  cellCount: number;
  cellPositions: Float32Array;
  nucleusRadius: Float32Array;
  cellTypeIndex: Uint8Array;
}

const littleEndian = new Uint8Array(new Uint16Array([1]).buffer)[0] === 1;

function bytes(column: PackedColumn): ArrayBuffer {
  const text = atob(column.data);
  const out = new Uint8Array(text.length);
  for (let i = 0; i < text.length; i++) out[i] = text.charCodeAt(i);
  if (!littleEndian && column.dtype !== "uint8") throw new Error("big-endian browsers are not supported");
  return out.buffer;
}

const float32 = (column: PackedColumn) => new Float32Array(bytes(column));
const uint8 = (column: PackedColumn) => new Uint8Array(bytes(column));
const int32 = (column: PackedColumn) => new Int32Array(bytes(column));

function interleave(xs: Float32Array, ys: Float32Array): Float32Array {
  const out = new Float32Array(xs.length * 2);
  for (let i = 0; i < xs.length; i++) {
    out[2 * i] = xs[i] ?? 0;
    out[2 * i + 1] = ys[i] ?? 0;
  }
  return out;
}

export function decodeSection(view: PackedRegionView): SectionArrays {
  const m = view.molecules;
  const c = view.cells;
  return {
    view,
    moleculeCount: m.count,
    positions: interleave(float32(m.x), float32(m.y)),
    geneIndex: uint8(m.gene_index),
    cellIndex: int32(m.cell_index),
    inclusionBits: uint8(m.inclusion_bits),
    cellCount: c.count,
    cellPositions: interleave(float32(c.x), float32(c.y)),
    nucleusRadius: float32(c.nucleus_radius),
    cellTypeIndex: uint8(c.cell_type_index),
  };
}

/** Whether molecule i counts toward its cell under a condition, or null when the view lacks that condition. */
export function includedUnder(section: SectionArrays, i: number, condition: string): boolean | null {
  const bit = (section.view.molecules.condition_bits as Record<string, number | undefined>)[condition];
  if (bit === undefined) return null;
  return (((section.inclusionBits[i] ?? 0) >> bit) & 1) === 1;
}
