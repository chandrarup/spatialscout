// Bring your own sections: Xenium output (a transcripts file and a cells file per section), uploaded or linked, audited
// by the same engine as the built-in dataset. Nothing is kept: the server holds the files in memory for the one
// request and returns the audit and a publication figure.
import { useState } from "react";
import { AgentOrb } from "./AgentBar";
import { pct } from "./Explore";

const CELL_TYPES = ["Podocyte", "PT", "TAL", "DCT", "PC", "IC", "PEC", "Endothelial", "Mesangial/Pericyte", "Fibroblast", "Myeloid", "T cell", "B cell"];
const LABEL_WORD: Record<string, { word: string; tone: string; means: string }> = {
  stable: { word: "Holds", tone: "text-stable", means: "The signal stays when molecules are assigned more strictly, as real cell content would." },
  segmentation_sensitive: { word: "Falls away", tone: "text-sensitive", means: "The signal drops beyond random thinning: likely molecules from neighbouring cells." },
  insufficient_evidence: { word: "Not enough", tone: "text-ink-2", means: "Too few eligible sections or molecules to say either way." },
};

interface Section {
  section_id: string;
  validation: { molecules_read: number; molecules_kept: number; cells_kept: number };
  cell_types: Record<string, number>;
}
interface PooledValue {
  condition: string;
  cells: number;
  observed_value: number | null;
  expectation_home_matched: number | null;
}
interface Audit {
  sections: Section[];
  result: { label: string; label_reason: string; eligible_section_ids: string[]; pooled: PooledValue[]; finding_id: string } | null;
  problem: string | null;
  figure_svg: string | null;
  figure_png_base64: string | null;
  legend: string | null;
  handling: string;
}

