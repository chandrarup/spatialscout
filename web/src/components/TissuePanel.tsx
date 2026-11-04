// The tissue panel: section picker, label rule, compared condition and gene filter above the viewer, and the
// legend below it. It loads a whole section as a packed region view and decodes it once into typed arrays.
// A focus (from "Fly to evidence") opens the finding's section under its label rule, locks the gene filter to
// the finding's genes, splits the view against the ranking condition and flies into the evidence region.
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import type { AuditResult, ConditionName, DatasetManifest, Region } from "../contracts/generated";
import { type SectionArrays, decodeSection } from "../packed";
import { type Highlight, MAX_HIGHLIGHTED, toggleHighlight } from "../palette";
import { regionSize } from "../selection";
import { DepthView } from "./DepthView";
import { CONDITION_NAMES, type Display, Viewer } from "./Viewer";
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
  onShow?: (manifest: DatasetManifest, sectionId: string) => void;
  focus: TissueFocus | null;
  /** The viewer alone, without the section controls and legend: the run canvas's lens. */
  compact?: boolean;
  /** With `compact`, still show the colour legend under the viewer. */
  legend?: boolean;
}

const PREFERRED_GENES = ["LRP2", "NPHS1", "CUBN"];
const PREFERRED_CELL_TYPES = ["Podocyte", "PT", "Endothelial"];

function defaults(available: string[], preferred: string[]): Highlight {
  const chosen = preferred.filter((name) => available.includes(name));
  for (const name of available) if (chosen.length < MAX_HIGHLIGHTED && !chosen.includes(name)) chosen.push(name);
  return chosen.slice(0, MAX_HIGHLIGHTED);
}

// Decoded sections shared across stages (the run canvas and the full section view open the same one). Bounded: a
// decoded section holds several typed arrays the size of its molecule table.
const SECTION_CACHE_LIMIT = 3;
const sectionCache = new Map<string, Promise<SectionArrays>>();
function loadSection(sectionId: string, labelRuleId: string | null): Promise<SectionArrays> {
  const key = `${sectionId}|${labelRuleId ?? ""}`;
  const hit = sectionCache.get(key);
  if (hit) {
    sectionCache.delete(key);
    sectionCache.set(key, hit);
    return hit;
  }
  const load = api.packedRegionView(sectionId, labelRuleId ?? undefined).then(decodeSection);
  load.catch(() => sectionCache.delete(key));
  sectionCache.set(key, load);
  while (sectionCache.size > SECTION_CACHE_LIMIT) sectionCache.delete(sectionCache.keys().next().value!);
  return load;
}

function share(v: number | null | undefined): string {
  return v === null || v === undefined ? "–" : `${(v * 100).toFixed(1)}%`;
}

