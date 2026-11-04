// The protein audit of each pane's box (or whole image) on KPMP CODEX: per result, the observed positive share
// under every measurement condition beside its random-pixel-loss expectation, the pixel retention, and whether the
// cells that lose positivity border the marker's home cells. Every value comes from the server's computed result.
import type { ProteinAuditResult } from "../contracts/generated";

export interface PaneAudit {
  title: string;
  results: ProteinAuditResult[] | null;
  pending: boolean;
  problem: string | null;
}

const CONDITION_LABELS: Record<string, string> = {
  whole_cell: "Whole label",
  eroded_1px: "Eroded 1 px",
  eroded_2px: "Eroded 2 px",
  nucleus_region: "Nucleus region",
};
const LABEL_STYLES: Record<string, string> = {
  stable: "border-emerald-400/50 bg-emerald-400/10 text-emerald-200",
  segmentation_sensitive: "border-amber-400/60 bg-amber-400/10 text-amber-200",
  insufficient_evidence: "border-line bg-raised text-ink-3",
};

function pct(v: number | null): string {
  return v === null ? "—" : `${(v * 100).toFixed(1)}%`;
}

export function ProteinAuditPanel({ panes }: { panes: PaneAudit[] }) {
  return (
    <section aria-label="Protein audit" className="grid grid-cols-1 gap-2 md:grid-cols-2">
      {panes.map((pane) => (
        <div key={pane.title} className="rounded-md border border-line bg-panel px-3 py-2 text-xs text-ink-2">
          <p className="flex items-center gap-2 font-semibold text-ink">
            Protein audit · {pane.title}
            {pane.pending && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current opacity-70" />}
          </p>
          {pane.problem && <p className="text-red-300">{pane.problem}</p>}
          {pane.results?.map((r) => (
            <div key={r.result_id} className="mt-2" data-testid="protein-audit-result" data-label={r.label}>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-ink">
                  {r.marker}+ share of {r.population}
                </span>
                <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wide ${LABEL_STYLES[r.label] ?? ""}`}>
                  {r.label.replaceAll("_", " ")}
                </span>
                <span className="text-[11px] text-ink-3">
                  {r.roi ? "in the box" : "whole image"} · {r.population_cells.toLocaleString()} population cells · {r.home_cells.toLocaleString()} home cells
                </span>
              </div>
              <p className="text-[11px] text-ink-3">{r.label_reason}</p>
              <table className="mt-1 w-full text-left font-mono text-[11px]">
                <thead className="text-ink-3">
                  <tr>
                    <th className="font-normal">Condition</th>
                    <th className="font-normal">Observed</th>
                    <th className="font-normal" title="Random-pixel-loss expectation">Expected</th>
                    <th className="font-normal">Pixels kept</th>
                    <th className="font-normal" title="Cells losing positivity that border a home cell, vs cells keeping it">
                      Border home: lost / kept
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {r.conditions.map((c) => (
                    <tr key={c.condition}>
                      <td className="font-sans">{CONDITION_LABELS[c.condition] ?? c.condition}</td>
                      <td>
                        {pct(c.observed_share)} <span className="text-ink-3">({c.positive_cells})</span>
                      </td>
                      <td>{pct(c.expected_share)}</td>
                      <td>{pct(c.pixel_retention)}</td>
                      <td>
                        {c.condition === "whole_cell" ? "—" : `${pct(c.bordering_home_share_excluded)} (${c.excluded_cells}) / ${pct(c.bordering_home_share_retained)}`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
          {pane.results && pane.results[0] && <p className="mt-2 text-[11px] text-ink-3">{pane.results[0].inference}</p>}
        </div>
      ))}
    </section>
  );
}
