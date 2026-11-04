// The findings table: every committed audit and contrast result with its evidence label, filterable by kind,
// label, cell type and gene. Opening an audit result shows, per condition, the pooled observed value beside its
// retention and both random-thinning expectations (never an observed number alone); opening a contrast shows its
// group means and effect per condition, the exploratory column apart, and its inference eligibility. Both show the
// composite figure and "Fly to evidence" with rank stepping under the stated ranking rule.
import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type {
  AuditIndex,
  AuditIndexEntry,
  AuditResult,
  ContrastIndex,
  ContrastIndexEntry,
  ContrastResult,
  EvidenceStatus,
} from "../contracts/generated";
import { CONDITION_NAMES } from "./Viewer";
import type { TissueFocus } from "./TissuePanel";

interface Props {
  datasetId: string;
  onFocus: (focus: Omit<TissueFocus, "key">) => void;
}

const LABEL_STYLE: Record<EvidenceStatus, string> = {
  stable: "border-emerald-500/50 text-emerald-300",
  segmentation_sensitive: "border-amber-500/60 text-amber-300",
  insufficient_evidence: "border-line text-ink-3",
};

function pct(value: number | null | undefined): string {
  return value === null || value === undefined ? "n/a" : `${(value * 100).toFixed(1)}%`;
}

export function LabelBadge({ label }: { label: EvidenceStatus }) {
  return <span className={`rounded border px-1.5 py-0.5 text-[11px] ${LABEL_STYLE[label]}`}>{label.replaceAll("_", " ")}</span>;
}

interface Row {
  kind: "audit" | "contrast";
  findingId: string;
  title: string;
  label: EvidenceStatus;
  cellType: string;
  genes: string[];
  count: string;
  audit?: AuditIndexEntry;
  contrast?: ContrastIndexEntry;
}

/** The dataset's section and donor counts, shown wherever a section count appears. */
export function SectionDisclosure({ text }: { text: string | null | undefined }) {
  if (!text) return null;
  return <p className="text-[11px] text-ink-3">{text}</p>;
}

function Filter({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (v: string) => void }) {
  return (
    <label className="flex items-center gap-1 text-ink-3">
      {label}
      <select className="rounded border border-line bg-panel px-1 py-0.5 text-ink-2" value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">all</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {o.replaceAll("_", " ")}
          </option>
        ))}
      </select>
    </label>
  );
}

const unique = (values: string[]) => [...new Set(values)].sort();

