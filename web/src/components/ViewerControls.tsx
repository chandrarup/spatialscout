// Viewer controls: which section to open (grouped by dataset and group), which frozen label rule colours the
// nuclei, and which genes' molecules are drawn.
import type { ConditionName, DatasetManifest } from "../contracts/generated";
import { CONDITION_NAMES } from "./Viewer";

export const ALL_GENES = "__all__";
export const COLOURED_GENES = "__coloured__";

interface Props {
  datasets: DatasetManifest[];
  sectionId: string | null;
  onSection: (sectionId: string) => void;
  labelRuleIds: string[];
  labelRuleId: string | null;
  onLabelRule: (labelRuleId: string) => void;
  genes: string[];
  geneFilter: string;
  onGeneFilter: (filter: string) => void;
  /** Conditions the section view carries; the compared one splits the viewer against the default condition. */
  conditions: string[];
  compare: ConditionName | null;
  onCompare: (condition: ConditionName | null) => void;
  /** Genes a finding locked the filter to; null when unlocked. */
  lockedGenes: string[] | null;
  onUnlock: () => void;
}

const SELECT = "min-w-0 rounded border border-line bg-raised px-2 py-1 text-xs text-ink focus:border-accent focus:outline-none";

export function ViewerControls(props: Props) {
  return (
    <div className="flex flex-wrap items-end gap-3 text-xs">
      <label className="flex min-w-0 flex-col gap-1 text-ink-3">
        Section
        <select className={SELECT} value={props.sectionId ?? ""} onChange={(e) => props.onSection(e.target.value)}>
          {props.datasets.map((dataset) =>
            groups(dataset).map(([group, sections]) => (
              <optgroup key={`${dataset.dataset_id}/${group}`} label={`${dataset.dataset_id} · ${group}`}>
                {sections.map((s) => (
                  <option key={s.section_id} value={s.section_id}>
                    {s.name ? `${s.name} · ${s.section_id}` : s.section_id}
                    {s.molecules !== null ? ` · ${s.molecules.toLocaleString()} molecules` : ""}
                    {s.duplicate_of ? ` · same data as ${s.duplicate_of}` : ""}
                  </option>
                ))}
              </optgroup>
            )),
          )}
        </select>
      </label>
      {props.labelRuleIds.length > 1 && (
        <label className="flex flex-col gap-1 text-ink-3">
          Label rule
          <select className={SELECT} value={props.labelRuleId ?? ""} onChange={(e) => props.onLabelRule(e.target.value)}>
            {props.labelRuleIds.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </label>
      )}
      <label className="flex flex-col gap-1 text-ink-3">
        Compare with default
        <select
          className={SELECT}
          value={props.compare ?? ""}
          onChange={(e) => props.onCompare(e.target.value ? (e.target.value as ConditionName) : null)}
        >
          <option value="">No split</option>
          {props.conditions
            .filter((c) => c !== "default")
            .map((c) => (
              <option key={c} value={c}>
                {CONDITION_NAMES[c] ?? c}
              </option>
            ))}
        </select>
      </label>
      {props.lockedGenes ? (
        <div className="flex flex-col gap-1 text-ink-3">
          Gene filter
          <span className="flex items-center gap-2 rounded border border-accent/60 bg-raised px-2 py-1 text-ink">
            Locked to the finding: {props.lockedGenes.join(", ")}
            <button type="button" className="text-accent underline" onClick={props.onUnlock}>
              unlock
            </button>
          </span>
        </div>
      ) : (
      <label className="flex flex-col gap-1 text-ink-3">
        Gene filter
        <select className={SELECT} value={props.geneFilter} onChange={(e) => props.onGeneFilter(e.target.value)}>
          <option value={ALL_GENES}>All {props.genes.length} genes</option>
          <option value={COLOURED_GENES}>Coloured genes only</option>
          {props.genes.map((gene) => (
            <option key={gene} value={gene}>
              {gene} only
            </option>
          ))}
        </select>
      </label>
      )}
    </div>
  );
}

function groups(dataset: DatasetManifest): [string, DatasetManifest["sections"]][] {
  const byGroup = new Map<string, DatasetManifest["sections"]>();
  for (const section of dataset.sections) byGroup.set(section.group, [...(byGroup.get(section.group) ?? []), section]);
  return [...byGroup.entries()];
}

/** The genes whose molecules are drawn for a filter value; null means every gene. */
export function visibleGenes(filter: string, coloured: (string | null)[]): ReadonlySet<string> | null {
  if (filter === ALL_GENES) return null;
  if (filter === COLOURED_GENES) return new Set(coloured.filter((g): g is string => g !== null));
  return new Set([filter]);
}
