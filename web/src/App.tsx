// SpatialScout: a guided path from what the product is, to the tissue, to a question, to the agent's run drawn live on a
// canvas, to the verdict. The open investigation's id lives in the URL hash, so a refresh reconnects with after_seq.
// A recorded run arrives whole; it is played back on the canvas one event at a time, in recorded order, with each
// event's recorded latency and cost shown, and the wait between events compressed.
import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { api } from "./api";
import { DualViewer } from "./components/DualViewer";
import { formatUtc } from "./components/RunModeBanner";
import { CONDITION_NAMES } from "./components/Viewer";
import { AgentBar, AgentOrb, ScoutMark } from "./components/stage/AgentBar";
import { type Chapter, ChapterStrip, chaptersOf, MISSIONS } from "./components/stage/Chapters";
import { CompareView } from "./components/stage/CompareView";
import { Connections } from "./components/stage/Connections";
import { Explore, type TissueContext } from "./components/stage/Explore";
import { Intro } from "./components/stage/Intro";
import { ResearchTeam } from "./components/stage/ResearchTeam";
import { Results } from "./components/stage/Results";
import { Upload } from "./components/stage/Upload";
import { RunCanvas } from "./components/stage/RunCanvas";
import { buildGraph, isStep, playbackDelay } from "./components/stage/runGraph";
import { type TissueFocus, TissuePanel } from "./components/TissuePanel";
import type { AuditIndex, DataFit, DatasetManifest, InvestigationEvent, InvestigationSnapshot, KpmpManifest, ModeInfo, RunMode } from "./contracts/generated";
import type { DatasetAdapter, LoadedSection } from "./datasets/adapter";
import { kpmpAdapter } from "./datasets/kpmp";
import { moleculeAdapter } from "./datasets/molecules";
import { type InvestigationView, applyEvent, fromSnapshot, lastSeq } from "./investigation";

type Action = { type: "open"; view: InvestigationView } | { type: "event"; event: InvestigationEvent };
type Stage = "intro" | "explore" | "compare" | "classic" | "run" | "results" | "section" | "upload";
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

interface Milestone {
  key: string;
  text: string;
  sub?: string;
  final?: boolean;
}

/** The moments worth announcing, each read from its own event. */
function milestonesOf(events: InvestigationEvent[]): Milestone[] {
  const out: Milestone[] = [];
  const once = (key: string, m: Omit<Milestone, "key">) => {
    if (!out.some((x) => x.key === key)) out.push({ key, ...m });
  };
  for (const e of events) {
    if (e.type === "model_call" && e.call.purpose === "plan") once("plan-call", { text: "Muse Wonder is planning the checks", sub: `${(e.call.latency_ms / 1000).toFixed(1)} s` });
    if (e.type === "plan_proposed") once("plan", { text: "Plan ready", sub: `${e.plan.steps.length} step${e.plan.steps.length === 1 ? "" : "s"}` });
    if (e.type === "plan_approved") once("approved", { text: "Plan approved · the analysis engine starts" });
    if (e.type === "tool_finished") once("first-result", { text: "First result in", sub: e.label?.replaceAll("_", " ") ?? undefined });
    if (e.type === "agent_decision") once("reading", { text: "Muse Spark is reading the results" });
    if (e.type === "claim_drafted") once("claims", { text: "Writing claims from the computed results" });
    if (e.type === "claim_verified" && !e.claim.injected.is_injected) once("verified", { text: "Claims checked: every number recomputed, every figure read", sub: e.verification.verification_status });
    if (e.type === "claim_verified" && e.claim.injected.is_injected) once("injected", { text: "Testing the verifier with a deliberately wrong claim", sub: e.verification.verification_status });
    if (e.type === "verdict") once("verdict", { text: "Findings ready", sub: `prediction check: ${e.verdict.verdicts.map((v) => v.verdict).join(" · ")}`, final: true });
  }
  return out;
}

/** The finished run in one line: steps, model calls, recorded wall time and summed recorded cost. */
function runSummary(events: InvestigationEvent[]) {
  const calls = events.filter((e) => e.type === "model_call");
  const cost = calls.reduce((sum, e) => sum + (e.type === "model_call" ? (e.call.estimated_cost_usd ?? 0) : 0), 0);
  const times = events.map((e) => Date.parse(e.recorded_at_utc)).filter(Number.isFinite);
  const ms = times.length ? Math.max(...times) - Math.min(...times) : 0;
  const minutes = ms >= 60_000 ? `${Math.floor(ms / 60_000)} min ${Math.round((ms % 60_000) / 1000)} s` : `${Math.round(ms / 1000)} s`;
  return { steps: events.filter(isStep).length, calls: calls.length, cost, minutes };
}

