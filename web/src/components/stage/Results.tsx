// The results: one verdict per part of the question, set large, each opening onto the evidence it rests on (the
// computed numbers the claim cites, every check the verifier ran, and the figure Muse Spark read). Then what to look at
// next, the evidence package, and the full detail folded away. Verdict words come from the frozen rule; the plain
// sentence under each is the rule's own definition applied to the sub-claim's prediction.
import { type ReactNode, useState } from "react";
import { api } from "../../api";
import type { Claim, LabRun, ModeInfo, ReviewRequest, SubClaimVerdict, VerificationResult } from "../../contracts/generated";
import type { InvestigationView } from "../../investigation";
import { BenchmarkCard } from "../BenchmarkCard";
import { ClaimCard, roundLongDecimals } from "../ClaimCard";
import { ExportButton } from "../ExportButton";
import { FindingsPanel } from "../FindingsPanel";
import { TelemetryPills } from "../TelemetryPills";
import type { TissueFocus } from "../TissuePanel";
import { LabView } from "./LabView";
import { outcomeOf } from "./outcome";
import { WorkSummary } from "./WorkSummary";
import { labelTone } from "./RunCanvas";
import type { RunGraph } from "./runGraph";

const VERDICT_TONE: Record<string, string> = {
  confirmed: "text-stable",
  refuted: "text-sensitive",
  inconclusive: "text-ink-2",
};
const OUTCOME_WORDS: Record<string, string> = { holds: "stays", drops: "falls away" };
/** The protein-level counterpart on the KPMP images, where one exists. */
const PROTEIN_TWIN: Record<string, { marker: string; population: string }> = {
  "Podocyte|LRP2": { marker: "LRP2", population: "Podocalyxin+" },
  "B cell|UMOD": { marker: "UMOD", population: "CD20+" },
};

function plain(v: SubClaimVerdict): string {
  const what = `${v.sub_claim.genes.join("/")} in ${v.sub_claim.cell_type}s`;
  const predicted = OUTCOME_WORDS[v.sub_claim.predicted] ?? v.sub_claim.predicted;
  const opposite = v.sub_claim.predicted === "holds" ? OUTCOME_WORDS.drops : OUTCOME_WORDS.holds;
  if (v.verdict === "confirmed") return `You predicted ${what} ${predicted} when molecules are assigned more strictly. It does.`;
  if (v.verdict === "refuted") return `You predicted ${what} ${predicted} when molecules are assigned more strictly. It ${opposite} instead.`;
  return `The evidence can't say whether ${what} ${predicted} under stricter assignment.`;
}

const STABLE_RULE =
  "Persists means no stricter rule took the share below about 71% of what random molecule loss alone predicts (expectation × 2^-0.5, frozen before the run). It is not a test of where the signal comes from.";

const pct1 = (x: number) => `${(x * 100).toFixed(1)}%`;

/** The claim's own cited numbers as one readable sentence: default share, nucleus-only share, and the random-loss
 *  expectation when the claim cites it. */
function measuredSentence(v: SubClaimVerdict, claim: Claim | undefined): string | null {
  if (!claim) return null;
  const value = (key: string) => claim.cited[key]?.value ?? null;
  const base = value("pooled[default].observed_value");
  const strict = value("pooled[nucleus_only].observed_value");
  if (base === null || strict === null) return null;
  const expected = value("pooled[nucleus_only].expectation_home_matched");
  const sections = value("eligible_section_ids.count");
  return (
    `In cells labelled ${v.sub_claim.cell_type}, ${pct1(base)} carry ${v.sub_claim.genes.join("/")} under the usual counting and ${pct1(strict)} when only molecules over the nucleus count` +
    (expected !== null ? `; random molecule loss alone would predict ${pct1(expected)}` : "") +
    (sections !== null ? ` (pooled over ${sections} sections).` : ".")
  );
}