export function FindingsPanel({ datasetId, onFocus }: Props) {
  const [index, setIndex] = useState<AuditIndex | null>(null);
  const [contrasts, setContrasts] = useState<ContrastIndex | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [kind, setKind] = useState("");
  const [label, setLabel] = useState("");
  const [cellType, setCellType] = useState("");
  const [gene, setGene] = useState("");

  useEffect(() => {
    api
      .auditResults(datasetId)
      .then(setIndex)
      .catch((error: unknown) => setProblem(String(error)));
    api
      .contrastResults(datasetId)
      .then(setContrasts)
      .catch(() => setContrasts(null));
  }, [datasetId]);

  const rows = useMemo<Row[]>(() => {
    const audit: Row[] = (index?.entries ?? []).map((entry) => ({
      kind: "audit",
      findingId: entry.finding_id,
      title: entry.title,
      label: entry.label,
      cellType: entry.cell_type,
      genes: entry.genes,
      count: `${entry.eligible_sections} sections`,
      audit: entry,
    }));
    const contrast: Row[] = (contrasts?.entries ?? []).map((entry) => ({
      kind: "contrast",
      findingId: entry.finding_id,
      title: entry.title,
      label: entry.label,
      cellType: entry.cell_type,
      genes: [entry.gene],
      count: `${entry.disease_sections} vs ${entry.control_sections} sections`,
      contrast: entry,
    }));
    return [...audit, ...contrast];
  }, [index, contrasts]);

  if (problem) return <p className="rounded-lg border border-line bg-panel p-3 text-xs text-ink-3">No audit results: {problem}</p>;
  if (!index) return null;

  const shown = rows.filter(
    (r) => (!kind || r.kind === kind) && (!label || r.label === label) && (!cellType || r.cellType === cellType) && (!gene || r.genes.includes(gene)),
  );

  return (
    <section aria-label="Findings" className="rounded-lg border border-line bg-panel p-3 text-xs">
      <h2 className="mb-1 text-sm font-semibold text-ink">Findings</h2>
      <p className="text-ink-3">
        {index.sections_counted.length} sections counted
        {index.sections_left_out.map((s) => ` · ${s.section_id} left out (${s.reason.replace("_", " ")})`)}
      </p>
      <SectionDisclosure text={index.section_disclosure ?? contrasts?.section_disclosure} />
      {contrasts && <p className="text-ink-3">Contrasts are descriptive only: no p-values or confidence intervals.</p>}
      <div className="my-2 flex flex-wrap gap-2">
        <Filter label="Kind" value={kind} options={unique(rows.map((r) => r.kind))} onChange={setKind} />
        <Filter label="Label" value={label} options={unique(rows.map((r) => r.label))} onChange={setLabel} />
        <Filter label="Cell type" value={cellType} options={unique(rows.map((r) => r.cellType))} onChange={setCellType} />
        <Filter label="Gene" value={gene} options={unique(rows.flatMap((r) => r.genes))} onChange={setGene} />
        <span className="self-center text-ink-3">
          {shown.length} of {rows.length}
        </span>
      </div>
      <ul className="flex max-h-[32rem] flex-col divide-y divide-line overflow-y-auto">
        {shown.map((row) => (
          <li key={row.findingId} className="py-1.5">
            <button
              type="button"
              className="flex w-full items-center justify-between gap-2 text-left text-ink-2 hover:text-ink"
              aria-expanded={open === row.findingId}
              onClick={() => setOpen(open === row.findingId ? null : row.findingId)}
            >
              <span className="min-w-0 truncate">
                <span className="mr-1 text-ink-3">{row.kind}</span>
                {row.title}
              </span>
              <span className="flex shrink-0 items-center gap-2">
                <span className="text-ink-3">{row.count}</span>
                <LabelBadge label={row.label} />
              </span>
            </button>
            {open === row.findingId && row.audit && <FindingDetail datasetId={datasetId} entry={row.audit} onFocus={onFocus} />}
            {open === row.findingId && row.contrast && <ContrastDetail datasetId={datasetId} entry={row.contrast} onFocus={onFocus} />}
          </li>
        ))}
      </ul>
    </section>
  );
}

function num(value: number | null | undefined): string {
  return value === null || value === undefined ? "n/a" : value.toFixed(2);
}