const RAIL_KEY = "spatialscout.railWidth";
const DEFAULT_RAIL = 560;
const MIN_RAIL = 300;
const MIN_TISSUE = 360;

function useNarrow(): boolean {
  const query = "(max-width: 767px)";
  const [narrow, setNarrow] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const list = window.matchMedia(query);
    const on = () => setNarrow(list.matches);
    list.addEventListener("change", on);
    return () => list.removeEventListener("change", on);
  }, []);
  return narrow;
}

/** The separator between the tissue and the steps: drag it, or focus it and use the arrow keys (Home resets). */
function SplitHandle({ width, onWidth }: { width: number; onWidth: (w: number) => void }) {
  const clamp = (w: number, total: number) => Math.max(MIN_RAIL, Math.min(total - MIN_TISSUE, w));
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize the tissue and the agent's steps"
      aria-valuemin={MIN_RAIL}
      aria-valuenow={Math.round(width)}
      tabIndex={0}
      className="group relative z-10 w-2 shrink-0 cursor-col-resize touch-none bg-line/40 outline-none hover:bg-white/20 focus-visible:bg-white/40"
      onKeyDown={(e) => {
        const total = e.currentTarget.parentElement?.clientWidth ?? window.innerWidth;
        if (e.key === "ArrowLeft") onWidth(clamp(width + 40, total));
        else if (e.key === "ArrowRight") onWidth(clamp(width - 40, total));
        else if (e.key === "Home") onWidth(clamp(DEFAULT_RAIL, total));
        else return;
        e.preventDefault();
        e.stopPropagation();
      }}
      onPointerDown={(e) => {
        const parent = e.currentTarget.parentElement;
        if (!parent) return;
        e.currentTarget.setPointerCapture(e.pointerId);
        const box = parent.getBoundingClientRect();
        const move = (event: PointerEvent) => onWidth(clamp(box.right - event.clientX, box.width));
        const up = () => {
          window.removeEventListener("pointermove", move);
          window.removeEventListener("pointerup", up);
        };
        window.addEventListener("pointermove", move);
        window.addEventListener("pointerup", up);
      }}
    >
      <span className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-white/30 group-hover:bg-white/70" aria-hidden="true" />
    </div>
  );
}

