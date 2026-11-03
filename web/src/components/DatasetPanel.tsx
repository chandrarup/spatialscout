// The dataset panel: the capability report (what is supported, unavailable and why, and every contrast's
// inference eligibility), shown before any plan, plus the open section's validation and label counts.
import { useEffect, useState } from "react";
import { api } from "../api";
import type { CapabilityReport, DatasetManifest, LabelRuleSet } from "../contracts/generated";

interface Props {
  manifest: DatasetManifest;
  report: CapabilityReport;
  labelRules: LabelRuleSet | null;
  sectionId: string | null;
  open: boolean;
}

const STATUS_STYLE: Record<string, string> = {
  supported: "border-emerald-500/40 text-emerald-300",
  unavailable: "border-line text-ink-3",
  descriptive_only: "border-run-mode/50 text-run-mode",
};

export function DatasetPanel({ manifest, report, labelRules, sectionId, open }: Props) {
  const section = manifest.sections.find((s) => s.section_id === sectionId) ?? null;
  const counts = sectionId && labelRules ? (labelRules.sections[sectionId] ?? null) : null;
  return (
    <details open={open} className="group rounded-lg border border-line bg-panel p-4 text-xs">
      <summary className="cursor-pointer list-none text-sm font-semibold text-ink">
        Capability report · {manifest.dataset_id}
        <span className="ml-2 font-normal text-ink-3 group-open:hidden">show</span>
      </summary>
      <p className="mt-2 text-ink-2">{manifest.title}</p>

      <ul className="mt-3 space-y-1.5">
        {report.checks.map((check) => (
          <li key={check.capability} className="flex gap-2">
            <span className={`h-fit shrink-0 rounded border px-1.5 py-0.5 ${STATUS_STYLE[check.status] ?? ""}`}>
              {check.status.replaceAll("_", " ")}
            </span>
            <span className="text-ink-2">
              <span className="text-ink">{check.capability.replaceAll("_", " ")}</span>: {check.reason}
            </span>
          </li>
        ))}
      </ul>

      {report.contrasts.length > 0 && (
        <section className="mt-4">
          <h3 className="mb-1.5 font-medium text-ink-2">Contrasts and their inference eligibility</h3>
          <ul className="space-y-2">
            {report.contrasts.map((c) => (
              <li key={c.groups.disease} className="rounded border border-line bg-raised p-2">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="text-ink">
                    {c.groups.disease} vs {c.groups.control}
                  </span>
                  <span className={`rounded border px-1.5 py-0.5 ${STATUS_STYLE.descriptive_only}`}>
                    {c.inference_eligibility.replaceAll("_", " ")}
                  </span>
                </div>
                <div className="mt-1 text-ink-3">
                  {c.disease_section_ids.length} vs {c.control_section_ids.length} sections; published donors{" "}
                  {c.disease_donors_published} vs {c.control_donors_published}
                </div>
                <div className="mt-1 text-ink-2">{c.donor_distinctness_statement}</div>
                <div className="mt-1 text-ink-3">{c.inference_reason}</div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {manifest.donor_caveat && <p className="mt-3 text-ink-3">{manifest.donor_caveat}</p>}
      {manifest.filters && <p className="mt-2 text-ink-3">{manifest.filters.description}</p>}

      {section?.validation && (
        <section className="mt-4">
          <h3 className="mb-1.5 font-medium text-ink-2">
            Section {section.name ?? section.section_id} ({section.group}): validation
          </h3>
          <dl className="grid grid-cols-[1fr_auto] gap-x-3 gap-y-0.5 text-ink-3">
            {(
              [
                ["molecules read", section.validation.molecules_read],
                ["kept", section.validation.molecules_kept],
                ["below quality", section.validation.below_quality],
                ["not a panel gene", section.validation.not_in_panel],
                ["malformed", section.validation.malformed_molecules],
                ["duplicate", section.validation.duplicate_molecules],
                ["unassigned (kept)", section.validation.unassigned_molecules],
                ["unmatched cell id (kept as unassigned)", section.validation.unmatched_molecules],
                ["cells kept", section.validation.cells_kept],
                ["cells with no nucleus (kept)", section.validation.cells_without_nucleus],
                ["cells with no molecule (kept)", section.validation.cells_without_molecules],
              ] as const
            ).map(([label, value]) => (
              <div key={label} className="contents">
                <dt>{label}</dt>
                <dd className="text-right font-mono text-ink-2">{value.toLocaleString()}</dd>
              </div>
            ))}
          </dl>
          {section.duplicate_of && (
            <p className="mt-2 text-run-mode">
              This section's raw files hold the same content as {section.duplicate_of}; contrasts count only that one.
            </p>
          )}
        </section>
      )}

      {counts && labelRules && (
        <section className="mt-4">
          <h3 className="mb-1.5 font-medium text-ink-2">Cell type labels in this section, under each frozen rule</h3>
          <table className="w-full text-left text-ink-3">
            <thead>
              <tr>
                <th className="font-normal">cell type</th>
                {labelRules.rules.map((r) => (
                  <th key={r.label_rule_id} className="text-right font-normal">
                    {r.label_rule_id}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cellTypes(counts.cell_types).map((cellType) => (
                <tr key={cellType}>
                  <td>{cellType}</td>
                  {labelRules.rules.map((r) => (
                    <td key={r.label_rule_id} className="text-right font-mono text-ink-2">
                      {(counts.cell_types[r.label_rule_id]?.[cellType] ?? 0).toLocaleString()}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-ink-2">
            {counts.differing_cells.toLocaleString()} of {counts.cells.toLocaleString()} cells differ between the rules
            {Object.keys(counts.differing).length > 0 &&
              `: ${Object.entries(counts.differing)
                .map(([change, n]) => `${change} ${n.toLocaleString()}`)
                .join(", ")}`}
            .
          </p>
        </section>
      )}

      {manifest.citation && <p className="mt-4 text-ink-3">{manifest.citation}</p>}
    </details>
  );
}

function cellTypes(byRule: Record<string, Record<string, number>>): string[] {
  return [...new Set(Object.values(byRule).flatMap((perType) => Object.keys(perType)))].sort();
}

/** Loads the capability report and label rules of the open section's dataset, then shows the panel. */
export function DatasetCapabilities(props: { manifest: DatasetManifest; sectionId: string | null; open: boolean }) {
  const datasetId = props.manifest.dataset_id;
  const [loaded, setLoaded] = useState<{ datasetId: string; report: CapabilityReport; labelRules: LabelRuleSet | null } | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  useEffect(() => {
    let current = true;
    Promise.all([api.capabilityReport(datasetId), props.manifest.synthetic ? Promise.resolve(null) : api.labelRules(datasetId)])
      .then(([report, labelRules]) => current && setLoaded({ datasetId, report, labelRules }))
      .catch((error: unknown) => current && setProblem(String(error)));
    return () => {
      current = false;
    };
  }, [datasetId, props.manifest.synthetic]);
  if (problem) return <p role="alert" className="text-xs text-red-300">{problem}</p>;
  if (!loaded || loaded.datasetId !== datasetId) return <p className="text-xs text-ink-3">Loading the capability report…</p>;
  return <DatasetPanel {...props} report={loaded.report} labelRules={loaded.labelRules} />;
}
