// The assistant, docked on the image. It behaves like a coding agent's terminal rather than a chat: its words stream
// in, each step it takes is a tool line with a status mark and a collapsible output, and its mark turns faster while
// it works. Before a run it reads back what the researcher picked (from computed values only) and offers questions;
// during a run it narrates the steps and is the presenter's remote; after the verdict it shows only the outcome.
import { useEffect, useMemo, useRef, useState } from "react";
import type { ModeInfo } from "../../contracts/generated";
import type { InvestigationView } from "../../investigation";
import { QuestionBar } from "../QuestionBar";
import { DataFitCard } from "./DataFitCard";
import type { TissueContext } from "./Explore";
import { KIND_LINE } from "./RunCanvas";
import { type RunNode, modelName } from "./runGraph";

export interface Playback {
  step: number;
  steps: number;
  playing: boolean;
  paused: boolean;
  speed: number;
  onPause: () => void;
  onBack: () => void;
  onNext: () => void;
  onSpeed: () => void;
  onEnd: () => void;
}

interface Props {
  mode: ModeInfo | null;
  /** The run on screen, if any; the bar narrates it. */
  view: InvestigationView | null;
  /** The run's steps so far. */
  nodes: RunNode[];
  latest: string | null;
  playback: Playback | null;
  busy: boolean;
  problem: string | null;
  context: TissueContext | null;
  onClearContext: () => void;
  open: boolean;
  onOpen: (open: boolean) => void;
  onAsk: (question: string) => void;
  /** The question being checked against the data, before it runs. */
  checking: string | null;
  /** What the asked question needs that the data here lacks, and where to get it. */
  dataFit: Omit<React.ComponentProps<typeof DataFitCard>, "onAsk"> | null;
  onApprove: () => void;
  onReject: () => void;
  approving: boolean;
  onResults: () => void;
}

/** Text that types itself out, restarting whenever the text changes. */
export function useTyped(text: string, charsPerSecond = 70): { shown: string; done: boolean } {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setCount(text.length);
      return;
    }
    setCount(0);
    const start = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const n = Math.min(text.length, Math.floor(((now - start) / 1000) * charsPerSecond));
      setCount(n);
      if (n < text.length) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [text, charsPerSecond]);
  return { shown: text.slice(0, count), done: count >= text.length };
}

export function Typed({ text, className = "", speed }: { text: string; className?: string; speed?: number }) {
  const { shown, done } = useTyped(text, speed);
  return <span className={`${className} ${done ? "" : "caret"}`}>{shown}</span>;
}

/** Recorded questions, the ones that mention what the researcher picked first; synthetic ones last. */
function ranked(mode: ModeInfo | null, context: TissueContext | null) {
  const synthetic = (d: string | null) => !d || d === "synthetic";
  const runs = [...(mode?.recordings ?? [])].sort((a, b) => Number(synthetic(a.dataset_id)) - Number(synthetic(b.dataset_id)));
  if (!context) return runs;
  const words = context.markers.flatMap((m) => (m === "CD20" ? ["B cell", "B-cell"] : m === "Podocalyxin" ? ["podocyte"] : [m]));
  const score = (q: string) => words.filter((w) => q.toLowerCase().includes(w.toLowerCase())).length;
  return [...runs].sort((a, b) => score(b.question) - score(a.question));
}

function short(question: string, max = 96): string {
  return question.length > max ? `${question.slice(0, max - 1).trimEnd()}…` : question;
}