/** Plain reading of the measured behaviour: which way it went, under how many counting rules, over how many sections. */
function holdsLine(claim: Claim): string | null {
  const conditions = new Set<string>();
  for (const key of Object.keys(claim.cited)) {
    const m = /^pooled\[([a-z0-9_]+)\]\.observed_value$/.exec(key);
    if (m) conditions.add(m[1]!);
  }
  if (conditions.size === 0) return null;
  const rules = conditions.size === 1 ? "1 counting rule" : `${conditions.size} counting rules`;
  const sections = claim.cited["eligible_section_ids.count"]?.value;
  const over = typeof sections === "number" ? ` across ${sections} sections` : "";
  if (claim.evidence_status === "stable") return `Holds up under every counting rule tested (${rules}${over})`;
  if (claim.evidence_status === "segmentation_sensitive") return `Changes under stricter counting (${rules}${over})`;
  return null;
}

/** A cited number's source, in words. */
function citedLabel(key: string): string {
  return key
    .replace("eligible_section_ids.count", "sections counted")
    .replace(/pooled\[default\]\./, "default assignment · ")
    .replace(/pooled\[nucleus_only\]\./, "nucleus-only · ")
    .replace(/pooled\[([a-z0-9_]+)\]\./, (_, c: string) => `${c.replaceAll("_", " ")} · `)
    .replace("observed_value", "observed share")
    .replace("expectation_home_matched", "expected from random thinning")
    .replace("default_molecules", "molecules")
    .replaceAll("_", " ");
}

function citedValue(key: string, value: number | null): string {
  if (value === null) return "–";
  if (/observed_value|expectation|share|retention/.test(key) && value <= 1) return `${(value * 100).toFixed(1)}%`;
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(3);
}

const CHECK_NAME: Record<string, string> = {
  structural: "References and controls",
  numerical: "Every number recomputed",
  visual: "Figure read by Muse Spark",
};

