// Legend and highlight toggles for the viewer: up to three genes and three cell types carry a colour at once.
import type { RegionView } from "../contracts/generated";
import {
  CELL_TYPE_SLOTS,
  GENE_SLOTS,
  type Highlight,
  MAX_HIGHLIGHTED,
  OTHER_CELL,
  OTHER_MOLECULE,
  STRUCTURE_OUTLINE,
  colourOf,
} from "../palette";

interface Props {
  view: Pick<RegionView, "genes" | "cell_types" | "label_rule_id" | "structures" | "notes">;
  genes: Highlight;
  cellTypes: Highlight;
  onToggleGene: (gene: string) => void;
  onToggleCellType: (cellType: string) => void;
}

export function ViewerLegend({ view, genes, cellTypes, onToggleGene, onToggleCellType }: Props) {
  return (
    <div className="flex flex-col gap-3 text-xs">
      <Group
        title="Molecules by gene"
        names={view.genes}
        highlight={genes}
        onToggle={onToggleGene}
        swatch={(name) => (
          <span className="size-2.5 rounded-full" style={{ background: colourOf(genes, GENE_SLOTS, name, OTHER_MOLECULE) }} />
        )}
      />
      <Group
        title={`Nuclei by cell type label (${view.label_rule_id})`}
        names={view.cell_types}
        highlight={cellTypes}
        onToggle={onToggleCellType}
        swatch={(name) => (
          <span
            className="size-3 rounded-full border-2"
            style={{ borderColor: colourOf(cellTypes, CELL_TYPE_SLOTS, name, OTHER_CELL) }}
          />
        )}
      />
      <div className="flex items-center gap-2 text-ink-2">
        <span className="h-0.5 w-4" style={{ background: STRUCTURE_OUTLINE }} />
        Glomerulus outline{view.structures.some((s) => s.source === "synthetic") ? " (drawn by construction)" : ""}
        {view.structures.some((s) => s.source === "sam-3.1") && (
          <span
            className="rounded border px-1.5 py-0.5 text-xs"
            style={{ borderColor: STRUCTURE_OUTLINE, color: STRUCTURE_OUTLINE }}
            title="Box-prompted SAM 3.1 outlines on a nucleus image rendered from the data. Not checked against expert annotation; never used in an evidence label."
          >
            SAM 3.1 proposal (exploratory)
          </span>
        )}
      </div>
      <ul className="space-y-1 text-ink-3">
        {view.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
    </div>
  );
}

function Group(props: {
  title: string;
  names: string[];
  highlight: Highlight;
  onToggle: (name: string) => void;
  swatch: (name: string) => React.ReactNode;
}) {
  const full = props.highlight.filter(Boolean).length >= MAX_HIGHLIGHTED;
  return (
    <fieldset>
      <legend className="mb-1.5 font-medium text-ink-2">
        {props.title} <span className="font-normal text-ink-3">· colour up to {MAX_HIGHLIGHTED}, the rest grey</span>
      </legend>
      <div className="flex flex-wrap gap-1.5">
        {props.names.map((name) => {
          const on = props.highlight.includes(name);
          return (
            <button
              key={name}
              type="button"
              aria-pressed={on}
              disabled={!on && full}
              onClick={() => props.onToggle(name)}
              className={`flex items-center gap-1.5 rounded border px-2 py-1 transition-colors ${
                on ? "border-ink-3 bg-raised text-ink" : "border-line text-ink-3 hover:text-ink-2"
              } disabled:cursor-not-allowed disabled:opacity-50`}
            >
              {props.swatch(name)}
              {name}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
