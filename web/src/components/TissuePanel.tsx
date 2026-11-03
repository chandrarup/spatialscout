// The tissue panel: section picker, label rule, compared condition and gene filter above the viewer, and the
// legend below it. It loads a whole section as a packed region view and decodes it once into typed arrays.
// A focus (from "Fly to evidence") opens the finding's section under its label rule, locks the gene filter to
// the finding's genes, splits the view against the ranking condition and flies into the evidence region.
import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { ConditionName, DatasetManifest, Region } from "../contracts/generated";
import { type SectionArrays, decodeSection } from "../packed";
import { type Highlight, MAX_HIGHLIGHTED, toggleHighlight } from "../palette";
import { Viewer } from "./Viewer";
import { ALL_GENES, ViewerControls, visibleGenes } from "./ViewerControls";
import { ViewerLegend } from "./ViewerLegend";

export interface TissueFocus {
  key: number;
  sectionId: string;
  labelRuleId: string;
  /** The finding's genes: the gene filter locks to them. */
  genes: string[];
  /** Up to three genes to colour, and the population's cell type. */
  highlight: string[];
  cellType: string;
  condition: ConditionName;
  region: Region;
}

interface Props {
  /** The dataset whose first section opens first. */
  defaultDatasetId: string | null;
  /** Called with the open section's dataset manifest and section id. */
  onShow: (manifest: DatasetManifest, sectionId: string) => void;
  focus: TissueFocus | null;
}

const PREFERRED_GENES = ["LRP2", "NPHS1", "CUBN"];
const PREFERRED_CELL_TYPES = ["Podocyte", "PT", "Endothelial"];

function defaults(available: string[], preferred: string[]): Highlight {
  const chosen = preferred.filter((name) => available.includes(name));
  for (const name of available) if (chosen.length < MAX_HIGHLIGHTED && !chosen.includes(name)) chosen.push(name);
  return chosen.slice(0, MAX_HIGHLIGHTED);
}

export function TissuePanel({ defaultDatasetId, onShow, focus }: Props) {
  const [datasets, setDatasets] = useState<DatasetManifest[]>([]);
  const [sectionId, setSectionId] = useState<string | null>(null);
  const [labelRuleId, setLabelRuleId] = useState<string | null>(null);
  const [section, setSection] = useState<SectionArrays | null>(null);
  const [loading, setLoading] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [genes, setGenes] = useState<Highlight>([]);
  const [cellTypes, setCellTypes] = useState<Highlight>([]);
  const [geneFilter, setGeneFilter] = useState(ALL_GENES);
  const [compare, setCompare] = useState<ConditionName | null>(null);
  const [lockedGenes, setLockedGenes] = useState<string[] | null>(null);

  useEffect(() => {
    if (defaultDatasetId === null) return;
    api
      .datasets()
      .then((all) => {
        setDatasets(all);
        const first = (all.find((d) => d.dataset_id === defaultDatasetId) ?? all[0])?.sections[0];
        if (first) setSectionId((current) => current ?? first.section_id);
      })
      .catch((error: unknown) => setProblem(String(error)));
  }, [defaultDatasetId]);

  useEffect(() => {
    if (!focus) return;
    setSectionId(focus.sectionId);
    setLabelRuleId(focus.labelRuleId);
    setLockedGenes(focus.genes);
    setGenes(focus.highlight.slice(0, MAX_HIGHLIGHTED));
    setCellTypes([focus.cellType]);
    setCompare(focus.condition);
  }, [focus]);

  const manifest = useMemo(
    () => datasets.find((d) => d.sections.some((s) => s.section_id === sectionId)) ?? null,
    [datasets, sectionId],
  );

  useEffect(() => {
    if (!sectionId || !manifest) return;
    onShow(manifest, sectionId);
    let current = true;
    setLoading(true);
    setProblem(null);
    api
      .packedRegionView(sectionId, labelRuleId ?? undefined)
      .then((view) => {
        if (!current) return;
        const decoded = decodeSection(view);
        setSection(decoded);
        setGenes((g) => (g.some((name) => name && view.genes.includes(name)) ? g : defaults(view.genes, PREFERRED_GENES)));
        setCellTypes((c) => (c.some((name) => name && view.cell_types.includes(name)) ? c : defaults(view.cell_types, PREFERRED_CELL_TYPES)));
      })
      .catch((error: unknown) => current && setProblem(String(error)))
      .finally(() => current && setLoading(false));
    return () => {
      current = false;
    };
  }, [sectionId, labelRuleId, manifest, onShow]);

  const pickSection = (id: string) => {
    const next = datasets.find((d) => d.sections.some((s) => s.section_id === id));
    if (next && next.dataset_id !== manifest?.dataset_id) setLabelRuleId(null);
    setSectionId(id);
  };

  const visible = useMemo(
    () => (lockedGenes ? new Set(lockedGenes) : visibleGenes(geneFilter, genes)),
    [lockedGenes, geneFilter, genes],
  );
  const labelRuleIds = manifest?.label_rule_ids ?? [];
  const conditions = section ? Object.keys(section.view.molecules.condition_bits) : [];
  const focused = focus && section && focus.sectionId === section.view.section_id ? focus : null;

  return (
    <section aria-label="Tissue viewer" className="flex min-h-[28rem] flex-col gap-3">
      <ViewerControls
        datasets={datasets}
        sectionId={sectionId}
        onSection={pickSection}
        labelRuleIds={labelRuleIds}
        labelRuleId={labelRuleId ?? section?.view.label_rule_id ?? labelRuleIds[0] ?? null}
        onLabelRule={setLabelRuleId}
        genes={section?.view.genes ?? []}
        geneFilter={geneFilter}
        onGeneFilter={setGeneFilter}
        conditions={conditions}
        compare={compare}
        onCompare={setCompare}
        lockedGenes={lockedGenes}
        onUnlock={() => setLockedGenes(null)}
      />
      <div className="relative min-h-0 flex-1">
        {section ? (
          <Viewer
            section={section}
            genes={genes}
            cellTypes={cellTypes}
            visibleGenes={visible}
            compare={compare}
            flyTo={focused ? { region: focused.region, key: focused.key } : null}
            evidenceRegion={focused?.region ?? null}
          />
        ) : (
          <div className="flex h-full items-center justify-center rounded-lg border border-line text-sm text-ink-3">
            {problem ? "" : "Loading the section…"}
          </div>
        )}
        {(loading || problem) && (
          <div
            role={problem ? "alert" : "status"}
            className={`absolute left-3 top-10 max-w-[80%] rounded-md border px-3 py-2 text-xs ${
              problem ? "border-red-500/40 bg-red-500/10 text-red-300" : "border-line bg-panel text-ink-2"
            }`}
          >
            {problem ?? "Loading the whole section…"}
          </div>
        )}
      </div>
      {section && (
        <ViewerLegend
          view={section.view}
          genes={genes}
          cellTypes={cellTypes}
          onToggleGene={(gene) => setGenes((current) => toggleHighlight(current, gene))}
          onToggleCellType={(cellType) => setCellTypes((current) => toggleHighlight(current, cellType))}
        />
      )}
    </section>
  );
}
