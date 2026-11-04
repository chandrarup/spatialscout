// SpatialScout: a guided path from what the product is, to the tissue, to a question, to the agent's run drawn live on a
// canvas, to the verdict. The open investigation's id lives in the URL hash, so a refresh reconnects with after_seq.
// A recorded run arrives whole; it is played back on the canvas one event at a time, in recorded order, with each
// event's recorded latency and cost shown, and the wait between events compressed.
import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { api } from "./api";
import { DualViewer } from "./components/DualViewer";
import { formatUtc } from "./components/RunModeBanner";
import { CONDITION_NAMES } from "./components/Viewer";
import { AgentBar, ScoutMark } from "./components/stage/AgentBar";
import { CompareView } from "./components/stage/CompareView";
import { Explore, type TissueContext } from "./components/stage/Explore";
import { Intro } from "./components/stage/Intro";
import { Results } from "./components/stage/Results";
import { RunCanvas } from "./components/stage/RunCanvas";
import { buildGraph, isStep, playbackDelay } from "./components/stage/runGraph";
import { type TissueFocus, TissuePanel } from "./components/TissuePanel";
import type { AuditIndex, DatasetManifest, InvestigationEvent, InvestigationSnapshot, KpmpManifest, ModeInfo, RunMode } from "./contracts/generated";
import type { DatasetAdapter, LoadedSection } from "./datasets/adapter";
import { kpmpAdapter } from "./datasets/kpmp";
import { moleculeAdapter } from "./datasets/molecules";
import { type InvestigationView, applyEvent, fromSnapshot, lastSeq } from "./investigation";

type Action = { type: "open"; view: InvestigationView } | { type: "event"; event: InvestigationEvent };
type Stage = "intro" | "explore" | "compare" | "classic" | "run" | "results" | "section";
type Rail = "rail" | "full" | "hidden";
const SPEEDS = [1, 2, 4];

function reducer(state: InvestigationView | null, action: Action): InvestigationView | null {
  switch (action.type) {
    case "open":
      return action.view;
    case "event":
      return state && state.investigationId === action.event.investigation_id ? applyEvent(state, action.event) : state;
  }
}

const INVESTIGATION_ID = /^inv-[0-9a-f]{12}$/;
const RUN_MODE_LABEL: Record<RunMode, string> = {
  immutable_replay: "Immutable replay",
  cached_tool_rerun: "Cached tool rerun",
  live: "Live run",
};
const RUN_MODE_NOTE: Record<RunMode, string> = {
  immutable_replay: "recorded events played back verbatim",
  cached_tool_rerun: "tools re-run, model responses from a recording",
  live: "fresh model calls under the spend budget",
};

/** The view as it stood after the first `count` events. */
function partial(view: InvestigationView, count: number): InvestigationView {
  if (count >= view.events.length) return view;
  const base: InvestigationView = {
    ...view,
    status: "planning",
    plan: null,
    claims: [],
    verifications: {},
    injected: [],
    verdict: null,
    pkg: null,
    events: [],
    error: null,
  };
  return view.events.slice(0, count).reduce(applyEvent, base);
}

