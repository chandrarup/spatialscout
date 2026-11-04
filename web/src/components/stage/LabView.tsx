// The lab: what happens after the verdict. Muse Wonder dispatches sub-agents that run at the same time; their lanes
// are drawn from the recorded start and finish times (played back faster, durations shown as recorded), so the
// overlap on screen is the overlap that happened. Then the written analysis, the publication figures, the cited
// literature (only records Europe PMC returned) and the protein cross-checks.
import { useEffect, useMemo, useState } from "react";
import { api } from "../../api";
import type { LabEvent, LabRun, LabTask } from "../../contracts/generated";
import { AgentOrb, Typed } from "./AgentBar";
import { pct } from "./Explore";
import { labelTone } from "./RunCanvas";

const AGENT_NAME: Record<LabTask["agent"], string> = {
  literature: "Literature agent",
  protein_crosscheck: "Protein cross-check",
  publication_figure: "Figure agent",
};
const AGENT_TONE: Record<LabTask["agent"], string> = {
  literature: "from-[#4a63ff] to-[#7d8cff]",
  protein_crosscheck: "from-[#ff3fd0] to-[#ff8ae4]",
  publication_figure: "from-[#c6f24e] to-[#e2ff9a]",
};
const PLAY_MS = 9000;

function seconds(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${Math.round(ms)} ms`;
}

interface Props {
  investigationId: string;
  subClaims: string[];
  /** Each sub-claim's verdict, for the candidate-finding card. */
  verdicts?: { verdict: string; predicted: string; cellType: string; genes: string }[];
}

export function LabView({ investigationId, subClaims, verdicts }: Props) {
  const [lab, setLab] = useState<LabRun | null>(null);
  const [state, setState] = useState<"idle" | "starting" | "error">("idle");
  const [problem, setProblem] = useState<string | null>(null);
  const [progress, setProgress] = useState(1);

  useEffect(() => {
    api
      .lab(investigationId)
      .then((l) => l && setLab(l))
      .catch(() => undefined);
  }, [investigationId]);

  const start = () => {
    setState("starting");
    setProblem(null);
    api
      .startLab(investigationId)
      .then((l) => {
        setLab(l);
        setProgress(0);
        setState("idle");
      })
      .catch((e: unknown) => {
        setState("error");
        const text = String(e);
        setProblem(
          text.includes("no_recorded_lab")
            ? "This recorded run has no recorded lab. The lab is recorded for the featured run (the two-part podocyte LRP2 and B-cell UMOD question); live runs start it fresh."
            : text.replace(/^Error:\s*/, ""),
        );
      });
  };

  // Play the recorded timeline once, compressed into a few seconds.
  useEffect(() => {
    if (!lab || progress >= 1) return;
    const begin = performance.now() - progress * PLAY_MS;
    let frame = 0;
    const tick = (now: number) => {
      const p = Math.min(1, (now - begin) / PLAY_MS);
      setProgress(p);
      if (p < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [lab]); // eslint-disable-line react-hooks/exhaustive-deps

  const timeline = useMemo(() => {
    if (!lab) return null;
    const t0 = Date.parse(lab.started_at_utc);
    const t1 = Math.max(Date.parse(lab.finished_at_utc), t0 + 1);
    const at = (e: LabEvent | undefined) => (e ? (Date.parse(e.at_utc) - t0) / (t1 - t0) : null);
    const dispatched = lab.events.find((e) => e.type === "dispatched");
    const lanes = lab.tasks.map((t) => {
      const mine = lab.events.filter((e) => e.task_id === t.task_id);
      const s = mine.find((e) => e.type === "subagent_started");
      const f = mine.find((e) => e.type === "subagent_finished" || e.type === "subagent_failed");
      const call = mine.find((e) => e.type === "model_call")?.call;
      return { task: t, start: at(s) ?? 0, end: at(f) ?? 1, ms: s && f ? Date.parse(f.at_utc) - Date.parse(s.at_utc) : 0, failed: f?.type === "subagent_failed", finish: f, call };
    });
    const dispatchCall = lab.events.find((e) => e.type === "model_call" && !e.task_id)?.call;
    return { lanes, dispatchEnd: at(dispatched) ?? 0, total: t1 - t0, dispatchCall, rejected: lab.events.filter((e) => e.type === "task_rejected") };
  }, [lab]);

  if (!lab) {
    return (
      <div className="flex flex-col gap-4 rounded-3xl bg-panel p-6 md:flex-row md:items-center">
        <AgentOrb size={52} working={state === "starting"} />
        <div className="flex-1">
          <h2 className="text-[20px] font-semibold">Go deeper: open the lab</h2>
          <p className="mt-1 max-w-[46rem] text-[14px] leading-relaxed text-ink-2">
            Muse Wonder reads the verdict and dispatches sub-agents that work in parallel: a literature agent that searches Europe PMC and reads the records, a protein
            cross-check on the KPMP biopsies, and a figure agent that draws publication figures.
          </p>
          {problem && <p className="mt-2 text-[13px] text-bad">{problem}</p>}
        </div>
        <button type="button" onClick={start} disabled={state === "starting"} className="h-11 shrink-0 rounded-full bg-white px-6 text-[14px] font-medium text-black disabled:opacity-60">
          {state === "starting" ? <span className="shimmer-text">Dispatching…</span> : "Run the lab"}
        </button>
      </div>
    );
  }

  const done = progress >= 1;
  return (
    <div className="flex flex-col gap-6">
      {/* The dispatcher and its sub-agents, on the recorded clock. */}
      <section aria-label="Lab timeline" className="rounded-3xl bg-panel p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <AgentOrb size={40} working={!done} />
            <div>
              <h2 className="text-[20px] font-semibold">The lab</h2>
              <p className="text-[13px] text-ink-3">
                {lab.origin === "live" ? "Live" : "Recorded live, played back"} · {lab.tasks.length} sub-agents in parallel · {seconds(timeline!.total)} wall time
              </p>
            </div>
          </div>
          <button type="button" onClick={() => setProgress(0)} className="h-9 rounded-full bg-raised px-4 text-[13px] text-ink hover:bg-[#2a2d32]">
            Replay the timeline
          </button>
        </div>
        <p className="mt-4 max-w-[52rem] text-[14px] leading-relaxed text-ink">
          <Typed text={lab.dispatch_summary} speed={140} />
        </p>
        <div className="mt-5 flex flex-col gap-2.5">
          <Lane
            name="Dispatcher"
            sub={timeline!.dispatchCall ? `${timeline!.dispatchCall.model} · ${seconds(timeline!.dispatchCall.latency_ms)}` : "Muse Wonder"}
            start={0}
            end={timeline!.dispatchEnd}
            progress={progress}
            tone="from-white to-[#cfcfcf]"
            note="Chooses the sub-agents"
          />
          {timeline!.lanes.map((l) => (
            <Lane
              key={l.task.task_id}
              name={`${AGENT_NAME[l.task.agent]} · part ${l.task.sub_claim + 1}`}
              sub={`${seconds(l.ms)}${l.call ? ` · ${l.call.model} ${seconds(l.call.latency_ms)}` : ""}`}
              start={l.start}
              end={l.end}
              progress={progress}
              tone={l.failed ? "from-[#ff5d6c] to-[#ff8a95]" : AGENT_TONE[l.task.agent]}
              note={progress >= l.end ? (l.finish?.text ?? "") : l.task.query ?? l.task.reason}
            />
          ))}
        </div>
        {timeline!.rejected.length > 0 && (
          <p className="mt-3 text-[12px] text-ink-3">Rejected by the registry check: {timeline!.rejected.map((e) => e.text).join("; ")}</p>
        )}
        <p className="mt-3 text-[12px] text-ink-3">Bars are drawn from each sub-agent's recorded start and finish; overlapping bars ran at the same time.</p>
      </section>

      {done &&
        lab.literature
          .filter((l) => l.co_mention.records_mentioning_all === 0)
          .map((l) => {
            const task = lab.tasks.find((t) => t.task_id === l.task_id)!;
            const verdict = verdicts?.[task.sub_claim];
            // The signal held under stricter assignment: a confirmed 'holds' or a refuted 'drops'.
            const held = verdict && ((verdict.verdict === "confirmed" && verdict.predicted === "holds") || (verdict.verdict === "refuted" && verdict.predicted === "drops"));
            if (!verdict || !held) return null;
            const protein = lab.protein.find((p) => p.sub_claim === task.sub_claim);
            const figure = lab.figures.find((f) => f.sub_claim === task.sub_claim);
            return (
              <section key={l.task_id} aria-label="Candidate finding" className="rise milestone rounded-3xl bg-[#11150a] p-6">
                <p className="text-[12px] font-medium tracking-wide text-stable uppercase">Candidate to test · not a discovery</p>
                <h3 className="mt-2 text-[clamp(22px,2.6vw,32px)] leading-tight font-semibold tracking-tight">
                  {verdict.genes} signal in {verdict.cellType}s is not explained by molecules spilling over from neighbouring cells.
                </h3>
                <ul className="mt-4 grid grid-cols-1 gap-4 text-[14px] leading-relaxed text-ink-2 md:grid-cols-3">
                  <li>
                    <span className="block text-ink">Transcripts (the evidence)</span>
                    {figure
                      ? `${figure.sections} Xenium sections, ${figure.cells.toLocaleString()} cells: under nucleus-only assignment the share stays above what random thinning predicts. Verified claim, controls cited.`
                      : "The share stays under stricter assignment (verified claim)."}
                  </li>
                  <li>
                    <span className="block text-ink">Protein (descriptive)</span>
                    {protein ? protein.note : "Not checked."}
                  </li>
                  <li>
                    <span className="block text-ink">Literature (a count, not a search of everything)</span>
                    {l.co_mention.records_mentioning_all} of the {l.co_mention.records_searched} most relevant titles and abstracts (of {l.hit_count.toLocaleString()} Europe PMC hits for "
                    {l.query}") pair {verdict.genes} with {verdict.cellType}s in human tissue. Full texts were not read.
                  </li>
                </ul>
                <p className="mt-4 text-[12px] leading-relaxed text-ink-3">
                  One dataset, and protein from one person per group. Other explanations (a cell-labelling error beyond the
                  second rule tested, transcripts lying outside cells) are not fully ruled out; the next steps below say how to test them.
                </p>
              </section>
            );
          })}

      {done && (
        <>
          <section aria-label="Analysis" className="rise rounded-3xl bg-panel p-6">
            <h2 className="text-[20px] font-semibold">Analysis</h2>
            <p className="mt-1 text-[13px] text-ink-3">Written in code from the verdict, the verified claims, their controls and the lab's results. No model wrote these sentences.</p>
            <div className="mt-4 grid grid-cols-1 gap-6 lg:grid-cols-3">
              {(
                [
                  ["What happened", lab.report.what_happened],
                  ["Why we can say so", lab.report.why],
                  ["What to do next", lab.report.next_steps],
                ] as const
              ).map(([title, lines]) => (
                <div key={title}>
                  <h3 className="text-[14px] font-semibold">{title}</h3>
                  <ul className="mt-2 flex flex-col gap-2.5">
                    {lines.map((line) => (
                      <li key={line} className="text-[13px] leading-relaxed text-ink-2">
                        {line}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </section>

          {lab.figures.map((f) => (
            <figure key={f.task_id} className="rise rounded-3xl bg-panel p-6">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <p className="text-[12px] text-ink-3">
                  Figure {f.sub_claim + 1} · {subClaims[f.sub_claim]}
                </p>
                <div className="flex gap-2">
                  {[f.svg, f.pdf].map((name) => (
                    <a key={name} href={api.labFigureUrl(lab.investigation_id, name)} download className="h-8 rounded-full bg-raised px-3 text-[12px] leading-8 text-ink hover:bg-[#2a2d32]">
                      {name.endsWith(".svg") ? "SVG" : "PDF"}
                    </a>
                  ))}
                </div>
              </div>
              <h3 className="mt-1 text-[17px] font-semibold">{f.title}</h3>
              <img src={api.labFigureUrl(lab.investigation_id, f.png)} alt={f.title} className="mt-4 w-full rounded-xl bg-white p-3" loading="lazy" />
              <figcaption className="mt-3 text-[13px] leading-relaxed text-ink-2">
                <strong className="text-ink">Figure {f.sub_claim + 1}.</strong> {f.legend}
              </figcaption>
            </figure>
          ))}

          {lab.literature.map((l) => {
            const task = lab.tasks.find((t) => t.task_id === l.task_id);
            const byId = new Map(l.records.map((r) => [r.record_id, r]));
            return (
              <section key={l.task_id} aria-label="Literature" className="rise rounded-3xl bg-panel p-6">
                <p className="text-[12px] text-ink-3">Literature agent · part {(task?.sub_claim ?? 0) + 1}</p>
                <h3 className="mt-1 text-[17px] font-semibold">What the literature says</h3>
                <p className="mt-1 font-mono text-[12px] text-ink-3">
                  Europe PMC › {l.query} · {l.hit_count.toLocaleString()} hits · {l.records.length} most relevant read
                </p>
                <div className="mt-4 rounded-2xl bg-raised p-4">
                  <p className="text-[28px] leading-none font-semibold tracking-tight">
                    {l.co_mention.records_mentioning_all} <span className="text-[16px] font-normal text-ink-2">of {l.co_mention.records_searched}</span>
                  </p>
                  <p className="mt-2 text-[13px] leading-relaxed text-ink-2">{l.note}</p>
                </div>
                <ul className="mt-4 flex flex-col gap-3">
                  {l.statements.map((s) => (
                    <li key={s.text} className="text-[14px] leading-relaxed text-ink">
                      {s.text}{" "}
                      {s.cites.map((c) => {
                        const r = byId.get(c);
                        return (
                          <a key={c} href={r?.url} target="_blank" rel="noreferrer" title={r ? `${r.first_author ?? ""} ${r.year ?? ""}. ${r.title}. ${r.journal ?? ""}` : c} className="ml-1 rounded-full bg-[#1d2340] px-2 py-0.5 text-[11px] text-[#9fb0ff] hover:bg-[#28305a]">
                            {r?.first_author ?? c} {r?.year ?? ""}
                          </a>
                        );
                      })}
                    </li>
                  ))}
                </ul>
                {l.gap && <p className="mt-3 text-[13px] text-ink-2">Not addressed by these records: {l.gap}</p>}
                <p className="mt-3 text-[12px] text-ink-3">
                  Muse Spark read only the records listed; a check in code dropped {l.dropped.length} statement{l.dropped.length === 1 ? "" : "s"} citing anything not fetched.
                </p>
              </section>
            );
          })}

          {lab.protein.map((p) => (
            <section key={p.task_id} aria-label="Protein cross-check" className="rise rounded-3xl bg-panel p-6">
              <p className="text-[12px] text-ink-3">Protein cross-check · part {p.sub_claim + 1} · KPMP CODEX</p>
              <h3 className="mt-1 text-[17px] font-semibold">
                {p.marker} protein in {p.population}
              </h3>
              <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                {p.results.map((r) => {
                  const whole = r.conditions.find((c) => c.condition === "whole_cell");
                  const trimmed = r.conditions.find((c) => c.condition === "eroded_2px");
                  return (
                    <div key={r.participant_id} className="rounded-2xl bg-raised p-4">
                      <p className="text-[13px] text-ink-2">
                        {r.participant_id} · {r.role}
                      </p>
                      <p className="mt-1 text-[24px] font-semibold tracking-tight">
                        {pct(whole?.observed_share ?? null)} <span className="text-[14px] font-normal text-ink-3">→ {pct(trimmed?.observed_share ?? null)} trimmed</span>
                      </p>
                      <p className="mt-1 text-[12px] text-ink-3">
                        of {r.population_cells.toLocaleString()} {p.population}{" "}
                        <span className={`ml-1 rounded-full px-2 py-0.5 font-medium ${labelTone(r.label)}`}>{r.label.replaceAll("_", " ")}</span>
                      </p>
                    </div>
                  );
                })}
              </div>
              <p className="mt-3 text-[12px] leading-relaxed text-ink-3">{p.note}</p>
            </section>
          ))}
        </>
      )}
    </div>
  );
}

function Lane({ name, sub, start, end, progress, tone, note }: { name: string; sub: string; start: number; end: number; progress: number; tone: string; note: string }) {
  const shownEnd = Math.min(end, progress);
  const running = progress >= start && progress < end;
  const visible = progress >= start;
  return (
    <div className="grid grid-cols-1 items-center gap-1 md:grid-cols-[220px_1fr] md:gap-4">
      <div className="min-w-0">
        <p className="truncate text-[13px] font-medium text-ink">{name}</p>
        <p className="truncate font-mono text-[11px] text-ink-3">{sub}</p>
      </div>
      <div>
        <div className="relative h-3 rounded-full bg-raised">
          {visible && (
            <div
              className={`absolute inset-y-0 rounded-full bg-gradient-to-r ${tone} ${running ? "milestone" : ""}`}
              style={{ left: `${start * 100}%`, width: `${Math.max(0.6, (shownEnd - start) * 100)}%` }}
            />
          )}
        </div>
        {visible && <p className="mt-1 line-clamp-2 text-[12px] leading-relaxed text-ink-2">{note}</p>}
      </div>
    </div>
  );
}
