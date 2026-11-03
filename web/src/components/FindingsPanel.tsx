// The findings table: every committed audit result with its evidence label. Opening one shows, per condition,
// the pooled observed value beside its retention and both random-thinning expectations (never an observed number
// alone), the composite figure, and "Fly to evidence" with rank stepping under the stated ranking rule.
import { useEffect, useState } from "react";
import { api } from "../api";
import type { AuditIndex, AuditIndexEntry, AuditResult, EvidenceStatus } from "../contracts/generated";
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

export function FindingsPanel({ datasetId, onFocus }: Props) {
  const [index, setIndex] = useState<AuditIndex | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    api
      .auditResults(datasetId)
      .then(setIndex)
      .catch((error: unknown) => setProblem(String(error)));
  }, [datasetId]);

  if (problem) return <p className="rounded-lg border border-line bg-panel p-3 text-xs text-ink-3">No audit results: {problem}</p>;
  if (!index) return null;

  return (
    <section aria-label="Audit results" className="rounded-lg border border-line bg-panel p-3 text-xs">
      <h2 className="mb-1 text-sm font-semibold text-ink">Audit results</h2>
      <p className="mb-2 text-ink-3">
        {index.sections_counted.length} sections counted
        {index.sections_left_out.map((s) => ` · ${s.section_id} left out (${s.reason.replace("_", " ")})`)}
      </p>
      <ul className="flex flex-col divide-y divide-line">
        {index.entries.map((entry) => (
          <li key={entry.finding_id} className="py-1.5">
            <button
              type="button"
              className="flex w-full items-center justify-between gap-2 text-left text-ink-2 hover:text-ink"
              aria-expanded={open === entry.finding_id}
              onClick={() => setOpen(open === entry.finding_id ? null : entry.finding_id)}
            >
              <span className="min-w-0 truncate">{entry.title}</span>
              <span className="flex shrink-0 items-center gap-2">
                <span className="text-ink-3">{entry.eligible_sections} sections</span>
                <LabelBadge label={entry.label} />
              </span>
            </button>
            {open === entry.finding_id && <FindingDetail datasetId={datasetId} entry={entry} onFocus={onFocus} />}
          </li>
        ))}
      </ul>
    </section>
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