function ContrastDetail({ datasetId, entry, onFocus }: { datasetId: string; entry: ContrastIndexEntry; onFocus: Props["onFocus"] }) {
  const [result, setResult] = useState<ContrastResult | null>(null);
  const [rank, setRank] = useState(1);

  useEffect(() => {
    api.contrastResult(datasetId, entry.finding_id).then(setResult).catch(() => setResult(null));
  }, [datasetId, entry.finding_id]);

  if (!result) return <p className="py-2 text-ink-3">Loading…</p>;
  const regions = result.evidence_regions;
  const region = regions.find((r) => r.rank === rank) ?? null;
  const count = (group: string) => result.sections.filter((s) => s.group === group).length;

  const fly = (nextRank: number) => {
    const target = regions.find((r) => r.rank === nextRank);
    if (!target) return;
    setRank(nextRank);
    onFocus({
      sectionId: target.region.section_id,
      labelRuleId: result.population.label_rule_id,
      genes: [result.gene],
      highlight: [result.gene],
      cellType: result.population.cell_type,
      condition: target.condition ?? "nucleus_only",
      region: target.region,
    });
  };

  return (
    <div className="mt-2 flex flex-col gap-2">
      <p className="text-ink-3">{result.label_reason}</p>
      <p className="text-ink-3">
        Inference eligibility: descriptive only ({result.donor_distinctness?.replaceAll("_", " ")}). {result.inference_reason}
      </p>
      <table className="w-full table-fixed text-right text-[11px] tabular-nums">
        <caption className="mb-1 text-left text-ink-3">
          {result.groups.disease} (n={count(result.groups.disease)}) vs {result.groups.control} (n={count(result.groups.control)}) sections. Effect: the
          difference of group mean log2(CP10K + 1). Struck-through conditions fail the molecule gate.
        </caption>
        <thead className="text-ink-3">
          <tr>
            <th className="text-left font-normal">Condition</th>
            <th className="font-normal">{result.groups.disease} mean</th>
            <th className="font-normal">{result.groups.control} mean</th>
            <th className="font-normal">Effect</th>
            <th className="font-normal" title="SAM 3.1 proposal (exploratory), on sections with outlines only; never sets the label">
              Exploratory
            </th>
          </tr>
        </thead>
        <tbody className="text-ink-2">
          {result.effects.map((e) => (
            <tr key={e.condition} className={e.valid ? undefined : "text-ink-3 line-through"} title={e.invalid_reason ?? undefined}>
              <td className="text-left">{CONDITION_NAMES[e.condition] ?? e.condition}</td>
              <td>{num(e.disease_mean)}</td>
              <td>{num(e.control_mean)}</td>
              <td>{num(e.effect)}</td>
              <td />
            </tr>
          ))}
          {result.exploratory_effects.map((e) => (
            <tr key={e.condition} className="text-amber-300">
              <td className="truncate text-left" title={CONDITION_NAMES[e.condition]}>
                structure-constrained
              </td>
              <td>{num(e.disease_mean)}</td>
              <td>{num(e.control_mean)}</td>
              <td />
              <td title={e.missing_reason ?? `${e.sections_used.length} sections with outlines`}>{num(e.effect)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <SectionDisclosure text={result.section_disclosure} />
      {regions.length > 0 ? (
        <div className="flex flex-col gap-1 rounded border border-line p-2">
          <div className="flex items-center gap-2">
            <button type="button" className="rounded bg-accent px-2 py-1 font-medium text-surface" onClick={() => fly(rank)}>
              Fly to evidence
            </button>
            <button type="button" aria-label="Previous rank" disabled={rank <= 1} className="px-1 disabled:opacity-40" onClick={() => fly(rank - 1)}>
              ◀
            </button>
            <span>
              rank {rank} of {regions.length}
            </span>
            <button
              type="button"
              aria-label="Next rank"
              disabled={rank >= regions.length}
              className="px-1 disabled:opacity-40"
              onClick={() => fly(rank + 1)}
            >
              ▶
            </button>
          </div>
          {region && (
            <p className="text-ink-2">
              {region.region.section_id}: {region.excluded_molecules} of {region.default_molecules} molecules excluded under{" "}
              {CONDITION_NAMES[region.condition ?? ""] ?? region.condition}
            </p>
          )}
          <p className="text-ink-3">Ranking rule: {result.ranking_rule}</p>
        </div>
      ) : (
        <p className="text-ink-3">No evidence region: no molecules of this gene in the population are excluded.</p>
      )}
      {entry.figure && (
        <a href={api.contrastFigureUrl(datasetId, entry.finding_id)} target="_blank" rel="noreferrer">
          <img
            src={api.contrastFigureUrl(datasetId, entry.finding_id)}
            alt={`Composite figure. A: ${entry.figure.panel_a} B: ${entry.figure.panel_b}`}
            className="w-full rounded border border-line bg-white"
          />
        </a>
      )}
    </div>
  );
}

function FindingDetail({ datasetId, entry, onFocus }: { datasetId: string; entry: AuditIndexEntry; onFocus: Props["onFocus"] }) {
  const [result, setResult] = useState<AuditResult | null>(null);
  const [rank, setRank] = useState(1);

  useEffect(() => {
    api.auditResult(datasetId, entry.finding_id).then(setResult).catch(() => setResult(null));
  }, [datasetId, entry.finding_id]);

  if (!result) return <p className="py-2 text-ink-3">Loading…</p>;
  const regions = result.evidence_regions;
  const region = regions.find((r) => r.rank === rank) ?? null;
  const resultGenes =
    result.measure === "co_expression_score"
      ? result.genes.filter((g) => result.rules?.home_cell_types[g] !== result.population.cell_type)
      : result.genes;

  const fly = (nextRank: number) => {
    const target = regions.find((r) => r.rank === nextRank);
    if (!target) return;
    setRank(nextRank);
    onFocus({
      sectionId: target.region.section_id,
      labelRuleId: result.population.label_rule_id,
      genes: result.genes,
      highlight: resultGenes,
      cellType: result.population.cell_type,
      condition: target.condition ?? "nucleus_only",
      region: target.region,
    });
  };

  return (
    <div className="mt-2 flex flex-col gap-2">
      <p className="text-ink-3">{result.label_reason}</p>
      <table className="w-full table-fixed text-right text-[11px] tabular-nums">
        <caption className="mb-1 text-left text-ink-3">
          Pooled over {result.eligible_section_ids.length} eligible sections (
          {Object.entries(result.eligible_by_group)
            .map(([group, n]) => `${group} ${n}`)
            .join(", ")}
          )
        </caption>
        <thead className="text-ink-3">
          <tr>
            <th className="text-left font-normal">Condition</th>
            <th className="font-normal">Observed</th>
            <th className="font-normal">Retention</th>
            <th className="font-normal" title="Home-matched random-thinning expectation: the gene's retention in its home cell type, applied to each cell">
              Home exp.
            </th>
            <th className="font-normal" title="Cell-matched random-thinning expectation: each cell's own retention">
              Cell exp.
            </th>
          </tr>
        </thead>
        <tbody className="text-ink-2">
          {result.pooled.map((p) => (
            <tr key={p.condition} className={p.below_home_threshold ? "text-amber-300" : undefined}>
              <td className="text-left">{CONDITION_NAMES[p.condition] ?? p.condition}</td>
              <td>{pct(p.observed_value)}</td>
              <td>{pct(p.retention)}</td>
              <td>{pct(p.expectation_home_matched)}</td>
              <td>{pct(p.expectation_cell_matched)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {result.marker_pairs && result.measure === "co_expression_score" && (
        <p className="text-ink-3">
          {result.gene_pairs.length} frozen exclusive marker pairs from {result.marker_pairs.source_dataset} (
          <span className="font-mono">{result.marker_pairs.sha256.slice(0, 12)}</span>)
        </p>
      )}
      {regions.length > 0 ? (
        <div className="flex flex-col gap-1 rounded border border-line p-2">
          <div className="flex items-center gap-2">
            <button type="button" className="rounded bg-accent px-2 py-1 font-medium text-surface" onClick={() => fly(rank)}>
              Fly to evidence
            </button>
            <button type="button" aria-label="Previous rank" disabled={rank <= 1} className="px-1 disabled:opacity-40" onClick={() => fly(rank - 1)}>
              ◀
            </button>
            <span>
              rank {rank} of {regions.length}
            </span>
            <button
              type="button"
              aria-label="Next rank"
              disabled={rank >= regions.length}
              className="px-1 disabled:opacity-40"
              onClick={() => fly(rank + 1)}
            >
              ▶
            </button>
          </div>
          {region && (
            <p className="text-ink-2">
              {region.region.section_id}: {region.excluded_molecules} of {region.default_molecules} molecules excluded under{" "}
              {CONDITION_NAMES[region.condition ?? ""] ?? region.condition}
            </p>
          )}
          <p className="text-ink-3">Ranking rule: {result.ranking_rule}</p>
        </div>
      ) : (
        <p className="text-ink-3">No evidence region: no molecules of this result are excluded.</p>
      )}
      {entry.figure && (
        <a href={api.auditFigureUrl(datasetId, entry.finding_id)} target="_blank" rel="noreferrer">
          <img
            src={api.auditFigureUrl(datasetId, entry.finding_id)}
            alt={`Composite figure. A: ${entry.figure.panel_a} B: ${entry.figure.panel_b}`}
            className="w-full rounded border border-line bg-white"
          />
        </a>
      )}
    </div>
  );
}