/** One box's audit: the fixed population, then each rule's kept molecules and share, then the honest label. */
function RegionResult({ result }: { result: AuditResult }) {
  const s = result.sections[0];
  if (!s) return null;
  return (
    <div data-testid="rna-region-result" className="mt-2 border-t border-line pt-2">
      <p className="text-ink">
        {s.cells_labelled.toLocaleString()} {result.population.cell_type} cells in the box
      </p>
      <ul className="mt-1 flex flex-col gap-0.5 tabular-nums">
        {s.conditions.map((c) => (
          <li key={c.condition} className="flex justify-between gap-2">
            <span className="text-ink-3">{CONDITION_NAMES[c.condition] ?? c.condition}</span>
            <span>
              {c.molecules.toLocaleString()} molecules · {share(c.observed_value)} of cells
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-1.5">
        <span className="rounded-full bg-raised px-2 py-0.5 text-[11px] font-medium text-ink">{result.label.replaceAll("_", " ")}</span>{" "}
        <span className="text-ink-3">{result.label_reason}</span>
      </p>
    </div>
  );
}

export function TissuePanel({ defaultDatasetId, onShow, focus, compact = false, legend = false }: Props) {
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
  const [display, setDisplay] = useState<Display>("usual");
  const [depthMode, setDepthMode] = useState(false);
  const [boxMode, setBoxMode] = useState(false);
  const [box, setBox] = useState<Region | null>(null);
  const [fitKey, setFitKey] = useState(0);
  const [flyKey, setFlyKey] = useState(0);
  const [regionAudit, setRegionAudit] = useState<{ key: string; result: AuditResult | null; pending: boolean; problem: string | null } | null>(null);
  const auditRequest = useRef<AbortController | null>(null);

  // A new section or label rule clears the box and its result, so a result never outlives its source.
  useEffect(() => {
    auditRequest.current?.abort();
    setBox(null);
    setRegionAudit(null);
    setBoxMode(false);
    setDepthMode(false);
  }, [sectionId, labelRuleId]);

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
    setDisplay("excluded");
    setFlyKey((k) => k + 1);
  }, [focus]);

  const manifest = useMemo(
    () => datasets.find((d) => d.sections.some((s) => s.section_id === sectionId)) ?? null,
    [datasets, sectionId],
  );

  // Loading is keyed by section and label rule alone; a parent re-render (playback, resizing) never refetches.
  const onShowRef = useRef(onShow);
  onShowRef.current = onShow;
  useEffect(() => {
    if (!sectionId || !manifest) return;
    onShowRef.current?.(manifest, sectionId);
    let current = true;
    setLoading(true);
    setProblem(null);
    loadSection(sectionId, labelRuleId)
      .then((decoded) => {
        if (!current) return;
        const view = decoded.view;
        setSection(decoded);
        setGenes((g) => (g.some((name) => name && view.genes.includes(name)) ? g : defaults(view.genes, PREFERRED_GENES)));
        setCellTypes((c) => (c.some((name) => name && view.cell_types.includes(name)) ? c : defaults(view.cell_types, PREFERRED_CELL_TYPES)));
      })
      .catch((error: unknown) => current && setProblem(String(error)))
      .finally(() => current && setLoading(false));
    return () => {
      current = false;
    };
  }, [sectionId, labelRuleId, manifest]);

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
  const condition = compare ?? (conditions.includes("nucleus_only") ? ("nucleus_only" as ConditionName) : null);
  const auditCellType = focused?.cellType ?? cellTypes[0] ?? null;
  const auditGenes = focused ? focused.highlight : genes.slice(0, 1).filter((g): g is string => !!g);
  const auditKey = box && auditCellType ? JSON.stringify([box, auditCellType, auditGenes, section?.view.label_rule_id]) : null;
  const analyse = () => {
    if (!box || !auditCellType || auditGenes.length === 0 || !auditKey) return;
    auditRequest.current?.abort();
    const controller = new AbortController();
    auditRequest.current = controller;
    const key = auditKey;
    setRegionAudit({ key, result: null, pending: true, problem: null });
    api
      .regionAudit({ region: box, cell_type: auditCellType, genes: auditGenes as [string, ...string[]], label_rule_id: section?.view.label_rule_id ?? null }, controller.signal)
      .then((result) => !controller.signal.aborted && setRegionAudit({ key, result, pending: false, problem: null }))
      .catch((error: unknown) => !controller.signal.aborted && setRegionAudit({ key, result: null, pending: false, problem: String(error) }));
  };
  const currentAudit = regionAudit && regionAudit.key === auditKey ? regionAudit : null;
  const depthRegion = box ?? focused?.region ?? null;
  const DISPLAYS: { id: Display; label: string }[] = [
    { id: "usual", label: "Usual assignment" },
    { id: "stricter", label: "Stricter assignment" },
    { id: "excluded", label: "Show excluded molecules" },
    { id: "compare", label: "Compare conditions" },
  ];
  const chip = "h-7 shrink-0 rounded-full px-2.5 text-[12px] bg-raised text-ink-2 hover:text-ink aria-pressed:bg-white aria-pressed:text-black disabled:opacity-40";

  return (
    <section aria-label="Tissue viewer" className={`flex flex-col gap-3 ${compact ? "min-h-0" : "min-h-[28rem]"}`}>
      {!compact && <ViewerControls
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
        onCompare={(c) => {
          setCompare(c);
          if (c) setDisplay("compare");
        }}
        lockedGenes={lockedGenes}
        onUnlock={() => setLockedGenes(null)}
      />}
      {section && (
        <div className="flex flex-wrap items-center gap-1" role="toolbar" aria-label="Tissue view">
          <div className="flex gap-1" role="group" aria-label="Map or depth">
            <button type="button" aria-pressed={!depthMode} onClick={() => setDepthMode(false)} className={chip}>
              2D map
            </button>
            <button
              type="button"
              aria-pressed={depthMode}
              disabled={!depthRegion}
              title={depthRegion ? undefined : "Draw a box, or follow the agent's evidence, to explore its measured depth"}
              onClick={() => setDepthMode(true)}
              className={chip}
            >
              3D molecule depth
            </button>
          </div>
          <span className="mx-1 h-4 w-px bg-line" aria-hidden="true" />
          <div className={`flex flex-wrap gap-1 ${depthMode ? "hidden" : ""}`} role="group" aria-label="Counting rule shown">
            {DISPLAYS.map((d) => (
              <button
                key={d.id}
                type="button"
                aria-pressed={display === d.id}
                disabled={d.id !== "usual" && !condition}
                onClick={() => {
                  if (condition && !compare) setCompare(condition);
                  setDisplay(d.id);
                }}
                className={chip}
              >
                {d.label}
              </button>
            ))}
          </div>
          <span className="mx-1 h-4 w-px bg-line" aria-hidden="true" />
          <button type="button" aria-pressed={boxMode} onClick={() => setBoxMode((m) => !m)} className={chip}>
            {boxMode ? "Drag on the tissue…" : "Draw box"}
          </button>
          <button type="button" onClick={() => setFitKey((k) => k + 1)} className={chip}>
            Fit tissue
          </button>
          {focused && (
            <button type="button" onClick={() => setFlyKey((k) => k + 1)} className={chip}>
              Follow evidence
            </button>
          )}
        </div>
      )}
      <div className="relative min-h-0 flex-1">
        {section && depthMode && depthRegion ? (
          <DepthView
            region={depthRegion}
            genes={auditGenes}
            cellType={null}
            labelRuleId={section.view.label_rule_id}
            onOpenSection={(id) => {
              setDepthMode(false);
              pickSection(id);
            }}
          />
        ) : section ? (
          <Viewer
            section={section}
            genes={genes}
            cellTypes={cellTypes}
            visibleGenes={visible}
            compare={display === "usual" ? null : compare}
            display={display}
            flyTo={focused ? { region: focused.region, key: focused.key * 1000 + flyKey } : null}
            evidenceRegion={focused?.region ?? null}
            excludedCellType={focused && lockedGenes ? focused.cellType : null}
            boxMode={boxMode}
            box={box}
            onBox={(b) => {
              setBoxMode(false);
              setBox(b);
            }}
            fitKey={fitKey}
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
        {box && section && !depthMode && (
          <section
            aria-label="Your RNA region"
            data-testid="rna-region-card"
            className="absolute top-10 right-3 z-20 w-[min(360px,calc(100%-24px))] rounded-2xl bg-[#16171b]/95 p-3 text-[12px] text-ink-2 ring-1 ring-white/[0.08] backdrop-blur"
          >
            <div className="flex items-start justify-between gap-2">
              <p>
                <span className="font-medium text-ink">Your box</span> · Xenium RNA · {section.view.dataset_id} {section.view.section_id} · {regionSize(box)}
              </p>
              <button type="button" onClick={() => setBox(null)} aria-label="Clear the box" className="-mt-1 rounded-full px-2 text-ink-3 hover:text-ink">
                ×
              </button>
            </div>
            <p className="mt-1 text-ink-3">
              {auditCellType && auditGenes.length > 0
                ? `Population: ${auditCellType} · gene${auditGenes.length > 1 ? "s" : ""} ${auditGenes.join(", ")}`
                : "Pick a highlighted cell type and gene to audit."}
            </p>
            <button
              type="button"
              onClick={analyse}
              disabled={!auditCellType || auditGenes.length === 0 || currentAudit?.pending}
              className="mt-2 h-8 rounded-full bg-white px-3 text-[12px] font-medium text-black disabled:opacity-50"
            >
              Analyse selected region
            </button>
            {currentAudit?.pending && <p className="shimmer-text mt-1.5">Re-counting molecules in this box under each rule…</p>}
            {currentAudit?.problem && <p className="mt-1.5 text-bad">{currentAudit.problem}</p>}
            {currentAudit?.result && <RegionResult result={currentAudit.result} />}
            <p className="mt-2 text-[11px] leading-relaxed text-ink-3">
              New descriptive analysis of this box only, computed now by the analysis engine without a model call. The recorded investigation was not run on it.
            </p>
          </section>
        )}
      </div>
      {section && (!compact || legend) && (
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