export default function App() {
  const [mode, setMode] = useState<ModeInfo | null>(null);
  const [investigation, dispatch] = useReducer(reducer, null);
  const [stage, setStage] = useState<Stage>("intro");
  const [agentOpen, setAgentOpen] = useState(false);
  const [context, setContext] = useState<TissueContext | null>(null);
  const [approving, setApproving] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [uploadPrefill, setUploadPrefill] = useState<DataFit["upload_prefill"] | null>(null);
  const [kpmp, setKpmp] = useState<KpmpManifest | null | undefined>(undefined);
  const [audits, setAudits] = useState<AuditIndex | null>(null);
  const [strips, setStrips] = useState<{ section: LoadedSection; role: string }[]>([]);
  const [participantId, setParticipantId] = useState<string | null>(null);
  const [focus, setFocus] = useState<TissueFocus | null>(null);
  const [railChoice, setRail] = useState<Rail>("rail");
  const narrow = useNarrow();
  // On phones the tissue and the steps take turns rather than sharing a narrow row.
  const rail: Rail = narrow && railChoice === "rail" ? "hidden" : railChoice;
  const [railWidth, setRailWidthState] = useState(() => {
    const saved = Number(window.localStorage.getItem(RAIL_KEY));
    return Number.isFinite(saved) && saved >= MIN_RAIL ? saved : DEFAULT_RAIL;
  });
  const setRailWidth = useCallback((w: number) => {
    setRailWidthState(w);
    window.localStorage.setItem(RAIL_KEY, String(Math.round(w)));
  }, []);
  const [graphFit, setGraphFit] = useState(0);
  const [railView, setRailView] = useState<"team" | "graph">("team");
  const [recording, setRecording] = useState(() => window.localStorage.getItem("spatialscout.recording") === "on");
  useEffect(() => {
    document.documentElement.dataset.recording = recording ? "on" : "off";
    window.localStorage.setItem("spatialscout.recording", recording ? "on" : "off");
  }, [recording]);
  const [follow, setFollow] = useState(true);
  const [shownCount, setShownCount] = useState(Number.POSITIVE_INFINITY);
  const [paused, setPaused] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [auditFirst, setAuditFirst] = useState(false);
  const unsubscribe = useRef<(() => void) | null>(null);
  const focused = useRef(new Set<string>());
  const seenMilestones = useRef(new Set<string>());

  const [manifests, setManifests] = useState<DatasetManifest[]>([]);
  // The classic viewer offers every dataset: KPMP CODEX images, and the molecule datasets with SAM 3.1 box outlines.
  const adapters = useMemo<DatasetAdapter[]>(() => [...(kpmp ? [kpmpAdapter(kpmp)] : []), ...manifests.map(moleculeAdapter)], [kpmp, manifests]);
  const codexAdapter = useMemo(() => (kpmp ? kpmpAdapter(kpmp) : null), [kpmp]);

  const follow_ = useCallback((snapshot: InvestigationSnapshot, play: boolean) => {
    unsubscribe.current?.();
    const view = fromSnapshot(snapshot);
    dispatch({ type: "open", view });
    focused.current = new Set();
    seenMilestones.current = new Set();
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

  // One diseased and one healthy-reference image for the first screen (the hero has two rows), the diseased one
  // first; the explore view opens the diseased one.
  useEffect(() => {
    if (!kpmp || !codexAdapter) return;
    const ordered = [...kpmp.participants].sort((a, b) => (a.role === "healthy reference" ? 1 : b.role === "healthy reference" ? -1 : 0));
    setParticipantId((p) => p ?? ordered[0]?.participant_id ?? null);
    const shown = [ordered.find((p) => p.role !== "healthy reference"), ordered.find((p) => p.role === "healthy reference")].filter((p) => p !== undefined);
    Promise.all(shown.map((p) => codexAdapter.load(p.participant_id).then((section) => ({ section, role: p.role }))))
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
  const chapters = useMemo(() => (investigation ? chaptersOf(investigation.events) : []), [investigation]);
  const mission = investigation?.replay ? MISSIONS[investigation.replay.recording_id] : undefined;
  const [chapterId, setChapterId] = useState<string | null>(null);
  const [connectionsOpen, setConnectionsOpen] = useState(false);
  const graph = useMemo(() => buildGraph(shown?.question ?? "", shown?.events ?? []), [shown]);
  const milestones = useMemo(() => milestonesOf(shown?.events ?? []), [shown]);
  const [toasts, setToasts] = useState<Milestone[]>([]);
  useEffect(() => {
    const fresh = milestones.filter((m) => !seenMilestones.current.has(m.key));
    if (fresh.length === 0) return;
    for (const m of fresh) seenMilestones.current.add(m.key);
    const latest = fresh[fresh.length - 1]!;
    setToasts((t) => [...t.filter((x) => x.key !== latest.key), latest].slice(-2));
    window.setTimeout(() => setToasts((t) => t.filter((x) => x.key !== latest.key)), latest.final ? 6000 : 4200);
  }, [milestones]);
  const finishedRun = !!shown?.verdict && !playing;
  const summary = useMemo(() => (shown ? runSummary(shown.events) : null), [shown]);
  const collapsedFor = useRef<string | null>(null);
  useEffect(() => {
    if (finishedRun && shown && collapsedFor.current !== shown.investigationId && stage === "run") {
      collapsedFor.current = shown.investigationId;
      setRail("hidden");
    }
  }, [finishedRun, shown, stage]);
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

  // A chapter during the run seeks playback to its events; after the run it opens the findings section it names.
  const selectChapter = (chapter: Chapter) => {
    if (!investigation) return;
    setChapterId(chapter.id);
    if (chapter.atEvent !== null) {
      setPaused(true);
      setShownCount(chapter.atEvent);
      setFollow(true);
      setStage("run");
      if (chapter.id === "data") {
        const events = investigation.events;
        const audits = events.filter((e) => e.type === "tool_started" && e.tool === "audit_population");
        const pick = audits.find((e) => e.type === "tool_started" && JSON.stringify(e.arguments).includes('"B cell"')) ?? audits[0];
        const done = pick && events.find((e) => e.type === "tool_finished" && pick.type === "tool_started" && e.observation_id === pick.observation_id);
        if (done && done.type === "tool_finished" && done.artifact_id) focusFinding(done.artifact_id);
      }
      return;
    }
    openFindings(chapter.section ?? "");
  };
  /** Open the findings at the first of `labels` (separated by "|") that exists there. */
  function openFindings(labels: string) {
    if (!investigation?.verdict) return;
    setStage("results");
    window.setTimeout(() => {
      const target = labels
        .split("|")
        .map((label) => document.querySelector<HTMLElement>(`[aria-label="${label}"]`))
        .find(Boolean);
      if (!target) return;
      if (target instanceof HTMLDetailsElement) target.open = true;
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      target.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    }, 120);
  }
  const currentChapter =
    stage === "run" ? ([...chapters].reverse().find((c) => c.atEvent !== null && Math.min(shownCount, total) >= c.atEvent)?.id ?? null) : stage === "results" ? chapterId : null;

  const runsOn = (question: string): string | null => {
    const recording = mode?.recordings.find((r) => r.question.trim().toLowerCase() === question.trim().toLowerCase());
    if (recording) return recording.dataset_id ?? mode?.dataset_id ?? null;
    return mode?.dataset_id ?? null;
  };

  // Before a question that no recording answers runs, the data check says what it needs that the workspace lacks.
  const [fit, setFit] = useState<DataFit | null>(null);
  const [searching, setSearching] = useState(false);
  const [checking, setChecking] = useState<string | null>(null);
  const canRun = mode?.default_run_mode === "live";
  const recorded = (question: string) => mode?.recordings.some((r) => r.question.trim().toLowerCase() === question.trim().toLowerCase()) ?? false;

  const ask = (question: string) => {
    setProblem(null);
    setFit(null);
    if (recorded(question)) return start(question);
    setChecking(question);
    setAgentOpen(true);
    api
      .dataFit(question, false)
      .then((first) => {
        if (first.answerable && first.gaps.length === 0 && canRun) return start(question);
        setFit(first);
        if (first.gaps.length === 0) return;
        setSearching(true);
        return api
          .dataFit(question, true)
          .then((full) => setFit((now) => (now?.question === question ? full : now)))
          .finally(() => setSearching(false));
      })
      .catch(() => start(question))
      .finally(() => setChecking(null));
  };

  const start = (question: string) => {
    setFit(null);
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
    { id: "results", label: "Findings", enabled: !!investigation?.verdict },
    { id: "upload", label: "Your data", enabled: true },
  ];
  const showBar = stage !== "intro" && stage !== "upload" && stage !== "section" && stage !== "classic" && (stage !== "run" || !!shown);

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
          <button type="button" onClick={() => setConnectionsOpen(true)} className="h-8 rounded-full bg-raised px-3 text-[12px] text-ink hover:bg-[#2a2d32] sm:text-[13px]">
            Connections
          </button>
          <button
            type="button"
            aria-pressed={recording}
            onClick={() => setRecording((r) => !r)}
            title="A steadier screen for recording: no drifting images, the run mode and recording time always shown. Results are unchanged."
            className="hidden h-8 rounded-full bg-raised px-3 text-[12px] text-ink-2 hover:text-ink aria-pressed:bg-white aria-pressed:text-black sm:block sm:text-[13px]"
          >
            Recording mode
          </button>
          {runMode && (
            <p role="status" className="flex items-center gap-2 text-[12px] text-ink-2 sm:text-[13px]" title={RUN_MODE_NOTE[runMode]}>
              <span className="h-2 w-2 rounded-full bg-run-mode" aria-hidden="true" />
              <strong className="font-medium text-ink">{RUN_MODE_LABEL[runMode]}</strong>
              <span className={recording ? "inline" : "hidden lg:inline"}>
                {RUN_MODE_NOTE[runMode]}
                {replay && <> · recorded {formatUtc(replay.recorded_at)}</>}
                {replay?.origin === "hand_authored" && " · responses hand-authored"}
              </span>
            </p>
          )}
        </div>
      </header>
      {connectionsOpen && <Connections mode={mode} onClose={() => setConnectionsOpen(false)} />}
      <nav aria-label="Stages (narrow screens)" className="flex shrink-0 gap-1 overflow-x-auto px-3 pb-2 md:hidden">
        {nav.map((item) => (
          <button
            key={item.id}
            type="button"
            disabled={!item.enabled}
            aria-current={stage === item.id || (item.id === "explore" && stage === "compare") ? "page" : undefined}
            onClick={() => setStage(item.id)}
            className="h-8 shrink-0 rounded-full px-3 text-[13px] font-medium text-[#bbb] disabled:text-[#555] aria-[current=page]:bg-raised aria-[current=page]:text-white"
          >
            {item.label}
          </button>
        ))}
      </nav>

      <main className="relative min-h-0 flex-1">
        {stage === "intro" && (
          <Intro
            key={recording ? "still" : "drift"}
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
            onAsk={(c) => {
              setContext(c);
              setAgentOpen(true);
            }}
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
            <div className={`relative flex min-w-0 flex-1 flex-col overflow-y-auto md:overflow-visible ${rail === "full" ? "hidden" : ""}`}>
              <div className="flex-none px-5 pt-4 pb-2">
                <p className="text-[12px] text-ink-3">{playing ? "Replaying a recorded investigation" : shown.status.replaceAll("_", " ")}</p>
                {mission ? (
                  <>
                    <h1 className="mt-0.5 max-w-[60rem] text-[18px] leading-snug font-semibold">{mission.title}</h1>
                    <p className="mt-0.5 max-w-[60rem] text-[13px] leading-relaxed text-ink-2">{mission.summary}</p>
                    <details className="mt-1 max-w-[60rem] text-[12px] text-ink-3">
                      <summary className="cursor-pointer">Exact research question · {mission.focus}</summary>
                      <p className="mt-1 text-[13px] leading-snug text-ink">{shown.question}</p>
                    </details>
                  </>
                ) : (
                  <h1 className="mt-0.5 line-clamp-2 max-w-[60rem] text-[16px] leading-snug font-semibold">{shown.question}</h1>
                )}
                {chapters.length > 0 && (
                  <div className="mt-2">
                    <ChapterStrip chapters={chapters} shownCount={Math.min(shownCount, total)} finished={finishedRun} current={currentChapter} onSelect={selectChapter} />
                  </div>
                )}
                <p className="mt-1 max-w-[60rem] text-[13px] leading-relaxed text-ink-2">
                  {focus
                    ? `On screen: Xenium section ${focus.sectionId}, the region the agent cites for ${focus.cellType} ${focus.highlight.join("/")} (outlined). Yellow: the molecules the stricter ${CONDITION_NAMES[focus.condition] ?? focus.condition} rule drops. Switch the counting rule above the tissue, or compare both rules on the same section.`
                    : "Each dot is one RNA molecule in a Xenium kidney section. When the agent's first result arrives, the view flies to the region it cites."}
                </p>
              </div>
              <div className="flex min-h-[60vh] flex-1 flex-col px-3 pb-2 *:flex-1 md:min-h-0">
                <TissuePanel defaultDatasetId={datasetId} focus={focus} compact />
              </div>
              {/* Milestones: glow while the agent works, then fade. */}
              <div className="pointer-events-none absolute inset-x-0 bottom-6 z-20 hidden flex-col items-center gap-2 md:flex">
                {toasts.map((t) => (
                  <div key={t.key} className="milestone flex items-center gap-3 rounded-full bg-[#111214]/95 py-2 pr-5 pl-2 backdrop-blur">
                    <AgentOrb size={26} working={!t.final} />
                    <span className="text-[14px] font-medium text-ink">{t.text}</span>
                    {t.sub && <span className="text-[12px] text-ink-3">{t.sub}</span>}
                  </div>
                ))}
              </div>
              {rail === "hidden" && (
                <button
                  type="button"
                  onClick={() => setRail("rail")}
                  className="order-first mx-5 mt-3 flex items-center gap-3 self-start rounded-full bg-raised py-2 pr-4 pl-3 text-left text-[13px] text-ink ring-1 ring-white/[0.06] hover:bg-[#2a2d32] md:absolute md:top-4 md:right-5 md:z-10 md:m-0"
                >
                  <span className={`h-2 w-2 rounded-full ${finishedRun ? "bg-stable" : "animate-pulse bg-stable"}`} />
                  {finishedRun && summary ? (
                    <span>
                      Run complete · {summary.steps} steps · {summary.calls} model calls · {summary.minutes} · ${summary.cost.toFixed(2)}
                      <span className="ml-2 text-ink-3">Show the steps</span>
                    </span>
                  ) : (
                    "Show the agent's steps"
                  )}
                </button>
              )}
            </div>
            {rail === "rail" && <SplitHandle width={railWidth} onWidth={setRailWidth} />}
            {/* The agent's steps, as a graph. */}
            {rail !== "hidden" && (
              <aside
                aria-label="The agent's steps"
                className={`relative flex min-w-0 flex-col bg-[#0d0e10] ${rail === "full" ? "flex-1" : "shrink-0"}`}
                style={rail === "full" ? undefined : { width: `min(${railWidth}px, calc(100% - ${MIN_TISSUE}px))` }}
              >
                <header className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5">
                  <div className="flex gap-1" role="tablist" aria-label="How to show the agent's steps">
                    {(
                      [
                        ["team", "Research team"],
                        ["graph", "Detailed graph"],
                      ] as const
                    ).map(([id, label]) => (
                      <button
                        key={id}
                        type="button"
                        role="tab"
                        aria-selected={railView === id}
                        onClick={() => setRailView(id)}
                        className="h-7 rounded-full px-3 text-[13px] font-semibold text-ink-3 hover:text-ink aria-selected:bg-raised aria-selected:text-ink"
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <div className="flex flex-wrap gap-1">
                    <button type="button" onClick={() => setFollow(true)} disabled={follow} className="h-7 rounded-full px-2.5 text-[12px] text-ink-2 hover:bg-raised hover:text-ink disabled:text-ink-3">
                      {follow ? "Following the run" : "Follow evidence"}
                    </button>
                    <button type="button" onClick={() => setGraphFit((k) => k + 1)} className="h-7 rounded-full px-2.5 text-[12px] text-ink-2 hover:bg-raised hover:text-ink">
                      Fit graph
                    </button>
                    <button type="button" onClick={() => setRail(rail === "full" ? "rail" : "full")} className="h-7 rounded-full px-2.5 text-[12px] text-ink-2 hover:bg-raised hover:text-ink">
                      {rail === "full" ? "Show the tissue" : "Expand"}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setRail("rail");
                        setRailWidth(DEFAULT_RAIL);
                      }}
                      className="h-7 rounded-full px-2.5 text-[12px] text-ink-2 hover:bg-raised hover:text-ink"
                    >
                      Reset layout
                    </button>
                    <button type="button" onClick={() => setRail("hidden")} className="h-7 rounded-full px-2.5 text-[12px] text-ink-2 hover:bg-raised hover:text-ink">
                      Hide
                    </button>
                  </div>
                </header>
                {railView === "team" && (
                  <div className="relative min-h-0 flex-1">
                    <ResearchTeam
                      events={shown.events}
                      investigationId={shown.investigationId}
                      complete={finishedRun}
                      onOpen={(target) => {
                        if (target.kind === "graph") setRailView("graph");
                        else if (target.kind === "finding") focusFinding(target.id, () => rail === "full" && setRail("rail"));
                        else openFindings(target.section);
                      }}
                    />
                  </div>
                )}
                <div className={`relative min-h-0 flex-1 ${railView === "graph" ? "" : "hidden"}`}>
                  <RunCanvas
                    graph={graph}
                    investigationId={shown.investigationId}
                    rightInset={0}
                    onFocus={(id) => focusFinding(id, () => rail === "full" && setRail("rail"))}
                    follow={follow}
                    onFollow={setFollow}
                    zoom={rail === "full" ? 0.9 : 0.72}
                    fitKey={graphFit}
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
            mission={mission}
            chapters={
              chapters.length > 0 ? <ChapterStrip chapters={chapters} shownCount={Math.min(shownCount, total)} finished={finishedRun} current={currentChapter} onSelect={selectChapter} /> : null
            }
            mode={mode}
            libraryDatasetId={audits?.dataset_id ?? null}
            onCanvas={() => setStage("run")}
            onReplay={() => {
              setShownCount(0);
              setPaused(false);
              setFollow(true);
              setFocus(null);
              focused.current = new Set();
              seenMilestones.current = new Set();
              collapsedFor.current = null;
              setRail("rail");
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
        {stage === "upload" && <Upload key={JSON.stringify(uploadPrefill)} prefill={uploadPrefill} />}
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
        <div className={stage === "run" ? "relative z-40 flex shrink-0 justify-center border-t border-line px-3 py-2" : "pointer-events-none fixed inset-x-0 bottom-4 z-40 flex justify-center px-3"}>
          <AgentBar
            mode={mode}
            view={stage === "run" ? shown : null}
            nodes={graph.nodes}
            latest={graph.latest}
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
            checking={checking}
            dataFit={
              fit
                ? {
                    fit,
                    searching,
                    canRun,
                    onAskAnyway: () => start(fit.question),
                    onUpload: (prefill) => {
                      setUploadPrefill(prefill);
                      setFit(null);
                      setAgentOpen(false);
                      setStage("upload");
                    },
                    onDismiss: () => setFit(null),
                  }
                : null
            }
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
