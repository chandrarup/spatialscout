// The assistant, docked on the image at the bottom of the screen instead of in a chat window. Before a run it takes a
// question (typed or spoken), with what the researcher picked on the tissue as context and the recorded runs as
// one-click starts. During a run it is the narrator and the presenter's remote: the step on screen in plain words,
// built from that event's own fields, with back, play and next.
import { useState } from "react";
import type { ModeInfo } from "../../contracts/generated";
import type { InvestigationView } from "../../investigation";
import { QuestionBar } from "../QuestionBar";
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
  current: RunNode | null;
  playback: Playback | null;
  busy: boolean;
  problem: string | null;
  context: TissueContext | null;
  onClearContext: () => void;
  open: boolean;
  onOpen: (open: boolean) => void;
  onAsk: (question: string) => void;
  onApprove: () => void;
  onReject: () => void;
  approving: boolean;
  onResults: () => void;
}

/** Recorded questions, the ones that mention what the researcher picked first. */
function ranked(mode: ModeInfo | null, context: TissueContext | null) {
  const runs = [...(mode?.recordings ?? [])].sort((a, b) => Number(a.dataset_id === "synthetic") - Number(b.dataset_id === "synthetic"));
  if (!context) return runs;
  const words = context.markers.flatMap((m) => (m === "CD20" ? ["B cell", "B-cell", "CD20"] : m === "Podocalyxin" ? ["podocyte", "Podocyte"] : [m]));
  const score = (q: string) => words.filter((w) => q.toLowerCase().includes(w.toLowerCase())).length;
  return [...runs].sort((a, b) => score(b.question) - score(a.question));
}

