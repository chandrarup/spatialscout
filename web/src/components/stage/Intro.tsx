// The first screen: the name, the question it answers, and the tissue itself. Both KPMP participants' CODEX images
// drift across the top in opposite directions until touched; below, the three things SpatialScout does, each shown
// with something real. Every count is read from a manifest or index the server serves.
import type { AuditIndex, KpmpManifest, ModeInfo } from "../../contracts/generated";
import type { LoadedSection } from "../../datasets/adapter";
import { CodexView } from "./CodexView";

interface Props {
  strips: { section: LoadedSection; role: string }[];
  visible: ReadonlySet<string>;
  kpmp: KpmpManifest | null | undefined;
  audits: AuditIndex | null;
  mode: ModeInfo | null;
  onExplore: () => void;
  onAsk: () => void;
  /** Ask one of the recorded questions straight away. */
  onExample: (question: string) => void;
}

const PIPELINE: { who: string; does: string }[] = [
  { who: "You", does: "ask in plain words" },
  { who: "Muse Wonder", does: "plans the checks" },
  { who: "Analysis engine", does: "re-counts every molecule under stricter rules" },
  { who: "Controls", does: "random thinning, label swaps" },
  { who: "Verifier", does: "recomputes every number; Muse Spark reads each figure" },
  { who: "Frozen rule", does: "gives the verdict" },
];

const VERDICTS: { word: string; tone: string; means: string }[] = [
  { word: "Confirmed", tone: "text-stable", means: "the signal behaved the way your hypothesis predicted" },
  { word: "Refuted", tone: "text-sensitive", means: "it did the opposite of what you predicted" },
  { word: "Inconclusive", tone: "text-ink-2", means: "the evidence can't separate the two" },
];

/** The featured recorded question: the one with a confirmed and a refuted part, else the first real-data one. */
export function featuredQuestion(mode: ModeInfo | null): string | null {
  const runs = mode?.recordings ?? [];
  return (runs.find((r) => r.recording_id.includes("two-part")) ?? runs.find((r) => r.dataset_id && r.dataset_id !== "synthetic") ?? runs[0])?.question ?? null;
}