/** `prefill`: the cell type and genes of a question the data check sent here. */
export function Upload({ prefill = null }: { prefill?: { cell_type?: string | null; genes?: string[] } | null }) {
  const [pairs, setPairs] = useState<{ t: File | null; c: File | null }[]>([{ t: null, c: null }]);
  const [links, setLinks] = useState("");
  const [cellType, setCellType] = useState(prefill?.cell_type && CELL_TYPES.includes(prefill.cell_type) ? prefill.cell_type : "Podocyte");
  const [genes, setGenes] = useState(prefill?.genes?.length ? prefill.genes.join(", ") : "NPHS1");
  const [state, setState] = useState<"idle" | "running">("idle");
  const [audit, setAudit] = useState<Audit | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  const run = (source: "sample" | "files" | "links") => {
    const form = new FormData();
    form.set("cell_type", cellType);
    form.set("genes", genes);
    if (source === "sample") form.set("use_sample", "true");
    if (source === "files") {
      for (const p of pairs) {
        if (!p.t || !p.c) return setProblem("Each section needs a transcripts file and a cells file.");
        form.append("transcripts", p.t);
        form.append("cells", p.c);
      }
    }
    if (source === "links") {
      const rows = links
        .split("\n")
        .map((l) => l.trim().split(/\s+/))
        .filter((r) => r.length === 2);
      if (rows.length === 0) return setProblem("One line per section: the transcripts link, a space, then the cells link.");
      for (const [t, c] of rows) {
        form.append("transcripts_url", t!);
        form.append("cells_url", c!);
      }
    }
    setState("running");
    setProblem(null);
    setAudit(null);
    fetch("/api/upload/audit", { method: "POST", body: form })
      .then(async (r) => {
        const body = await r.json();
        if (!r.ok) throw new Error(body?.detail?.message ?? JSON.stringify(body?.detail ?? body));
        setAudit(body as Audit);
      })
      .catch((e: unknown) => setProblem(String(e).replace(/^Error:\s*/, "")))
      .finally(() => setState("idle"));
  };

  const label = audit?.result ? LABEL_WORD[audit.result.label] : null;
  const d = audit?.result?.pooled.find((p) => p.condition === "default");
  const n = audit?.result?.pooled.find((p) => p.condition === "nucleus_only");
  const download = () => {
    if (!audit?.figure_svg) return;
    const url = URL.createObjectURL(new Blob([audit.figure_svg], { type: "image/svg+xml" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `spatialscout-${cellType}-${genes}.svg`.replaceAll(/[^A-Za-z0-9.-]/g, "_");
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-6 px-5 pt-10 pb-28">
        <div>
          <p className="text-[13px] text-ink-3">Your data</p>
          <h1 className="mt-1 text-[clamp(28px,3.4vw,44px)] leading-tight font-semibold tracking-[-0.03em]">Audit your own Xenium sections</h1>
          <p className="mt-2 max-w-[48rem] text-[16px] leading-relaxed text-ink-2">
            Upload or link each section's <code className="text-ink">transcripts.parquet</code> and <code className="text-ink">cells.csv</code> straight from the Xenium output folder. The
            same engine re-counts every molecule under stricter rules and tells you whether the signal holds. At least three sections give a verdict.
          </p>
          <p className="mt-3 flex items-start gap-2 rounded-2xl bg-[#11150a] px-4 py-3 text-[13px] leading-relaxed text-ink-2">
            <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-stable" />
            Nothing is kept. Files sit in temporary storage for the one request and are deleted when it ends; nothing is stored or sent to a model. Up to 40 MB per request. Cell types use label
            rules frozen on the GSE286184 50-gene panel, so other panels may leave cells unlabelled.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_320px]">
          <div className="flex flex-col gap-3 rounded-3xl bg-panel p-5">
            <h2 className="text-[15px] font-semibold">Sections</h2>
            {pairs.map((p, i) => (
              <div key={i} className="grid grid-cols-1 gap-2 sm:grid-cols-[auto_1fr_1fr]">
                <span className="self-center text-[13px] text-ink-3">#{i + 1}</span>
                {(["t", "c"] as const).map((k) => (
                  <label key={k} className="flex cursor-pointer items-center gap-2 rounded-2xl border border-dashed border-line px-3 py-2.5 text-[13px] text-ink-2 hover:border-ink-3">
                    <input
                      type="file"
                      accept=".parquet,.csv,.gz"
                      className="sr-only"
                      onChange={(e) => {
                        const file = e.target.files?.[0] ?? null;
                        setPairs((all) => all.map((q, j) => (j === i ? { ...q, [k]: file } : q)));
                      }}
                    />
                    <span className="truncate">{p[k]?.name ?? (k === "t" ? "transcripts.parquet / .csv" : "cells.csv / .parquet")}</span>
                  </label>
                ))}
              </div>
            ))}
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={() => setPairs((a) => [...a, { t: null, c: null }])} className="h-9 rounded-full bg-raised px-4 text-[13px] text-ink hover:bg-[#2a2d32]">
                Add a section
              </button>
              <button type="button" disabled={state === "running"} onClick={() => run("files")} className="h-9 rounded-full bg-white px-4 text-[13px] font-medium text-black disabled:opacity-50">
                Audit these files
              </button>
            </div>
            <details className="text-[13px] text-ink-2">
              <summary className="cursor-pointer text-ink">Or link files (https), one section per line</summary>
              <textarea
                value={links}
                onChange={(e) => setLinks(e.target.value)}
                rows={3}
                placeholder="https://…/transcripts.parquet https://…/cells.csv.gz"
                className="mt-2 w-full rounded-2xl bg-raised p-3 font-mono text-[12px] text-ink focus:outline-none"
              />
              <button type="button" disabled={state === "running"} onClick={() => run("links")} className="mt-2 h-9 rounded-full bg-white px-4 text-[13px] font-medium text-black disabled:opacity-50">
                Audit the links
              </button>
            </details>
          </div>
          <div className="flex flex-col gap-3 rounded-3xl bg-panel p-5">
            <h2 className="text-[15px] font-semibold">Question</h2>
            <label className="text-[12px] text-ink-3">
              Cell type
              <select value={cellType} onChange={(e) => setCellType(e.target.value)} className="mt-1 block h-10 w-full rounded-xl bg-raised px-3 text-[14px] text-ink">
                {CELL_TYPES.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
            <label className="text-[12px] text-ink-3">
              Gene(s), comma-separated
              <input value={genes} onChange={(e) => setGenes(e.target.value)} className="mt-1 block h-10 w-full rounded-xl bg-raised px-3 text-[14px] text-ink" />
            </label>
            <button type="button" disabled={state === "running"} onClick={() => run("sample")} className="mt-auto h-10 rounded-full bg-raised px-4 text-[13px] text-ink hover:bg-[#2a2d32] disabled:opacity-50">
              Try it on the sample (3 GSE286184 crops)
            </button>
            <p className="text-center text-[11px] leading-snug text-ink-3">The sample holds GSE286184's 50 genes (NPHS1, LRP2, UMOD, …), not every gene you may ask about.</p>
            <a href="/api/upload/sample" target="_blank" rel="noreferrer" className="text-center text-[12px] text-ink-3 underline underline-offset-4 hover:text-ink">
              Download the sample files
            </a>
          </div>
        </div>

        {state === "running" && (
          <div className="flex items-center gap-3 rounded-3xl bg-panel p-5">
            <AgentOrb size={34} working />
            <p className="shimmer-text text-[14px]">Validating molecules, labelling cells, re-counting under four assignment rules, drawing the figure…</p>
          </div>
        )}
        {problem && <p className="rounded-2xl bg-[#2c1a20] px-4 py-3 text-[13px] text-bad">{problem}</p>}

        {audit && (
          <section aria-label="Your audit" className="rise flex flex-col gap-4 rounded-3xl bg-panel p-6">
            {audit.result && label ? (
              <>
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:gap-8">
                  <span className={`text-[clamp(40px,5vw,68px)] leading-none font-semibold tracking-[-0.04em] uppercase ${label.tone}`}>{label.word}</span>
                  <div>
                    <p className="text-[18px] font-semibold">
                      {genes} in {cellType} cells: {pct(d?.observed_value ?? null)} → {pct(n?.observed_value ?? null)} under nucleus-only
                      <span className="font-normal text-ink-3"> (random thinning predicts {pct(n?.expectation_home_matched ?? null)})</span>
                    </p>
                    <p className="mt-1 text-[14px] text-ink-2">{label.means}</p>
                    <p className="mt-1 text-[12px] text-ink-3">{audit.result.label_reason}</p>
                  </div>
                </div>
                {audit.figure_png_base64 && (
                  <figure>
                    <img src={`data:image/png;base64,${audit.figure_png_base64}`} alt="Publication figure of your audit" className="w-full rounded-xl bg-white p-3" />
                    <figcaption className="mt-2 text-[13px] leading-relaxed text-ink-2">{audit.legend}</figcaption>
                  </figure>
                )}
                <button type="button" onClick={download} className="h-9 self-start rounded-full bg-white px-4 text-[13px] font-medium text-black">
                  Download the figure (SVG)
                </button>
              </>
            ) : (
              <p className="text-[14px] text-ink-2">{audit.problem}</p>
            )}
            <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
              {audit.sections.map((s) => (
                <div key={s.section_id} className="rounded-2xl bg-raised p-3 text-[12px] text-ink-2">
                  <p className="font-medium text-ink">{s.section_id}</p>
                  <p>
                    {s.validation.molecules_kept.toLocaleString()} of {s.validation.molecules_read.toLocaleString()} molecules kept · {s.validation.cells_kept.toLocaleString()} cells ·{" "}
                    {(s.cell_types[cellType] ?? 0).toLocaleString()} {cellType}
                  </p>
                </div>
              ))}
            </div>
            <p className="text-[12px] text-ink-3">{audit.handling}</p>
          </section>
        )}
      </div>
    </div>
  );
}
