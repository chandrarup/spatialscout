// SpatialScout workspace: question bar, tissue viewer, capability report, plan, events, claims and export.
// The open investigation's id lives in the URL hash, so a refresh reconnects with after_seq and loses nothing.
import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { api } from "./api";
import { ClaimCard } from "./components/ClaimCard";
import { DatasetCapabilities } from "./components/DatasetPanel";
import { DualViewer, type RegionPair } from "./components/DualViewer";
import { EventLog } from "./components/EventLog";
import { ExportButton } from "./components/ExportButton";
import { FindingsPanel } from "./components/FindingsPanel";
import { PlanCard } from "./components/PlanCard";
import { ReasoningTimeline } from "./components/ReasoningTimeline";
import { QuestionBar } from "./components/QuestionBar";
import { RunModeBanner } from "./components/RunModeBanner";
import { TelemetryPills } from "./components/TelemetryPills";
import { VerdictBanner } from "./components/VerdictBanner";
import { type TissueFocus, TissuePanel } from "./components/TissuePanel";
import type { DatasetManifest, InvestigationEvent, InvestigationSnapshot, KpmpManifest, ModeInfo, Region } from "./contracts/generated";
import type { DatasetAdapter } from "./datasets/adapter";
import { kpmpAdapter } from "./datasets/kpmp";
import { moleculeAdapter } from "./datasets/molecules";
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
  const [focus, setFocus] = useState<TissueFocus | null>(null);
  const flyTo = useCallback((next: Omit<TissueFocus, "key">) => setFocus((f) => ({ ...next, key: (f?.key ?? 0) + 1 })), []);
  const [approving, setApproving] = useState(false);
  const [workspace, setWorkspace] = useState<"dual" | "single">("dual");
  const [manifests, setManifests] = useState<DatasetManifest[]>([]);
  const [kpmp, setKpmp] = useState<KpmpManifest | null | undefined>(undefined); // undefined while loading
  const adapters = useMemo<DatasetAdapter[]>(() => [...(kpmp ? [kpmpAdapter(kpmp)] : []), ...manifests.map(moleculeAdapter)], [kpmp, manifests]);
  const [regionPair, setRegionPair] = useState<RegionPair | null>(null);
  const [contextRegions, setContextRegions] = useState<Region[]>([]);
  const [dualShown, setDualShown] = useState<string | null>(null);
  const showFromDual = useCallback(
    (datasetId: string, sectionId: string) => {
      setDualShown(`${datasetId} · ${datasetId === kpmp?.dataset_id ? "participant" : "section"} ${sectionId}`);
      const manifest = manifests.find((m) => m.dataset_id === datasetId);
      if (manifest) setShown({ manifest, sectionId });
    },
    [manifests, kpmp],
  );
  const focusFinding = useCallback(
    (next: Omit<TissueFocus, "key">) => {
      setWorkspace("single");
      flyTo(next);
    },
    [flyTo],
  );
  const [problem, setProblem] = useState<string | null>(null);
  const unsubscribe = useRef<(() => void) | null>(null);

  const follow = useCallback((snapshot: InvestigationSnapshot) => {
    unsubscribe.current?.();
    const view = fromSnapshot(snapshot);
    dispatch({ type: "open", view });
    setContextRegions(snapshot.regions ?? []);
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
      .catch((error: unknown) => setProblem(String(error)));
    api
      .kpmp()
      .then(setKpmp)
      .catch(() => setKpmp(null));
    const id = window.location.hash.slice(1);
    if (INVESTIGATION_ID.test(id)) api.investigation(id).then(follow).catch(() => window.history.replaceState(null, "", " "));
    return () => unsubscribe.current?.();
  }, [follow]);

  // The region pair goes with a question only when it lies on the dataset the question will run on (a recorded
  // question runs on its recording's dataset); the server refuses regions on any other dataset.
  // A recorded question runs on its recording's dataset (the server's default when the recording names none);
  // any other question on the open section's dataset.
  const runsOn = (question: string): string | null => {
    const recording = mode?.recordings.find((r) => r.question.trim().toLowerCase() === question.trim().toLowerCase());
    if (recording) return recording.dataset_id ?? mode?.dataset_id ?? null;
    return shown?.manifest.dataset_id ?? mode?.dataset_id ?? null;
  };
  const regionsFor = (question: string): [] | [Region] | [Region, Region] =>
    regionPair && regionPair.datasetIds.length === 1 && regionPair.datasetIds[0] === runsOn(question) ? (regionPair.regions.slice(0, 2) as [Region] | [Region, Region]) : [];

  const ask = (question: string) => {
    setProblem(null);
    api
      .start({
        question,
        run_mode: mode?.default_run_mode ?? "cached_tool_rerun",
        dataset_id: runsOn(question),
        regions: regionsFor(question),
      })
      .then(follow)
      .catch((error: unknown) => setProblem(String(error)));
  };

  // Approve or reject the plan; both are idempotent on the server, so a double click changes nothing.
  const decide = (call: (investigationId: string) => Promise<InvestigationSnapshot>) => {
    if (!investigation) return;
    setApproving(true);
    call(investigation.investigationId)
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
            {workspace === "dual" && dualShown ? dualShown : shown ? `${shown.manifest.dataset_id} · section ${shown.sectionId}` : "loading section…"}
          </p>
        </div>
        <div className="min-w-0 flex-1">
          <QuestionBar examples={mode?.recordings.map((r) => r.question) ?? []} busy={busy} onAsk={ask} />
        </div>
      </header>
      <main className="grid min-h-0 flex-1 grid-cols-1 gap-3 overflow-y-auto p-3 lg:grid-cols-[minmax(0,1fr)_26rem] lg:overflow-hidden">
        <div className="flex min-h-[36rem] flex-col gap-2 lg:min-h-0">
          <div role="tablist" aria-label="Workspace" className="flex items-center gap-1 text-xs">
            {(
              [
                ["dual", "Healthy vs diseased biopsies"],
                ["single", "One section · molecules and conditions"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                role="tab"
                type="button"
                aria-selected={workspace === id}
                onClick={() => setWorkspace(id)}
                className={`rounded-t-md border-b-2 px-3 py-1.5 ${
                  workspace === id ? "border-accent text-ink" : "border-transparent text-ink-3 hover:text-ink-2"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="flex min-h-0 flex-1 flex-col *:flex-1">
            {workspace === "dual" ? (
              adapters.length > 0 && kpmp !== undefined && (
                <DualViewer
                  adapters={adapters}
                  defaultDatasetId={kpmp ? kpmp.dataset_id : manifests.some((m) => m.dataset_id === "GSE286184") ? "GSE286184" : (mode?.dataset_id ?? null)}
                  onShow={showFromDual}
                  onContext={setRegionPair}
                />
              )
            ) : (
              <TissuePanel defaultDatasetId={mode?.dataset_id ?? null} onShow={show} focus={focus} />
            )}
          </div>
        </div>
        <aside aria-label="Investigation" className="flex min-h-0 flex-col gap-3 lg:overflow-y-auto">
          {problem && (
            <p role="alert" className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300">
              {problem}
            </p>
          )}
          {shown && <DatasetCapabilities manifest={shown.manifest} sectionId={shown.sectionId} open={investigation === null} />}
          {regionPair && !investigation && (
            <p className="rounded-lg border border-line bg-panel px-3 py-2 text-xs text-ink-2">
              The region pair ({regionPair.regions.length} box{regionPair.regions.length === 1 ? "" : "es"}) goes with your next question on{" "}
              {regionPair.datasetIds.join(", ")} as context.
            </p>
          )}
          <FindingsPanel datasetId="GSE286184" onFocus={focusFinding} />
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
              {contextRegions.length > 0 && (
                <div className="rounded-lg border border-line bg-panel px-3 py-2 text-xs text-ink-2">
                  <p className="font-semibold text-ink">Region pair kept as context</p>
                  {contextRegions.map((r) => (
                    <p key={`${r.section_id}${r.x0}${r.y0}`} className="font-mono text-[11px]">
                      {r.section_id}: {Math.round(r.x0)}–{Math.round(r.x1)} × {Math.round(r.y0)}–{Math.round(r.y1)} µm
                    </p>
                  ))}
                  <p className="mt-1 text-[11px] text-ink-3">Visual evidence beside cohort-level verdicts; it does not scope the analysis.</p>
                </div>
              )}
              {investigation.verdict && (
                <VerdictBanner
                  verdict={investigation.verdict}
                  onClaim={(id) => document.getElementById(`claim-${id}`)?.scrollIntoView({ behavior: "smooth", block: "center" })}
                />
              )}
              <PlanCard
                plan={investigation.plan}
                events={investigation.events}
                status={investigation.status}
                busy={approving}
                onApprove={() => decide(api.approve)}
                onReject={() => decide(api.reject)}
              />
              <ReasoningTimeline events={investigation.events} />
              {investigation.claims.some((claim) => investigation.verifications[claim.claim_id]) && (
                <section aria-label="Validated summary" className="rounded-lg border border-line bg-panel p-4 text-sm">
                  <h2 className="mb-2 text-sm font-semibold text-ink">Validated summary</h2>
                  {investigation.claims.filter((claim) => investigation.verifications[claim.claim_id]?.in_validated_summary).length === 0 ? (
                    <p className="text-xs text-ink-3">No claim passed its structural and numerical checks; every claim stays in the history below.</p>
                  ) : (
                    <ul className="list-disc space-y-1 pl-4 text-ink">
                      {investigation.claims
                        .filter((claim) => investigation.verifications[claim.claim_id]?.in_validated_summary)
                        .map((claim) => (
                          <li key={claim.claim_id}>
                            {claim.text} <span className="text-xs text-ink-3">({claim.verification_status.replaceAll("_", " ")})</span>
                          </li>
                        ))}
                    </ul>
                  )}
                </section>
              )}
              {investigation.claims.map((claim) => (
                <ClaimCard
                  key={claim.claim_id}
                  claim={claim}
                  verification={investigation.verifications[claim.claim_id]}
                  investigationId={investigation.investigationId}
                />
              ))}
              {investigation.injected.map(({ claim, verification }) => (
                <ClaimCard key={claim.claim_id} claim={claim} verification={verification} />
              ))}
              {investigation.events.map(
                (event) =>
                  event.type === "claim_rejected" && (
                    <p key={event.seq} className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-xs text-red-300">
                      No claim on finding <span className="font-mono">{event.finding_id}</span>: its draft failed the check
                      twice ({event.problems.join("; ")}).
                    </p>
                  ),
              )}
              <ExportButton pkg={investigation.pkg} />
              <TelemetryPills events={investigation.events} />
              <EventLog events={investigation.events} />
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