function StepLine({ node, latest }: { node: RunNode; latest: boolean }) {
  const [open, setOpen] = useState(false);
  const call = node.calls[node.calls.length - 1];
  const tone = node.injected ? "text-sensitive" : node.state === "failed" ? "text-bad" : "text-stable";
  return (
    <li className={latest ? "" : "opacity-60"}>
      <button type="button" onClick={() => setOpen((o) => !o)} className="flex w-full items-baseline gap-2.5 text-left font-mono text-[12.5px] leading-relaxed">
        <span className={`w-3 shrink-0 text-center ${tone}`} aria-hidden="true">
          {node.state === "active" ? <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-stable" /> : node.injected ? "◆" : node.state === "failed" ? "✕" : "✓"}
        </span>
        <span className="min-w-0 flex-1 truncate">
          <span className="text-ink-3">{KIND_LINE[node.kind]} › </span>
          <span className="text-ink">{node.title}</span>
          {node.label && <span className="text-ink-3"> · {node.label.replaceAll("_", " ")}</span>}
        </span>
        {call && (
          <span className="hidden shrink-0 text-ink-3 sm:inline">
            {modelName(call)}
            {call.latency_ms > 0 && ` ${(call.latency_ms / 1000).toFixed(1)}s`}
          </span>
        )}
        {node.detail && <span className="shrink-0 text-ink-3">{open ? "▾" : "▸"}</span>}
      </button>
      {node.detail && (open || latest) && (
        <p className={`mt-0.5 mb-1 ml-[22px] border-l border-line pl-3 text-[12.5px] leading-relaxed text-ink-2 ${open ? "" : "line-clamp-2"}`}>
          {latest && !open ? <Typed text={node.detail} speed={170} /> : node.detail}
        </p>
      )}
    </li>
  );
}

export function AgentBar(props: Props) {
  const { view, nodes, latest, playback, mode, context, open } = props;
  const running = !!view && !!playback;
  const awaiting = view?.status === "awaiting_approval" && view.runMode !== "immutable_replay" && !playback?.playing;
  const log = useRef<HTMLOListElement>(null);
  const recent = useMemo(() => [...nodes].sort((a, b) => a.seq - b.seq).slice(-5), [nodes]);
  useEffect(() => {
    log.current?.scrollTo({ top: log.current.scrollHeight, behavior: "smooth" });
  }, [latest]);

  if (running) {
    const finished = !playback.playing && !!view.verdict;
    return (
      <section aria-label="Agent narration" aria-live="polite" className="pointer-events-auto w-[min(860px,calc(100vw-24px))] rounded-3xl bg-[#111214]/95 p-3 shadow-[0_16px_50px_rgb(0_0_0/0.6)] ring-1 ring-white/[0.08] backdrop-blur">
        <div className="flex items-start gap-3 px-1">
          <AgentOrb size={34} working={playback.playing && !playback.paused} />
          <div className="min-w-0 flex-1">
            {finished ? (
              <div>
                <p className="text-[12px] text-ink-3">Done · {playback.steps} steps</p>
                <ul className="mt-1 flex flex-wrap gap-x-5 gap-y-1">
                  {view.verdict!.verdicts.map((v) => (
                    <li key={v.sub_claim.text} className="flex items-baseline gap-2">
                      <span className={`text-[20px] font-semibold tracking-tight uppercase ${v.verdict === "confirmed" ? "text-stable" : v.verdict === "refuted" ? "text-sensitive" : "text-ink-2"}`}>{v.verdict}</span>
                      <span className="text-[13px] text-ink-2">
                        {v.sub_claim.cell_type} · {v.sub_claim.genes.join("/")}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <ol ref={log} className="flex max-h-[148px] flex-col gap-0.5 overflow-y-auto pr-1">
                {recent.map((n) => (
                  <StepLine key={n.id} node={n} latest={n.id === latest} />
                ))}
              </ol>
            )}
          </div>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-1 border-t border-line pt-2">
          <div className="mr-auto flex min-w-[80px] flex-1 items-center gap-2">
            <div className="h-1 flex-1 overflow-hidden rounded-full bg-raised">
              <div className="h-full rounded-full bg-gradient-to-r from-[#4a63ff] to-stable transition-[width] duration-500" style={{ width: `${(100 * playback.step) / Math.max(1, playback.steps)}%` }} />
            </div>
            <span className="font-mono text-[11px] text-ink-3 tabular-nums">
              {Math.max(1, playback.step)}/{playback.steps}
            </span>
          </div>
          {playback.playing && (
            <>
              <button type="button" onClick={playback.onBack} disabled={playback.step <= 1} className="h-8 rounded-full px-3 text-[13px] text-ink hover:bg-raised disabled:text-ink-3" aria-label="Previous step">
                ← Back
              </button>
              <button type="button" onClick={playback.onPause} className="h-8 min-w-[72px] rounded-full bg-white px-3 text-[13px] font-medium text-black">
                {playback.paused ? "Play" : "Pause"}
              </button>
              <button type="button" onClick={playback.onNext} className="h-8 rounded-full px-3 text-[13px] text-ink hover:bg-raised" aria-label="Next step">
                Next →
              </button>
              <button type="button" onClick={playback.onSpeed} className="h-8 rounded-full px-3 text-[13px] text-ink-2 hover:bg-raised" title="Playback speed">
                {playback.speed}×
              </button>
              <button type="button" onClick={playback.onEnd} className="h-8 rounded-full px-3 text-[13px] text-ink-2 hover:bg-raised">
                Skip to end
              </button>
            </>
          )}
          {finished && (
            <>
              <button type="button" onClick={playback.onBack} className="h-8 rounded-full px-3 text-[13px] text-ink hover:bg-raised">
                ← Step back
              </button>
              <button type="button" onClick={props.onResults} className="h-8 rounded-full bg-white px-4 text-[13px] font-medium text-black">
                See the verdict
              </button>
            </>
          )}
          {awaiting && (
            <>
              <button type="button" disabled={props.approving} onClick={props.onApprove} className="h-8 rounded-full bg-white px-4 text-[13px] font-medium text-black disabled:opacity-40">
                Approve and run
              </button>
              <button type="button" disabled={props.approving} onClick={props.onReject} className="h-8 rounded-full bg-raised px-4 text-[13px] text-ink disabled:opacity-40">
                Reject
              </button>
            </>
          )}
        </div>
        {props.problem && (
          <p role="alert" className="mt-2 rounded-2xl bg-[#2c1a20] px-3.5 py-2.5 text-[13px] text-bad">
            {props.problem}
          </p>
        )}
      </section>
    );
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => props.onOpen(true)}
        aria-label={context ? `Talk to SpatialScout about ${context.label}` : "Talk to SpatialScout"}
        className="pointer-events-auto flex h-14 w-[min(560px,calc(100vw-24px))] items-center gap-3 rounded-full bg-[#111214]/95 pr-2 pl-2.5 text-left shadow-[0_12px_40px_rgb(0_0_0/0.55)] ring-1 ring-white/[0.1] backdrop-blur transition-transform hover:scale-[1.01] active:scale-[0.99]"
      >
        <AgentOrb size={38} />
        <span className="min-w-0 flex-1 truncate text-[15px] text-ink-2">
          {context ? <Typed text={`Ask about ${context.label}`} speed={90} /> : <Typed text="Talk to SpatialScout" speed={40} />}
        </span>
        <span className="flex items-center gap-1.5 rounded-full bg-white px-4 py-2 text-[13px] font-medium text-black">
          <svg aria-hidden="true" viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
            <path d="M4 10v4M8 7v10M12 4v16M16 7v10M20 10v4" />
          </svg>
          Talk
        </span>
      </button>
    );
  }

  const runs = ranked(mode, context).slice(0, context ? 2 : 3);
  const greeting = context
    ? context.summary
    : "Ask me whether a gene really sits in a cell type, or is spillover from a neighbour. I'll plan the checks, run them on the tissue, and show you every step.";
  return (
    <section aria-label="Ask SpatialScout" className="drawer-up pointer-events-auto w-[min(680px,calc(100vw-24px))] rounded-3xl bg-[#111214]/97 p-4 shadow-[0_16px_50px_rgb(0_0_0/0.6)] ring-1 ring-white/[0.08] backdrop-blur">
      <header className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <AgentOrb size={34} working={props.busy} />
          <div>
            <h2 className="text-[15px] font-semibold">SpatialScout</h2>
            <p className="text-[12px] text-ink-3">powered by Muse Wonder and Muse Spark</p>
          </div>
        </div>
        <button type="button" onClick={() => props.onOpen(false)} aria-label="Close the assistant" className="grid h-9 w-9 place-items-center rounded-full text-ink-2 hover:bg-raised hover:text-ink">
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
          </svg>
        </button>
      </header>
      {props.checking ? (
        <p className="shimmer-text mt-3 text-[14px] leading-relaxed">Checking what this question needs against the data here…</p>
      ) : props.dataFit ? (
        <DataFitCard {...props.dataFit} onAsk={props.onAsk} />
      ) : (
        <p className="mt-3 text-[14px] leading-relaxed text-ink">
          <Typed text={greeting} speed={110} />
        </p>
      )}
      {context && !props.dataFit && (
        <button type="button" onClick={props.onClearContext} className="mt-1 text-[12px] text-ink-3 hover:text-ink">
          Clear the selection
        </button>
      )}
      {!props.busy && !props.dataFit && !props.checking && runs.length > 0 && (
        <ul className="mt-3 flex flex-col gap-0.5">
          {runs.map((r) => (
            <li key={r.recording_id}>
              <button type="button" onClick={() => props.onAsk(r.question)} className="group flex w-full items-baseline gap-2.5 rounded-xl px-2 py-1.5 text-left font-mono text-[12.5px] hover:bg-raised">
                <span className="text-stable">›</span>
                <span className="text-ink-2 group-hover:text-ink">{short(r.question)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-3">
        <QuestionBar examples={[]} busy={props.busy} onAsk={props.onAsk} placeholder={context ? "Ask about your selection…" : "Ask about a gene, a cell type, a condition…"} />
      </div>
      {props.problem && (
        <p role="alert" className="mt-2 rounded-2xl bg-[#2c1a20] px-3.5 py-2.5 text-[13px] text-bad">
          {props.problem}
        </p>
      )}
    </section>
  );
}

/** The agent's living mark: a colour ring that turns (faster while working) around a breathing core. */
export function AgentOrb({ size = 32, working = false }: { size?: number; working?: boolean }) {
  return (
    <span className="relative inline-grid shrink-0 place-items-center" style={{ width: size, height: size }} aria-hidden="true">
      <span className={`orb-ring absolute inset-0 rounded-full ${working ? "working" : ""}`} />
      <span className="absolute rounded-full bg-[#0b0c0e]" style={{ inset: Math.max(2, size * 0.09) }} />
      <span className="orb-core absolute rounded-full bg-gradient-to-br from-white to-[#c6f24e]" style={{ width: size * 0.3, height: size * 0.3 }} />
    </span>
  );
}

/** The product's mark: a cell outline with its nucleus, and one molecule just outside it. */
export function ScoutMark({ size = 28 }: { size?: number }) {
  return (
    <svg viewBox="0 0 32 32" width={size} height={size} aria-hidden="true">
      <circle cx="16" cy="16" r="15" fill="#000" />
      <circle cx="15" cy="17" r="8.5" fill="none" stroke="#fff" strokeWidth="2" />
      <circle cx="15" cy="17" r="3.2" fill="#4a63ff" />
      <circle cx="25" cy="8" r="2.4" fill="#c6f24e" />
    </svg>
  );
}
