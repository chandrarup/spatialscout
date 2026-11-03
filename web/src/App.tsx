// SpatialScout workspace: question bar, tissue viewer, capability report, plan, events, claims and export.
// The open investigation's id lives in the URL hash, so a refresh reconnects with after_seq and loses nothing.
import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { api } from "./api";
import { ClaimCard } from "./components/ClaimCard";
import { DatasetCapabilities } from "./components/DatasetPanel";
import { EventLog } from "./components/EventLog";
import { ExportButton } from "./components/ExportButton";
import { PlanCard } from "./components/PlanCard";
import { QuestionBar } from "./components/QuestionBar";
import { RunModeBanner } from "./components/RunModeBanner";
import { TissuePanel } from "./components/TissuePanel";
import type { DatasetManifest, InvestigationEvent, InvestigationSnapshot, ModeInfo } from "./contracts/generated";
import { type InvestigationView, applyEvent, fromSnapshot, lastSeq } from "./investigation";

type Action = { type: "open"; view: InvestigationView } | { type: "event"; event: InvestigationEvent };

function reducer(state: InvestigationView | null, action: Action): InvestigationView | null {
  switch (action.type) {
    case "open":
      return action.view;
    case "event":
      return state && state.investigationId === action.event.investigation_id ? applyEvent(state, action.event) : state;
  }
}

const INVESTIGATION_ID = /^inv-[0-9a-f]{12}$/;

export default function App() {
  const [mode, setMode] = useState<ModeInfo | null>(null);
  const [shown, setShown] = useState<{ manifest: DatasetManifest; sectionId: string } | null>(null);
  const show = useCallback((manifest: DatasetManifest, sectionId: string) => setShown({ manifest, sectionId }), []);
  const [investigation, dispatch] = useReducer(reducer, null);
  const [approving, setApproving] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const unsubscribe = useRef<(() => void) | null>(null);

  const follow = useCallback((snapshot: InvestigationSnapshot) => {
    unsubscribe.current?.();
    const view = fromSnapshot(snapshot);
    dispatch({ type: "open", view });
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
    const id = window.location.hash.slice(1);
    if (INVESTIGATION_ID.test(id)) api.investigation(id).then(follow).catch(() => window.history.replaceState(null, "", " "));
    return () => unsubscribe.current?.();
  }, [follow]);

  const ask = (question: string) => {
    setProblem(null);
    api
      .start({ question, run_mode: mode?.default_run_mode ?? "cached_tool_rerun" })
      .then(follow)
      .catch((error: unknown) => setProblem(String(error)));
  };

  const approve = () => {
    if (!investigation) return;
    setApproving(true);
    api
      .approve(investigation.investigationId)
      .then((snapshot) => snapshot.events.forEach((event) => dispatch({ type: "event", event })))
      .catch((error: unknown) => setProblem(String(error)))
      .finally(() => setApproving(false));
  };

  const busy = investigation !== null && ["planning", "running"].includes(investigation.status);

  return (
    <div className="flex h-screen flex-col">
      <RunModeBanner
        runMode={investigation?.runMode ?? mode?.default_run_mode ?? "cached_tool_rerun"}
        replay={investigation ? investigation.replay : (mode?.recordings[0] ?? null)}
      />
      <header className="flex flex-col gap-3 border-b border-line px-4 py-3 lg:flex-row lg:items-start">
        <div className="shrink-0 lg:w-56">
          <h1 className="text-lg font-semibold tracking-tight text-ink">SpatialScout</h1>
          <p className="text-xs text-ink-3">
            {shown ? `${shown.manifest.dataset_id} · section ${shown.sectionId}` : "loading section…"}
          </p>
        </div>
        <div className="min-w-0 flex-1">
          <QuestionBar examples={mode?.recordings.map((r) => r.question) ?? []} busy={busy} onAsk={ask} />
        </div>
      </header>
      <main className="grid min-h-0 flex-1 grid-cols-1 gap-3 overflow-y-auto p-3 lg:grid-cols-[minmax(0,1fr)_26rem] lg:overflow-hidden">
        <TissuePanel defaultDatasetId={mode?.dataset_id ?? null} onShow={show} />
        <aside aria-label="Investigation" className="flex min-h-0 flex-col gap-3 lg:overflow-y-auto">
          {problem && (
            <p role="alert" className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300">
              {problem}
            </p>
          )}
          {shown && <DatasetCapabilities manifest={shown.manifest} sectionId={shown.sectionId} open={investigation === null} />}
          {investigation ? (
            <>
              <div className="text-xs text-ink-3">
                <span className="font-mono">{investigation.investigationId}</span> · {investigation.status.replaceAll("_", " ")}
                <p className="mt-1 text-sm text-ink-2">{investigation.question}</p>
              </div>
              {investigation.error && (
                <p role="alert" className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300">
                  {investigation.error}
                </p>
              )}
              {investigation.plan && (
                <PlanCard plan={investigation.plan} status={investigation.status} approving={approving} onApprove={approve} />
              )}
              <EventLog events={investigation.events} />
              {investigation.claims.map((claim) => (
                <ClaimCard key={claim.claim_id} claim={claim} />
              ))}
              <ExportButton pkg={investigation.pkg} />
            </>
          ) : (
            <p className="rounded-lg border border-line bg-panel p-4 text-sm text-ink-2">
              Ask a question to start an investigation. Its plan appears here for your approval before anything runs.
            </p>
          )}
        </aside>
      </main>
    </div>
  );
}
