// What the asked question needs that this workspace does not hold, and the two ways to get it: the researcher's own
// sections (the Your data page, prefilled) or public datasets a live GEO search returned. Every line comes from the
// data check (`POST /api/data-fit`), computed in code; nothing here is written by a model.
import type { DataFit } from "../../contracts/generated";
import { Typed } from "./AgentBar";

interface Props {
  fit: DataFit;
  /** True while the repository search is still running. */
  searching: boolean;
  /** Whether a new question can run here (live runs); in replay only recorded questions play. */
  canRun: boolean;
  onAskAnyway: () => void;
  onAsk: (question: string) => void;
  onUpload: (prefill: DataFit["upload_prefill"]) => void;
  onDismiss: () => void;
}

function headline(fit: DataFit, canRun: boolean): string {
  const hard = fit.gaps.filter((g) => g.hard);
  if (hard.length > 0) return `I can't prove this with the data here: it needs ${hard.map((g) => g.item).join(", ")}.`;
  if (fit.gaps.length > 0) return `The data here answers part of this; ${fit.gaps.map((g) => g.item).join(", ")} is not in it.`;
  if (!canRun) return "The data here can answer this, but this public demo replays recorded runs only.";
  return "The data here can answer this.";
}

export function DataFitCard({ fit, searching, canRun, onAskAnyway, onAsk, onUpload, onDismiss }: Props) {
  const hard = fit.gaps.some((g) => g.hard);
  const found = fit.matched.filter((m) => m.available);
  return (
    <div data-testid="data-fit" className="mt-3 flex max-h-[52vh] flex-col gap-3 overflow-y-auto pr-1">
      <p className="text-[14px] leading-relaxed text-ink">
        <Typed text={headline(fit, canRun)} speed={90} />
      </p>

      {(fit.gaps.length > 0 || found.length > 0) && (
        <ul className="flex flex-col gap-1 font-mono text-[12.5px]">
          {fit.gaps.map((g) => (
            <li key={`${g.kind}-${g.item}`} className="flex gap-2.5">
              <span className={g.hard ? "text-bad" : "text-sensitive"}>{g.hard ? "✕" : "◆"}</span>
              <span className="min-w-0">
                <span className="text-ink">{g.item}</span> <span className="font-sans text-ink-3">{g.why}</span>
              </span>
            </li>
          ))}
          {found.length > 0 && (
            <li className="flex gap-2.5">
              <span className="text-stable">✓</span>
              <span className="text-ink-2">
                Here: {found.map((m) => m.value).join(", ")}
              </span>
            </li>
          )}
        </ul>
      )}

      {fit.related_recordings.length > 0 && (
        <div>
          <p className="text-[12px] text-ink-3">Closest recorded run on the same genes or cells</p>
          {fit.related_recordings.slice(0, 2).map((q) => (
            <button key={q} type="button" onClick={() => onAsk(q)} className="group mt-0.5 flex w-full items-baseline gap-2.5 rounded-xl px-2 py-1.5 text-left font-mono text-[12.5px] hover:bg-raised">
              <span className="text-stable">›</span>
              <span className="text-ink-2 group-hover:text-ink">{q.length > 110 ? `${q.slice(0, 108)}…` : q}</span>
            </button>
          ))}
        </div>
      )}

      {(hard || fit.gaps.length > 0) && (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <section aria-label="Bring your own sections" className="flex flex-col gap-2 rounded-2xl bg-raised/70 p-3">
            <h3 className="text-[13px] font-semibold">Bring your own sections</h3>
            <p className="text-[12px] leading-relaxed text-ink-2">The same engine audits your Xenium output; nothing is kept.</p>
            <details className="text-[12px] text-ink-2">
              <summary className="cursor-pointer text-ink-3 hover:text-ink">What your files need</summary>
              <ul className="mt-1 flex list-disc flex-col gap-1 pl-4 leading-relaxed">
                {fit.upload_needs.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            </details>
            <button type="button" onClick={() => onUpload(fit.upload_prefill)} className="mt-auto h-9 self-start rounded-full bg-white px-4 text-[13px] font-medium text-black">
              Audit your data
            </button>
          </section>

          <section aria-label="Public datasets" className="flex min-w-0 flex-col gap-1.5 rounded-2xl bg-raised/70 p-3">
            <h3 className="text-[13px] font-semibold">Public datasets that might</h3>
            {searching && <p className="shimmer-text text-[12px]">Searching GEO for {fit.gaps.map((g) => g.item).join(", ")}…</p>}
            {!searching && fit.datasets.length === 0 && <p className="text-[12px] text-ink-3">{fit.search_note || "No record found."}</p>}
            <ul className="flex flex-col gap-1.5">
              {fit.datasets.slice(0, 4).map((d) => (
                <li key={d.accession} className="rise">
                  <a href={d.url} target="_blank" rel="noreferrer" className="group block rounded-xl px-1.5 py-1 hover:bg-[#2a2d32]">
                    <span className="flex flex-wrap items-center gap-1.5 text-[12px]">
                      <span className="font-mono text-ink">{d.accession}</span>
                      <span className={`rounded-full px-1.5 py-px text-[10.5px] font-medium ${d.auditable_here ? "bg-[#222a10] text-stable" : "bg-[#24262b] text-ink-2"}`}>
                        {d.auditable_here ? `${d.technology} · audit it here` : d.technology}
                      </span>
                      {d.samples != null && <span className="text-ink-3">{d.samples} samples</span>}
                    </span>
                    <span className="mt-0.5 line-clamp-2 block text-[12px] leading-snug text-ink-2 group-hover:text-ink">{d.title}</span>
                    {d.matches.length > 0 && <span className="block text-[11px] text-ink-3">mentions {d.matches.join(", ")}</span>}
                  </a>
                </li>
              ))}
            </ul>
            {!searching && fit.datasets.length > 0 && <p className="text-[11px] leading-snug text-ink-3">{fit.search_note}</p>}
            <a href={fit.search_url} target="_blank" rel="noreferrer" className="text-[12px] text-ink-3 underline underline-offset-4 hover:text-ink">
              Run this search on GEO
            </a>
          </section>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {!hard && canRun && (
          <button type="button" onClick={onAskAnyway} className="h-8 rounded-full bg-white px-4 text-[13px] font-medium text-black">
            {fit.gaps.length > 0 ? "Run on what is here" : "Run it"}
          </button>
        )}
        <button type="button" onClick={onDismiss} className="h-8 rounded-full px-3 text-[13px] text-ink-2 hover:bg-raised hover:text-ink">
          Ask something else
        </button>
      </div>
    </div>
  );
}