function Basis({ claim, verification, investigationId, onTissue }: { claim: Claim; verification: VerificationResult | undefined; investigationId: string; onTissue: () => void }) {
  return (
    <div className="mt-5 grid grid-cols-1 gap-4 border-t border-line pt-5 lg:grid-cols-[1fr_1fr]">
      <div className="flex flex-col gap-4">
        <div>
          <p className="text-[12px] text-ink-3">The claim the agent wrote</p>
          <p className="mt-1 text-[14px] leading-relaxed text-ink">{roundLongDecimals(claim.text)}</p>
          <p className="mt-1 text-[12px] text-ink-3">
            Evidence label <span className={`rounded-full px-2 py-0.5 font-medium ${labelTone(claim.evidence_status)}`}>{claim.evidence_status.replaceAll("_", " ")}</span> · finding{" "}
            {claim.finding.finding_id}
          </p>
        </div>
        <div>
          <p className="text-[12px] text-ink-3">1 · What the analysis engine computed</p>
          <ul className="mt-1.5 divide-y divide-line rounded-2xl bg-raised px-3">
            {Object.entries(claim.cited).map(([key, c]) => (
              <li key={key} className="flex items-baseline justify-between gap-3 py-1.5 text-[13px]">
                <span className="text-ink-2">{citedLabel(key)}</span>
                <span className="font-medium text-ink tabular-nums">{citedValue(key, c.value)}</span>
              </li>
            ))}
          </ul>
        </div>
        {verification && (
          <div>
            <p className="text-[12px] text-ink-3">2 · What the verifier checked</p>
            <ul className="mt-1.5 flex flex-col gap-1.5">
              {verification.checks.map((check) => (
                <li key={check.kind} className="rounded-2xl bg-raised px-3 py-2 text-[13px]">
                  <span className="flex items-center justify-between gap-2">
                    <span className="font-medium text-ink">{CHECK_NAME[check.kind] ?? check.kind}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${check.status === "passed" ? "bg-[#222a10] text-stable" : "bg-[#2c1a20] text-bad"}`}>{check.status}</span>
                  </span>
                  <span className="mt-0.5 block text-[12px] leading-relaxed text-ink-2">{roundLongDecimals(check.details)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      <div className="flex flex-col gap-3">
        <p className="text-[12px] text-ink-3">3 · The figure Muse Spark read</p>
        <img src={api.investigationFigureUrl(investigationId, claim.finding.finding_id)} alt={`Computed figure for ${claim.finding.finding_id}`} className="block w-full rounded-2xl bg-white" loading="lazy" />
        {verification?.visual && <p className="text-[13px] leading-relaxed text-ink-2">“{roundLongDecimals(verification.visual.explanation)}”</p>}
        <button type="button" onClick={onTissue} className="h-10 self-start rounded-full bg-white px-4 text-[13px] font-medium text-black">
          See it on the tissue
        </button>
      </div>
    </div>
  );
}

interface Props {
  view: InvestigationView;
  graph: RunGraph;
  /** The recording's audience-facing mission, if it has one; the exact question stays shown. */
  mission?: { title: string; summary: string; focus: string };
  chapters?: ReactNode;
  mode: ModeInfo | null;
  onCanvas: () => void;
  onReplay: () => void;
  onFocusFinding: (focus: Omit<TissueFocus, "key">) => void;
  onOpenFinding: (findingId: string) => void;
  onAsk: (question: string) => void;
  onProtein: () => void;
  onReview?: (claimId: string, decision: ReviewRequest["decision"]) => Promise<void>;
  /** The dataset whose committed audit library is browsable; null hides the library. */
  libraryDatasetId: string | null;
}

export function Results({ view, graph, mission, chapters, mode, onCanvas, onReplay, onFocusFinding, onOpenFinding, onAsk, onProtein, onReview, libraryDatasetId }: Props) {
  const [open, setOpen] = useState<number | null>(0);
  const [lab, setLab] = useState<LabRun | null>(null);
  const calls = view.events.filter((e) => e.type === "model_call").length;
  const tools = view.events.filter((e) => e.type === "tool_finished").length;
  const claimsById = new Map(view.claims.map((c) => [c.claim_id, c]));
  const others = (mode?.recordings ?? []).filter((r) => r.question.trim() !== view.question.trim() && !!r.dataset_id && r.dataset_id !== "synthetic");
  const twins = (view.verdict?.verdicts ?? [])
    .map((v) => ({ v, twin: v.sub_claim.genes.map((g) => PROTEIN_TWIN[`${v.sub_claim.cell_type}|${g}`]).find(Boolean) }))
    .filter((t) => t.twin);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-12 px-5 pt-10 pb-44">
        <section aria-label="Hypothesis verdict" className="rise">
          {chapters && <div className="mb-6">{chapters}</div>}
          <p className="text-[13px] text-ink-3">What the investigation found</p>
          {mission && <h1 className="mt-1 max-w-[56rem] text-[clamp(22px,2.4vw,30px)] leading-tight font-semibold tracking-tight">{mission.title}</h1>}
          <details className="mt-2 max-w-[56rem]" open={!mission}>
            <summary className="cursor-pointer text-[12px] text-ink-3">Exact research question{mission ? ` · ${mission.focus}` : ""}</summary>
            <p className="mt-1 text-[17px] leading-snug text-ink">{view.question}</p>
          </details>
          {view.verdict ? (
            <>
              <ul className="mt-7 flex flex-col gap-3">
                {view.verdict.verdicts.map((v, i) => {
                  const claim = v.claim_ids.map((id) => claimsById.get(id)).find(Boolean);
                  const expanded = open === i;
                  const outcome = outcomeOf(claim);
                  const sentence = measuredSentence(v, claim);
                  return (
                    <li key={v.sub_claim.text} data-testid="sub-claim-verdict" data-verdict={v.verdict} className={`scroll-mt-24 rounded-3xl bg-panel p-6 ring-1 ${outcome.ring}`}>
                      <button type="button" aria-expanded={expanded} onClick={() => setOpen(expanded ? null : i)} className="flex w-full flex-col gap-3 text-left">
                        <span className="flex flex-wrap items-baseline justify-between gap-3">
                          <span className="text-[13px] text-ink-3">
                            Part {i + 1} · {v.sub_claim.cell_type} · {v.sub_claim.genes.join("/")} · {v.dataset_id} RNA
                          </span>
                          <span className="shrink-0 text-[13px] font-medium text-ink underline decoration-ink-3 underline-offset-4">{expanded ? "Hide the evidence" : "Why?"}</span>
                        </span>
                        <span className={`block text-[clamp(28px,3.6vw,46px)] leading-[1.05] font-semibold tracking-[-0.03em] ${outcome.tone}`}>{outcome.title}</span>
                        {claim && holdsLine(claim) && <span className="block text-[15px] font-medium text-ink-2">{holdsLine(claim)}</span>}
                        {sentence && <span className="block max-w-[52rem] text-[16px] leading-relaxed text-ink">{sentence}</span>}
                        <span className="mt-1 flex flex-col gap-1 rounded-2xl bg-raised px-4 py-3 md:flex-row md:items-baseline md:gap-4">
                          <span className="shrink-0 text-[12px] text-ink-3">
                            Prediction check <span className={`ml-1 text-[14px] font-semibold uppercase ${VERDICT_TONE[v.verdict] ?? ""}`}>{v.verdict}</span>
                          </span>
                          <span className="text-[13px] leading-relaxed text-ink-2">
                            {plain(v)} This compares the researcher's prediction with the measured behaviour in these sections and controls; it is not a test of biological truth.
                          </span>
                        </span>
                      </button>
                      {expanded &&
                        (claim ? (
                          <Basis claim={claim} verification={view.verifications[claim.claim_id]} investigationId={view.investigationId} onTissue={() => onOpenFinding(claim.finding.finding_id)} />
                        ) : (
                          <p className="mt-4 border-t border-line pt-4 text-[14px] text-ink-2">{v.reason}</p>
                        ))}
                    </li>
                  );
                })}
              </ul>
              <p className="mt-4 max-w-[52rem] text-[13px] leading-relaxed text-ink-3">
                {STABLE_RULE} {view.verdict.scope} Outcomes and prediction checks come from fixed rules over verified claims; no model writes them.
              </p>
            </>
          ) : (
            <p className="mt-6 text-[15px] text-ink-2">No verdict yet: the run has not finished.</p>
          )}
        </section>

        {view.verdict && view.status === "complete" && <WorkSummary events={view.events} lab={lab?.investigation_id === view.investigationId ? lab : null} />}

        {view.verdict && view.status === "complete" && (
          <section aria-label="Lab" className="scroll-mt-6">
          <LabView investigationId={view.investigationId} subClaims={view.verdict.verdicts.map((v) => `${v.sub_claim.cell_type} · ${v.sub_claim.genes.join("/")}`)}
            verdicts={view.verdict.verdicts.map((v) => ({ verdict: v.verdict, predicted: v.sub_claim.predicted, cellType: v.sub_claim.cell_type, genes: v.sub_claim.genes.join("/") }))}
            onLab={setLab}
          />
          </section>
        )}

        <section aria-label="What to look at next" className="flex flex-col gap-3">
          <h2 className="text-[22px] font-semibold tracking-tight">What to look at next</h2>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {twins.map(({ v, twin }) => (
              <button key={v.sub_claim.text} type="button" onClick={onProtein} className="rounded-3xl bg-panel p-5 text-left transition-colors hover:bg-raised">
                <p className="flex flex-wrap items-center gap-2 text-[12px] text-ink-3">
                  Same question, different evidence
                  <span className="rounded-full bg-[#2a2213] px-2 py-0.5 font-medium text-run-mode">Different specimens</span>
                </p>
                <p className="mt-1 text-[16px] leading-snug font-semibold">
                  Is {twin!.marker} protein still there in {twin!.population} cells when their edges are trimmed?
                </p>
                <p className="mt-1 text-[13px] text-ink-2">The KPMP protein images are a different assay and different people, so this is a second line of evidence, not a repeat.</p>
              </button>
            ))}
            {others.map((r) => (
              <button key={r.recording_id} type="button" onClick={() => onAsk(r.question)} className="rounded-3xl bg-panel p-5 text-left transition-colors hover:bg-raised">
                <p className="text-[12px] text-ink-3">Recorded run · {r.dataset_id}</p>
                <p className="mt-1 text-[16px] leading-snug font-semibold">{r.question}</p>
              </button>
            ))}
          </div>
        </section>

        <section aria-label="Take the evidence" className="grid scroll-mt-6 grid-cols-1 gap-3 md:grid-cols-[1.4fr_1fr]">
          <button type="button" onClick={onCanvas} className="group flex flex-col items-start rounded-3xl bg-panel p-6 text-left transition-colors hover:bg-raised">
            <h2 className="text-[18px] font-semibold">How the agent got here</h2>
            <p className="mt-2 text-[14px] leading-relaxed text-ink-2">
              {graph.nodes.length} steps: {tools} tool results, {calls} model calls, {view.claims.length} claim{view.claims.length === 1 ? "" : "s"} and {view.injected.length} injected
              error{view.injected.length === 1 ? "" : "s"}, each with its recorded time and cost.
            </p>
            <span className="mt-4 inline-block text-[14px] font-medium underline decoration-ink-3 underline-offset-4 group-hover:decoration-white">Open the run</span>
          </button>
          <div className="flex flex-col justify-between gap-4 rounded-3xl bg-panel p-6">
            <div>
              <h2 className="text-[18px] font-semibold">Take the evidence with you</h2>
              <p className="mt-2 text-[14px] leading-relaxed text-ink-2">Claims, computed results, figures, the hash-linked audit log and a notebook that recomputes them.</p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <ExportButton pkg={view.pkg} />
              <button type="button" onClick={onReplay} className="h-11 rounded-full bg-raised px-5 text-[14px] text-ink hover:bg-[#2a2d32]">
                Replay the run
              </button>
            </div>
          </div>
        </section>

        <details aria-label="Checked claims" className="group scroll-mt-6 rounded-3xl bg-panel p-6">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
            <span>
              <span className="block text-[18px] font-semibold">All checked claims, including the injected errors</span>
              <span className="mt-1 block text-[14px] text-ink-2">
                {view.claims.length} claim{view.claims.length === 1 ? "" : "s"} and {view.injected.length} deliberately wrong cop{view.injected.length === 1 ? "y" : "ies"}, put through the same checks to
                show the verifier catches errors.
              </span>
            </span>
            <span className="text-[14px] text-ink-2 group-open:hidden">Show</span>
            <span className="hidden text-[14px] text-ink-2 group-open:inline">Hide</span>
          </summary>
          {libraryDatasetId && (
            <div className="mt-4">
              <BenchmarkCard datasetId={libraryDatasetId} />
            </div>
          )}
          <div className="mt-4 flex flex-col gap-3 [&_section]:rounded-3xl [&_section]:border-0 [&_section]:bg-raised [&_section]:p-5">
            {view.claims.map((claim) => (
              <ClaimCard
                key={claim.claim_id}
                claim={claim}
                verification={view.verifications[claim.claim_id]}
                investigationId={view.investigationId}
                onReview={onReview ? (decision) => onReview(claim.claim_id, decision) : undefined}
              />
            ))}
            {view.injected.map(({ claim, verification }) => (
              <ClaimCard key={claim.claim_id} claim={claim} verification={verification} />
            ))}
          </div>
        </details>

        <details className="group rounded-3xl bg-panel p-6">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
            <span>
              <span className="block text-[18px] font-semibold">Model calls</span>
              <span className="mt-1 block text-[14px] text-ink-2">Every Muse call with its model, provider, time and cost.</span>
            </span>
            <span className="text-[14px] text-ink-2 group-open:hidden">Show</span>
            <span className="hidden text-[14px] text-ink-2 group-open:inline">Hide</span>
          </summary>
          <div className="mt-4">
            <TelemetryPills events={view.events} />
          </div>
        </details>

        {libraryDatasetId && (
          <details className="group rounded-3xl bg-panel p-6">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
              <span>
                <span className="block text-[18px] font-semibold">Every audited finding in {libraryDatasetId}</span>
                <span className="mt-1 block text-[14px] text-ink-2">The full library behind these answers; open any finding on its section.</span>
              </span>
              <span className="text-[14px] text-ink-2 group-open:hidden">Show</span>
              <span className="hidden text-[14px] text-ink-2 group-open:inline">Hide</span>
            </summary>
            <div className="mt-4">
              <FindingsPanel datasetId={libraryDatasetId} onFocus={onFocusFinding} />
            </div>
          </details>
        )}
      </div>
    </div>
  );
}
