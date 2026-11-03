// Data colours for the viewer, validated on the dark surface #111214 with the dataviz palette checker
// (`--mode dark --pairs all`): each triple passes the CVD and normal-vision floors on its own. Points and
// rings show at most three highlighted categories each, in fixed slots; every other category is neutral
// grey, and the legend plus the hover tooltip name every mark, so identity never rests on colour alone.
// Yellow is reserved for excluded molecules (ticket 05).

export type Rgb = [number, number, number];

function rgb(hex: string): Rgb {
  const value = Number.parseInt(hex.slice(1), 16);
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}

export const GENE_SLOTS: readonly string[] = ["#3987e5", "#d95926", "#199e70"]; // blue, orange, aqua
export const CELL_TYPE_SLOTS: readonly string[] = ["#d55181", "#9085e9", "#008300"]; // magenta, violet, green
export const OTHER_MOLECULE = "#6b6f76";
export const OTHER_CELL = "#8e8d86";
export const STRUCTURE_OUTLINE = "#4dd0e1"; // cyan
export const EXCLUDED_MOLECULE = "#f5c518"; // yellow, reserved for excluded molecules
export const EVIDENCE_REGION = "#ffffff";
export const MAX_HIGHLIGHTED = 3;

/** Highlighted categories keep their slot while highlighted: colour follows the entity, never its rank. */
export type Highlight = (string | null)[];

export function toggleHighlight(highlight: Highlight, name: string): Highlight {
  const slot = highlight.indexOf(name);
  if (slot >= 0) return highlight.map((h) => (h === name ? null : h));
  const free = highlight.indexOf(null);
  if (free >= 0) return highlight.map((h, i) => (i === free ? name : h));
  if (highlight.length < MAX_HIGHLIGHTED) return [...highlight, name];
  return highlight;
}

export function colourOf(highlight: Highlight, slots: readonly string[], name: string, other: string): string {
  const slot = highlight.indexOf(name);
  return slot >= 0 ? (slots[slot] ?? other) : other;
}

export function rgbOf(hex: string): Rgb {
  return rgb(hex);
}