export default function App() {
  const [mode, setMode] = useState<ModeInfo | null>(null);
  const [investigation, dispatch] = useReducer(reducer, null);
  const [stage, setStage] = useState<Stage>("intro");
  const [agentOpen, setAgentOpen] = useState(false);
  const [context, setContext] = useState<TissueContext | null>(null);
  const [approving, setApproving] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [kpmp, setKpmp] = useState<KpmpManifest | null | undefined>(undefined);
  const [audits, setAudits] = useState<AuditIndex | null>(null);
  const [strips, setStrips] = useState<{ section: LoadedSection; role: string }[]>([]);
  const [participantId, setParticipantId] = useState<string | null>(null);
  const [focus, setFocus] = useState<TissueFocus | null>(null);
  const [rail, setRail] = useState<Rail>("rail");
  const [follow, setFollow] = useState(true);
  const [shownCount, setShownCount] = useState(Number.POSITIVE_INFINITY);
  const [paused, setPaused] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [auditFirst, setAuditFirst] = useState(false);
  const unsubscribe = useRef<(() => void) | null>(null);
  const focused = useRef(new Set<string>());

  const [manifests, setManifests] = useState<DatasetManifest[]>([]);
  // The classic viewer offers every dataset: KPMP CODEX images, and the molecule datasets with SAM 3.1 box outlines.
  const adapters = useMemo<DatasetAdapter[]>(() => [...(kpmp ? [kpmpAdapter(kpmp)] : []), ...manifests.map(moleculeAdapter)], [kpmp, manifests]);
  const codexAdapter = useMemo(() => (kpmp ? kpmpAdapter(kpmp) : null), [kpmp]);

  const follow_ = useCallback((snapshot: InvestigationSnapshot, play: boolean) => {
    unsubscribe.current?.();
    const view = fromSnapshot(snapshot);
    dispatch({ type: "open", view });
    focused.current = new Set();
    setShownCount(play ? 0 : Number.POSITIVE_INFINITY);
    setPaused(false);
    setFollow(true);
    window.history.replaceState(null, "", `#${snapshot.investigation_id}`);
    if (snapshot.status !== "complete" && snapshot.status !== "failed") {
      unsubscribe.current = api.subscribe(snapshot.investigation_id, lastSeq(view), (event) => dispatch({ type: "event", event }));
    }
  }, []);

  useEffect(() => {
    api
      .mode()
      .then(setMode)
      .catch((error: unknown) => setProblem(String(error)));
    api
      .datasets()
      .then(setManifests)
      .catch(() => setManifests([]));
    api
      .kpmp()
      .then(setKpmp)
      .catch(() => setKpmp(null));
    const id = window.location.hash.slice(1);
    if (INVESTIGATION_ID.test(id))
      api
        .investigation(id)
        .then((snapshot) => {
          follow_(snapshot, false);
          setStage(snapshot.status === "complete" ? "results" : "run");
        })
        .catch(() => window.history.replaceState(null, "", " "));
    return () => unsubscribe.current?.();
  }, [follow_]);

  useEffect(() => {
    const datasetId = mode?.dataset_id === "synthetic" ? "GSE286184" : (mode?.dataset_id ?? "GSE286184");
    api
      .auditResults(datasetId)
      .then(setAudits)
      .catch(() => setAudits(null));
  }, [mode?.dataset_id]);

  // Both participants' images for the first screen, the diseased one first; the explore view opens the diseased one.
  useEffect(() => {
    if (!kpmp || !codexAdapter) return;
    const ordered = [...kpmp.participants].sort((a, b) => (a.role === "healthy reference" ? 1 : b.role === "healthy reference" ? -1 : 0));
    setParticipantId((p) => p ?? ordered[0]?.participant_id ?? null);
    Promise.all(ordered.map((p) => codexAdapter.load(p.participant_id).then((section) => ({ section, role: p.role }))))
      .then(setStrips)
      .catch(() => setStrips([]));
  }, [kpmp, codexAdapter]);
  const introChannels = useMemo(() => {
    const first = strips[0]?.section;
    return new Set(first && codexAdapter ? first.channels.filter((c) => !codexAdapter.defaultHidden?.has(c.id)).map((c) => c.id) : []);
  }, [strips, codexAdapter]);

  // Playback: reveal the next recorded event after its paced gap. A step is any event but a model call.
  const total = investigation?.events.length ?? 0;
  const playing = investigation !== null && shownCount < total;
  useEffect(() => {
    if (!investigation || paused || shownCount >= total) return;
    const events = investigation.events;
    const delay = playbackDelay(events[shownCount - 1], events[shownCount]!, speed);
    const timer = window.setTimeout(() => setShownCount((n) => n + 1), delay);
    return () => window.clearTimeout(timer);
  }, [investigation, paused, shownCount, total, speed]);
  const stepEnds = useMemo(() => (investigation ? investigation.events.flatMap((e, i) => (isStep(e) ? [i + 1] : [])) : []), [investigation]);
  const step = stepEnds.filter((end) => end <= Math.min(shownCount, total)).length;
  const goStep = (n: number) => {
    setPaused(true);
    const target = Math.max(1, Math.min(stepEnds.length, n));
    setShownCount(stepEnds[target - 1] ?? 0);
    setFollow(true);
  };

  const shown = useMemo(() => (investigation ? partial(investigation, shownCount) : null), [investigation, shownCount]);
  const graph = useMemo(() => buildGraph(shown?.question ?? "", shown?.events ?? []), [shown]);
  const current = graph.nodes.find((n) => n.id === graph.latest) ?? null;
  const datasetId = shown?.plan?.dataset_id ?? mode?.dataset_id ?? "GSE286184";

  // When a finding arrives, fly the tissue to its first evidence region and split it against the stricter condition.
  const focusFinding = useCallback(
    (findingId: string, then?: () => void) => {
      if (!investigation) return;
      api
        .investigationArtifact(investigation.investigationId, findingId)
        .then((result) => {
          const target = result.evidence_regions[0];
          if (!target) return;
          const genes =
            result.measure === "co_expression_score" ? result.genes.filter((g) => result.rules?.home_cell_types[g] !== result.population.cell_type) : result.genes;
          setFocus((f) => ({
            key: (f?.key ?? 0) + 1,
            sectionId: target.region.section_id,
            labelRuleId: result.population.label_rule_id,
            genes: result.genes,
            highlight: genes,
            cellType: result.population.cell_type,
            condition: target.condition ?? "nucleus_only",
            region: target.region,
          }));
          then?.();
        })
        .catch(() => undefined);
    },
    [investigation],
  );
  useEffect(() => {
    for (const node of graph.nodes) {
      const id = node.focus?.findingId;
      if (id && !focused.current.has(id)) {
        focused.current.add(id);
        if (stage === "run") focusFinding(id);
      }
    }
  }, [graph, focusFinding, stage]);

  const runsOn = (question: string): string | null => {
    const recording = mode?.recordings.find((r) => r.question.trim().toLowerCase() === question.trim().toLowerCase());
    if (recording) return recording.dataset_id ?? mode?.dataset_id ?? null;
    return mode?.dataset_id ?? null;
  };

  const ask = (question: string) => {
    setProblem(null);
    setContext(null);
    api
      .start({ question, run_mode: mode?.default_run_mode ?? "cached_tool_rerun", dataset_id: runsOn(question), regions: [] })
      .then((snapshot) => {
        follow_(snapshot, true);
        setFocus(null);
        setRail("rail");
        setAgentOpen(false);
        setStage("run");
      })
      .catch((error: unknown) => {
        const text = String(error).replace(/^Error:\s*/, "");
        setAgentOpen(true);
        setProblem(
          mode?.default_run_mode === "immutable_replay" ? `${text} This demo replays recorded runs only; pick one of the recorded questions.` : text,
        );
      });
  };

  const decide = (call: (investigationId: string) => Promise<InvestigationSnapshot>) => {
    if (!investigation) return;
    setApproving(true);
    call(investigation.investigationId)
      .then((snapshot) => snapshot.events.forEach((event) => dispatch({ type: "event", event })))
      .catch((error: unknown) => setProblem(String(error)))
      .finally(() => setApproving(false));
  };

  const busy = investigation !== null && (["planning", "running"].includes(investigation.status) || playing);
  const runMode = investigation?.runMode ?? mode?.default_run_mode ?? null;
  const replay = investigation ? investigation.replay : (mode?.recordings[0] ?? null);

  // Arrow keys step the run while presenting.
  useEffect(() => {
    if (stage !== "run" || !investigation) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === "ArrowRight") goStep(step + 1);
      if (e.key === "ArrowLeft") goStep(step - 1);
      if (e.key === " ") {
        e.preventDefault();
        setPaused((p) => !p);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const nav: { id: Stage; label: string; enabled: boolean }[] = [
    { id: "intro", label: "Overview", enabled: true },
    { id: "explore", label: "Tissue", enabled: !!kpmp },
    { id: "run", label: "Run", enabled: !!investigation },
    { id: "results", label: "Verdict", enabled: !!investigation?.verdict },
  ];
  const showBar = stage !== "intro" && stage !== "section" && stage !== "classic" && (stage !== "run" || !!shown);

  return (
    <div className="flex h-full flex-col bg-surface">
      <header className="relative z-30 flex h-[52px] shrink-0 items-center gap-6 px-5">
        <button type="button" onClick={() => setStage("intro")} className="flex items-center gap-2.5">
          <ScoutMark size={26} />
          <span className="text-[16px] font-semibold tracking-tight">SpatialScout</span>
        </button>
        <nav aria-label="Stages" className="hidden items-center gap-5 md:flex">
          {nav.map((item) => (
            <button
              key={item.id}
              type="button"
              disabled={!item.enabled}
              aria-current={stage === item.id || (item.id === "explore" && stage === "compare") ? "page" : undefined}
              onClick={() => setStage(item.id)}
              className="text-[14px] font-medium text-[#bbb] transition-colors hover:text-white disabled:text-[#555] aria-[current=page]:text-white"
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-3">
          {runMode && (
            <p role="status" className="hidden items-center gap-2 text-[13px] text-ink-2 sm:flex" title={RUN_MODE_NOTE[runMode]}>
              <span className="h-2 w-2 rounded-full bg-run-mode" aria-hidden="true" />
              <strong className="font-medium text-ink">{RUN_MODE_LABEL[runMode]}</strong>
              <span className="hidden lg:inline">
                {RUN_MODE_NOTE[runMode]}
                {replay && <> · recorded {formatUtc(replay.recorded_at)}</>}
                {replay?.origin === "hand_authored" && " · responses hand-authored"}
              </span>
            </p>
          )}
        </div>
      </header>

      <main className="relative min-h-0 flex-1">
        {stage === "intro" && (
          <Intro
            strips={strips}
            visible={introChannels}
            kpmp={kpmp}
            audits={audits}
            mode={mode}
            onExplore={() => setStage("explore")}
            onAsk={() => setAgentOpen(true)}
            onExample={ask}
          />
        )}
        {stage === "explore" && kpmp && codexAdapter && participantId && (
          <Explore
            adapter={codexAdapter}
            kpmp={kpmp}
            participantId={participantId}
            onParticipant={setParticipantId}
            onAsk={(c) => {
              setContext(c);
              setAgentOpen(true);
            }}
            onCompare={() => setStage("compare")}
            auditFirst={auditFirst}
          />
        )}
        {stage === "compare" && kpmp && codexAdapter && (
          <CompareView
            adapter={codexAdapter}
            kpmp={kpmp}
            onOpen={(id) => {
              setParticipantId(id);
              setStage("explore");
            }}
            onBack={() => setStage("explore")}
            onClassic={() => setStage("classic")}
          />
        )}
        {stage === "classic" && adapters.length > 0 && (
          <div className="flex h-full flex-col gap-3 p-4 *:flex-1">
            <DualViewer adapters={adapters} defaultDatasetId={kpmp?.dataset_id ?? manifests[0]?.dataset_id ?? null} onShow={() => undefined} onContext={() => undefined} />
          </div>
        )}
        {stage === "run" && shown && (
          <div className="absolute inset-0 flex">
            {/* The tissue the agent is working on: the main surface. */}
            <div className={`relative flex min-w-0 flex-1 flex-col ${rail === "full" ? "hidden" : ""}`}>
              <div className="flex-none px-5 pt-4 pb-2">
                <p className="text-[12px] text-ink-3">{playing ? "Replaying a recorded run" : shown.status.replaceAll("_", " ")}</p>
                <h1 className="mt-0.5 line-clamp-2 max-w-[60rem] text-[16px] leading-snug font-semibold">{shown.question}</h1>
                <p className="mt-1 max-w-[60rem] text-[13px] leading-relaxed text-ink-2">
                  {focus
                    ? `On screen: Xenium section ${focus.sectionId}, the region the agent cites for ${focus.cellType} ${focus.highlight.join("/")} (white box). Left of the divider, every molecule counted the usual way; right, the stricter ${CONDITION_NAMES[focus.condition] ?? focus.condition} rule, with the molecules it drops in yellow. Drag the divider.`
                    : "Each dot is one RNA molecule in a Xenium kidney section. When the agent's first result arrives, the view flies to the region it cites."}
                </p>
              </div>
              <div className="flex min-h-0 flex-1 flex-col px-3 pb-[150px] *:flex-1">
                <TissuePanel defaultDatasetId={datasetId} onShow={() => undefined} focus={focus} compact />
              </div>
              {rail === "hidden" && (
                <button type="button" onClick={() => setRail("rail")} className="absolute top-5 right-5 z-10 h-9 rounded-full bg-raised px-4 text-[13px] text-ink hover:bg-raised">
                  Show the agent's steps
                </button>
              )}
            </div>
            {/* The agent's steps, as a graph. */}
            {rail !== "hidden" && (
              <aside aria-label="The agent's steps" className={`relative flex flex-col bg-[#0d0e10] ${rail === "full" ? "flex-1" : "w-[min(44vw,620px)] border-l border-line"}`}>
                <header className="flex items-center justify-between gap-2 px-4 py-2.5">
                  <h2 className="text-[13px] font-semibold">
                    The agent's steps <span className="font-normal text-ink-3">· drag, zoom, click a card</span>
                  </h2>
                  <div className="flex gap-1">
                    {!follow && (
                      <button type="button" onClick={() => setFollow(true)} className="h-7 rounded-full px-2.5 text-[12px] text-ink-2 hover:bg-raised hover:text-ink">
                        Follow
                      </button>
                    )}
                    <button type="button" onClick={() => setRail(rail === "full" ? "rail" : "full")} className="h-7 rounded-full px-2.5 text-[12px] text-ink-2 hover:bg-raised hover:text-ink">
                      {rail === "full" ? "Show the tissue" : "Expand"}
                    </button>
                    <button type="button" onClick={() => setRail("hidden")} className="h-7 rounded-full px-2.5 text-[12px] text-ink-2 hover:bg-raised hover:text-ink">
                      Hide
                    </button>
                  </div>
                </header>
                <div className="relative min-h-0 flex-1 pb-[140px]">
                  <RunCanvas
                    graph={graph}
                    investigationId={shown.investigationId}
                    rightInset={0}
                    onFocus={(id) => focusFinding(id, () => rail === "full" && setRail("rail"))}
                    follow={follow}
                    onFollow={setFollow}
                    zoom={rail === "full" ? 0.9 : 0.72}
                  />
                </div>
              </aside>
            )}
          </div>
        )}
        {stage === "results" && shown && (
          <Results
            view={shown}
            graph={graph}
            mode={mode}
            libraryDatasetId={audits?.dataset_id ?? null}
            onCanvas={() => setStage("run")}
            onReplay={() => {
              setShownCount(0);
              setPaused(false);
              setFollow(true);
              setFocus(null);
              focused.current = new Set();
              setStage("run");
            }}
            onFocusFinding={(next) => {
              setFocus((f) => ({ ...next, key: (f?.key ?? 0) + 1 }));
              setStage("section");
            }}
            onOpenFinding={(id) => focusFinding(id, () => setStage("section"))}
            onAsk={ask}
            onProtein={() => {
              const diseased = kpmp?.participants.find((p) => p.role !== "healthy reference");
              if (diseased) setParticipantId(diseased.participant_id);
              setAuditFirst(true);
              setStage("explore");
            }}
            onReview={
              investigation && investigation.status === "complete" && investigation.runMode !== "immutable_replay"
                ? (claimId, decision) =>
                    api
                      .review(investigation.investigationId, claimId, { decision, reviewer: "Researcher", via: "click", confirmed: true })
                      .then((snapshot) => snapshot.events.forEach((event) => dispatch({ type: "event", event })))
                : undefined
            }
          />
        )}
        {stage === "section" && (
          <div className="flex h-full flex-col gap-2 p-4 *:flex-1">
            <button type="button" onClick={() => setStage(investigation?.verdict ? "results" : "run")} className="h-9 flex-none! self-start rounded-full bg-raised px-4 text-[13px] text-ink hover:bg-[#2a2d32]">
              ← Back
            </button>
            <TissuePanel defaultDatasetId={datasetId} onShow={() => undefined} focus={focus} />
          </div>
        )}
      </main>

      {showBar && (
        <div className="pointer-events-none fixed inset-x-0 bottom-4 z-40 flex justify-center px-3">
          <AgentBar
            mode={mode}
            view={stage === "run" ? shown : null}
            current={current}
            playback={
              stage === "run" && shown
                ? {
                    step,
                    steps: stepEnds.length,
                    playing,
                    paused,
                    speed,
                    onPause: () => setPaused((p) => !p),
                    onBack: () => goStep(step - 1),
                    onNext: () => goStep(step + 1),
                    onSpeed: () => setSpeed((s) => SPEEDS[(SPEEDS.indexOf(s) + 1) % SPEEDS.length]!),
                    onEnd: () => setShownCount(total),
                  }
                : null
            }
            busy={busy && stage !== "run"}
            problem={problem}
            context={context}
            onClearContext={() => setContext(null)}
            open={agentOpen}
            onOpen={setAgentOpen}
            onAsk={ask}
            onApprove={() => decide(api.approve)}
            onReject={() => decide(api.reject)}
            approving={approving}
            onResults={() => setStage("results")}
          />
        </div>
      )}
    </div>
  );
}
