// The tissue panel: section picker, label rule and gene filter above the viewer, and the legend below it.
// It loads a whole section as a packed region view and decodes it once into typed arrays.
import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { DatasetManifest } from "../contracts/generated";
import { type SectionArrays, decodeSection } from "../packed";
import { type Highlight, MAX_HIGHLIGHTED, toggleHighlight } from "../palette";
import { Viewer } from "./Viewer";
import { ALL_GENES, ViewerControls, visibleGenes } from "./ViewerControls";
import { ViewerLegend } from "./ViewerLegend";

interface Props {
  /** The dataset whose first section opens first. */
  defaultDatasetId: string | null;
  /** Called with the open section's dataset manifest and section id. */
  onShow: (manifest: DatasetManifest, sectionId: string) => void;
}

const PREFERRED_GENES = ["LRP2", "NPHS1", "CUBN"];
const PREFERRED_CELL_TYPES = ["Podocyte", "PT", "Endothelial"];

function defaults(available: string[], preferred: string[]): Highlight {
  const chosen = preferred.filter((name) => available.includes(name));
  for (const name of available) if (chosen.length < MAX_HIGHLIGHTED && !chosen.includes(name)) chosen.push(name);
  return chosen.slice(0, MAX_HIGHLIGHTED);
}

export function TissuePanel({ defaultDatasetId, onShow }: Props) {
  const [datasets, setDatasets] = useState<DatasetManifest[]>([]);
  const [sectionId, setSectionId] = useState<string | null>(null);
  const [labelRuleId, setLabelRuleId] = useState<string | null>(null);
  const [section, setSection] = useState<SectionArrays | null>(null);
  const [loading, setLoading] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [genes, setGenes] = useState<Highlight>([]);
  const [cellTypes, setCellTypes] = useState<Highlight>([]);
  const [geneFilter, setGeneFilter] = useState(ALL_GENES);

  useEffect(() => {
    if (defaultDatasetId === null) return;
    api
      .datasets()
      .then((all) => {
        setDatasets(all);
        const first = (all.find((d) => d.dataset_id === defaultDatasetId) ?? all[0])?.sections[0];
        if (first) setSectionId(first.section_id);
      })
      .catch((error: unknown) => setProblem(String(error)));
  }, [defaultDatasetId]);

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

  const visible = useMemo(() => visibleGenes(geneFilter, genes), [geneFilter, genes]);
  const labelRuleIds = manifest?.label_rule_ids ?? [];

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
      />
      <div className="relative min-h-0 flex-1">
        {section ? (
          <Viewer section={section} genes={genes} cellTypes={cellTypes} visibleGenes={visible} />
        ) : (
          <div className="flex h-full items-center justify-center rounded-lg border border-line text-sm text-ink-3">
            {problem ? "" : "Loading the section…"}
          </div>
        )}
        {(loading || problem) && (
          <div
            role={problem ? "alert" : "status"}
            className={`absolute left-3 top-3 max-w-[80%] rounded-md border px-3 py-2 text-xs ${
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
