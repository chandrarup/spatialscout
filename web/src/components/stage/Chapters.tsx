// The guided view of an investigation: six chapters, each bound to real events of the run (or a section of the
// findings that the run produced). A chapter is reached only when its events have played; nothing here invents a step.
import type { InvestigationEvent } from "../../contracts/generated";

export interface Chapter {
  id: string;
  title: string;
  /** Number of events that must have played for the chapter to be reached; null for post-run chapters. */
  atEvent: number | null;
  /** The findings section the chapter opens (aria-label), for chapters after the run. */
  section?: string;
}

/** Presentation metadata for a recording: an audience-facing mission and summary. The recorded question, events and
 *  outcomes are untouched and stay available under "Exact research question". */
export const MISSIONS: Record<string, { title: string; summary: string; focus: string }> = {
  "gse286184-two-part-hypothesis": {
    title: "Investigate an unexpected signal in kidney immune cells",
    summary:
      "Check whether it survives stricter counting, inspect available protein evidence, read relevant research and prepare the evidence for a follow-up experiment.",
    focus: "Summarises the recording's B-cell UMOD branch; the podocyte LRP2 branch and all its evidence are shown alongside it.",
  },
};

export function chaptersOf(events: InvestigationEvent[]): Chapter[] {
  const index = (pred: (e: InvestigationEvent) => boolean) => {
    const i = events.findIndex(pred);
    return i < 0 ? null : i + 1;
  };
  const lastIndex = (pred: (e: InvestigationEvent) => boolean) => {
    for (let i = events.length - 1; i >= 0; i--) if (pred(events[i]!)) return i + 1;
    return null;
  };
  const planned = index((e) => e.type === "plan_approved") ?? index((e) => e.type === "plan_proposed");
  const firstResult = index((e) => e.type === "tool_finished");
  const lastCheck = lastIndex((e) => e.type === "tool_finished" || e.type === "agent_decision");
  return [
    { id: "question", title: "The question", atEvent: planned },
    { id: "checks", title: "The checks", atEvent: firstResult },
    { id: "data", title: "What the data shows", atEvent: lastCheck },
    { id: "evidence", title: "Other evidence", atEvent: null, section: "Lab" },
    { id: "review", title: "Review the result", atEvent: null, section: "Checked claims" },
    { id: "next", title: "The next experiment", atEvent: null, section: "Analysis|Take the evidence" },
  ];
}

interface Props {
  chapters: Chapter[];
  shownCount: number;
  finished: boolean;
  current: string | null;
  onSelect: (chapter: Chapter) => void;
}

export function ChapterStrip({ chapters, shownCount, finished, current, onSelect }: Props) {
  return (
    <ol aria-label="Chapters" className="flex gap-1 overflow-x-auto pb-1">
      {chapters.map((c, i) => {
        const reached = c.atEvent !== null ? shownCount >= c.atEvent : finished;
        const available = c.atEvent !== null || finished;
        return (
          <li key={c.id} className="shrink-0">
            <button
              type="button"
              disabled={!available}
              aria-current={current === c.id ? "step" : undefined}
              onClick={() => onSelect(c)}
              title={available ? undefined : "Opens once the run has finished"}
              className="flex h-8 items-center gap-2 rounded-full bg-raised/60 px-3 text-[12px] text-ink-2 transition-colors hover:bg-raised hover:text-ink disabled:opacity-40 aria-[current=step]:bg-white aria-[current=step]:text-black"
            >
              <span className={`grid h-4 w-4 place-items-center rounded-full text-[10px] font-semibold ${reached ? "bg-stable text-black" : "bg-[#2a2d32] text-ink-3"}`}>{i + 1}</span>
              {c.title}
            </button>
          </li>
        );
      })}
    </ol>
  );
}