export function AgentBar(props: Props) {
  const { view, current, playback, mode, context, open } = props;
  const [detail, setDetail] = useState(false);
  const running = !!view && !!playback;
  const awaiting = view?.status === "awaiting_approval" && view.runMode !== "immutable_replay" && !playback?.playing;

  if (running && current) {
    const call = current.calls[current.calls.length - 1];
    return (
      <section aria-label="Agent narration" aria-live="polite" className="pointer-events-auto w-[min(820px,calc(100vw-24px))] rounded-3xl bg-[#16171b]/95 ring-1 ring-white/[0.08] p-3 shadow-[0_16px_50px_rgb(0_0_0/0.6)] backdrop-blur">
        <div className="flex items-start gap-3 px-1">
          <ScoutMark size={34} pulse={playback.playing && !playback.paused} />
          <div className="min-w-0 flex-1">
            <p className="text-[12px] text-ink-3">
              Step {Math.max(1, playback.step)} of {playback.steps} · {KIND_LINE[current.kind]}
              {call && ` · ${modelName(call)}${call.latency_ms > 0 ? `, ${(call.latency_ms / 1000).toFixed(1)} s` : ""}`}
            </p>
            <h2 className="text-[16px] leading-snug font-semibold">{current.title}</h2>
            {current.detail && (
              <button type="button" onClick={() => setDetail((d) => !d)} className="block w-full text-left">
                <p className={`mt-0.5 text-[13px] leading-relaxed whitespace-pre-line text-ink-2 ${detail ? "" : "line-clamp-2"}`}>{current.detail}</p>
              </button>
            )}
          </div>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-1 border-t border-line pt-2">
          <div className="mr-auto h-1 min-w-[80px] flex-1 overflow-hidden rounded-full bg-raised">
            <div className="h-full rounded-full bg-white transition-[width] duration-500" style={{ width: `${(100 * playback.step) / Math.max(1, playback.steps)}%` }} />
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
          {!playback.playing && view.verdict && (
            <>
              <button type="button" onClick={playback.onBack} className="h-8 rounded-full px-3 text-[13px] text-ink hover:bg-raised">
                ← Back
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
        className="pointer-events-auto flex h-14 w-[min(560px,calc(100vw-24px))] items-center gap-3 rounded-full bg-white pr-2 pl-3 text-left text-black shadow-[0_12px_40px_rgb(0_0_0/0.55)] transition-transform hover:scale-[1.01] active:scale-[0.99]"
      >
        <ScoutMark size={34} pulse />
        <span className="flex-1 truncate text-[15px] text-black/60">{context ? `Ask about ${context.label}…` : "Ask SpatialScout about this tissue…"}</span>
        <span className="rounded-full bg-black px-4 py-2 text-[13px] font-medium text-white">Ask</span>
      </button>
    );
  }

  const runs = ranked(mode, context);
  return (
    <section aria-label="Ask SpatialScout" className="drawer-up pointer-events-auto w-[min(720px,calc(100vw-24px))] rounded-3xl bg-[#16171b]/97 ring-1 ring-white/[0.08] p-4 shadow-[0_16px_50px_rgb(0_0_0/0.6)] backdrop-blur">
      <header className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <ScoutMark size={34} pulse />
          <div>
            <h2 className="text-[16px] font-semibold">SpatialScout</h2>
            <p className="text-[12px] text-ink-3">Plans with Muse Wonder, checks figures with Muse Spark. Every number it shows is computed.</p>
          </div>
        </div>
        <button type="button" onClick={() => props.onOpen(false)} aria-label="Close the assistant" className="grid h-9 w-9 place-items-center rounded-full text-ink-2 hover:bg-raised hover:text-ink">
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
          </svg>
        </button>
      </header>
      {context && (
        <div className="mt-3 flex items-center justify-between gap-2 rounded-2xl bg-raised px-3 py-2 text-[13px]">
          <span className="text-ink-2">
            About <span className="text-ink">{context.label}</span>
          </span>
          <button type="button" onClick={props.onClearContext} className="text-[12px] text-ink-3 hover:text-ink">
            Clear
          </button>
        </div>
      )}
      {!props.busy && runs.length > 0 && (
        <div className="mt-3">
          <p className="text-[12px] text-ink-3">
            {mode?.default_run_mode === "immutable_replay"
              ? "This demo plays recorded runs. Each one ran on the GSE286184 Xenium kidney sections (RNA molecules), not on the protein image."
              : "Recorded questions you can run again:"}
          </p>
          <ul className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
            {runs.map((r, i) => (
              <li key={r.recording_id}>
                <button
                  type="button"
                  onClick={() => props.onAsk(r.question)}
                  className="flex h-full w-full flex-col gap-1.5 rounded-2xl bg-raised p-3 text-left transition-colors hover:bg-[#2a2d32]"
                >
                  <span className="text-[13px] leading-snug text-ink">{r.question}</span>
                  <span className="text-[11px] text-ink-3">
                    {i === 0 && context ? "Closest to your selection · " : ""}
                    {r.dataset_id ?? "synthetic section"} · {r.origin === "live" ? "recorded live" : "hand-authored responses"}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="mt-3">
        <QuestionBar examples={[]} busy={props.busy} onAsk={props.onAsk} />
      </div>
      {props.problem && (
        <p role="alert" className="mt-2 rounded-2xl bg-[#2c1a20] px-3.5 py-2.5 text-[13px] text-bad">
          {props.problem}
        </p>
      )}
    </section>
  );
}

/** The product's mark: a cell outline with its nucleus, and one molecule just outside it. */
export function ScoutMark({ size = 28, pulse = false }: { size?: number; pulse?: boolean }) {
  return (
    <span className="relative inline-grid shrink-0 place-items-center" style={{ width: size, height: size }}>
      {pulse && <span className="mark-pulse absolute inset-0 rounded-full" aria-hidden="true" />}
      <svg viewBox="0 0 32 32" width={size} height={size} aria-hidden="true" className="relative">
        <circle cx="16" cy="16" r="15" fill="#000" />
        <circle cx="15" cy="17" r="8.5" fill="none" stroke="#fff" strokeWidth="2" />
        <circle cx="15" cy="17" r="3.2" fill="#4a63ff" />
        <circle cx="25" cy="8" r="2.4" fill="#c6f24e" />
      </svg>
    </span>
  );
}