export function Intro({ strips, visible, kpmp, audits, mode, onExplore, onAsk, onExample }: Props) {
  const example = featuredQuestion(mode);
  const diseased = kpmp?.participants.find((p) => p.role !== "healthy reference");
  const figure = audits?.entries.find((e) => e.cell_type === "Podocyte" && e.genes.length === 1 && e.genes[0] === "LRP2");

  return (
    <div className="h-full overflow-y-auto">
      <section aria-label="SpatialScout" className="relative flex flex-col">
        <div className="relative grid h-[44vh] min-h-[280px] grid-rows-2 gap-1">
          {strips.length > 0
            ? strips.map((s, i) => (
                <div key={s.section.sectionId} className="relative min-h-0">
                  <CodexView section={s.section} visible={visible} drift direction={i % 2 === 0 ? 1 : -1} phase={i * 0.35} fill={2.6} />
                  <p className="pointer-events-none absolute top-3 right-4 rounded-full bg-black/75 px-3 py-1 text-[12px] text-ink-2">
                    Participant {s.section.sectionId} · {s.role} · kidney biopsy, CODEX
                  </p>
                </div>
              ))
            : [0, 1].map((i) => <div key={i} className="bg-black" />)}
          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-surface to-transparent" />
        </div>

        <div className="relative mx-auto -mt-16 w-full max-w-[1180px] px-5 pb-8">
          <p className="rise text-[clamp(52px,8.4vw,112px)] leading-[0.9] font-semibold tracking-[-0.05em]">SpatialScout</p>
          <div className="rise mt-5 grid grid-cols-1 items-end gap-6 [animation-delay:100ms] lg:grid-cols-[1.2fr_1fr]">
            <div>
              <h1 className="text-[clamp(24px,2.6vw,34px)] leading-tight font-semibold tracking-[-0.02em]">Is it the cell, or its neighbour?</h1>
              <p className="mt-3 max-w-[38rem] text-[17px] leading-relaxed text-ink">
                In spatial transcriptomics, a molecule from one cell is easily counted toward the cell beside it. SpatialScout is an AI agent on Meta's Muse models
                that re-counts the molecules under stricter rules, runs the controls and tells you which kidney findings still hold.
              </p>
            </div>
            <div className="flex flex-wrap gap-3 lg:justify-end">
              <button type="button" onClick={onExplore} className="pointer-events-auto h-12 rounded-full bg-white px-6 text-[15px] font-medium text-black transition-transform hover:scale-[1.02] active:scale-95">
                Start with the diseased biopsy
              </button>
              <button
                type="button"
                onClick={example ? () => onExample(example) : onAsk}
                className="pointer-events-auto h-12 rounded-full bg-raised px-6 text-[15px] text-ink transition-colors hover:bg-[#2a2d32]"
              >
                Watch a recorded run
              </button>
            </div>
          </div>
        </div>
      </section>

      <section aria-label="What SpatialScout does" className="mx-auto grid w-full max-w-[1180px] grid-cols-1 gap-3 px-5 pb-20 md:grid-cols-3">
        <article className="flex flex-col overflow-hidden rounded-3xl bg-panel">
          <div className="p-5">
            <p className="text-[13px] text-ink-3">1 · Look</p>
            <h2 className="mt-1 text-[19px] font-semibold">Explore real kidney tissue</h2>
            <p className="mt-1.5 text-[14px] leading-relaxed text-ink-2">
              {diseased
                ? `Participant ${diseased.participant_id}'s biopsy, ${diseased.cells.toLocaleString()} cells. Switch proteins, show marker-positive cells, click one, or box a region.`
                : "A diseased kidney biopsy. Switch proteins, click a cell, or box a region."}
            </p>
            <button type="button" onClick={onExplore} className="mt-3 text-[14px] font-medium underline decoration-ink-3 underline-offset-4 hover:decoration-white">
              Open the biopsy
            </button>
          </div>
          {figure && audits && (
            <img
              src={`/api/datasets/${encodeURIComponent(audits.dataset_id)}/audit-results/${figure.finding_id}/figure.png`}
              alt={`Computed figure: ${figure.cell_type} ${figure.genes.join("/")}, ${figure.label}`}
              className="mt-auto block w-full bg-white"
              loading="lazy"
            />
          )}
        </article>

        <article className="flex flex-col rounded-3xl bg-panel p-5">
          <p className="text-[13px] text-ink-3">2 · Ask</p>
          <h2 className="mt-1 text-[19px] font-semibold">Watch the agent work it out</h2>
          <ol className="mt-3 flex flex-col gap-1.5">
            {PIPELINE.map((p, i) => (
              <li key={p.who} className="flex items-baseline gap-3 text-[14px]">
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-raised text-[12px] font-semibold">{i + 1}</span>
                <span>
                  <span className="font-medium text-ink">{p.who}</span> <span className="text-ink-2">{p.does}</span>
                </span>
              </li>
            ))}
          </ol>
          {example && (
            <button type="button" onClick={() => onExample(example)} className="mt-auto pt-4 text-left text-[14px] leading-relaxed text-ink">
              <span className="text-ink-3">Try: </span>“{example}”
              <span className="mt-1 block font-medium underline decoration-ink-3 underline-offset-4">Run this recorded question</span>
            </button>
          )}
        </article>

        <article className="flex flex-col rounded-3xl bg-panel p-5">
          <p className="text-[13px] text-ink-3">3 · Decide</p>
          <h2 className="mt-1 text-[19px] font-semibold">Get a verdict you can trace</h2>
          <ul className="mt-3 flex flex-col gap-3">
            {VERDICTS.map((v) => (
              <li key={v.word}>
                <p className={`text-[24px] leading-none font-semibold tracking-tight ${v.tone}`}>{v.word}</p>
                <p className="mt-1 text-[14px] text-ink-2">{v.means}</p>
              </li>
            ))}
          </ul>
          <dl className="mt-auto grid grid-cols-3 gap-3 pt-5">
            <div>
              <dt className="text-[12px] text-ink-3">Findings audited</dt>
              <dd className="text-[22px] font-semibold">{audits ? audits.entries.length : "–"}</dd>
            </div>
            <div>
              <dt className="text-[12px] text-ink-3">Xenium sections</dt>
              <dd className="text-[22px] font-semibold">{audits ? audits.sections_counted.length : "–"}</dd>
            </div>
            <div>
              <dt className="text-[12px] text-ink-3">Recorded runs</dt>
              <dd className="text-[22px] font-semibold">{mode ? mode.recordings.length : "–"}</dd>
            </div>
          </dl>
        </article>
      </section>
    </div>
  );
}
