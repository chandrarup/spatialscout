// The research team: the run in five jobs, each read from the events shown so far (seeking playback back restores
// its state) and, for the last job, the lab record. A job lights up only when an event says it ran; nothing here is a
// fixed step list. Model names, cost and latency come from each job's own model-call records; the verdict rule and the
// verifier are code, so they add no model.
import { useEffect, useState } from "react";
import { api } from "../../api";
import type { InvestigationEvent, LabRun, ModelCallRecord } from "../../contracts/generated";

export type TeamTarget = { kind: "finding"; id: string } | { kind: "findings"; section: string } | { kind: "graph" };

interface Job {
  id: string;
  title: string;
  who: string;
  status: "waiting" | "working" | "done";
  lines: string[];
  calls: ModelCallRecord[];
  target: TeamTarget | null;
}

const PURPOSE_JOB: Record<string, string> = {
  plan: "plan",
  follow_up: "check",
  claim_draft: "review",
  claim_redraft: "review",
  visual_check: "review",
};

function readable(model: string): string {
  if (model.includes("wonder")) return "Muse Wonder";
  if (model.includes("spark-open")) return "Muse Spark Open";
  if (model.includes("spark")) return "Muse Spark";
  if (model.includes("sam")) return "SAM 3.1";
  return model;
}

/** Largest number of lab sub-agents running at the same moment, from their recorded start and finish times. */
function peakConcurrency(lab: LabRun): number {
  const edges: [number, number][] = [];
  for (const e of lab.events) {
    if (e.type === "subagent_started") edges.push([Date.parse(e.at_utc), 1]);
    if (e.type === "subagent_finished" || e.type === "subagent_failed") edges.push([Date.parse(e.at_utc), -1]);
  }
  edges.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  let now = 0;
  let peak = 0;
  for (const [, d] of edges) peak = Math.max(peak, (now += d));
  return peak;
}

function jobsOf(events: InvestigationEvent[], lab: LabRun | null): Job[] {
  const calls = events.flatMap((e) => (e.type === "model_call" ? [e.call] : []));
  const callsFor = (job: string) => calls.filter((c) => (PURPOSE_JOB[c.purpose] ?? "") === job);
  const tools = (pick: (tool: string) => boolean) => {
    const started = events.filter((e) => e.type === "tool_started" && pick(e.tool));
    const finished = events.filter((e) => e.type === "tool_finished" && pick(e.tool));
    return { started, finished };
  };
  const plan = events.find((e) => e.type === "plan_proposed");
  const approved = events.some((e) => e.type === "plan_approved");
  const analyse = tools((t) => t === "audit_population" || t.includes("sam") || t.includes("structure"));
  const sam = analyse.started.filter((e) => e.type === "tool_started" && (e.tool.includes("sam") || e.tool.includes("structure"))).length;
  const checks = tools((t) => t !== "audit_population" && !t.includes("sam") && !t.includes("structure"));
  const requests = events.flatMap((e) => (e.type === "agent_decision" ? e.requests : []));
  const rejected = requests.filter((r) => r.status !== "accepted");
  const drafted = events.filter((e) => e.type === "claim_drafted").length;
  const verified = events.filter((e) => e.type === "claim_verified");
  const passed = verified.filter((e) => e.type === "claim_verified" && !e.claim.injected.is_injected && e.verification.verification_status === "verified").length;
  const caught = verified.filter((e) => e.type === "claim_verified" && e.claim.injected.is_injected && e.verification.verification_status === "failed").length;
  const verdict = events.some((e) => e.type === "verdict");
  const firstFinding = analyse.finished.find((e) => e.type === "tool_finished" && e.artifact_id);
  const firstControl = checks.finished.find((e) => e.type === "tool_finished" && e.artifact_id);
  const status = (started: boolean, done: boolean): Job["status"] => (done ? "done" : started ? "working" : "waiting");
  const labCalls = lab ? lab.events.flatMap((e) => (e.type === "model_call" && e.call ? [e.call] : [])) : [];

  return [
    {
      id: "plan",
      title: "Plan",
      who: "decomposes the question and picks supported tools",
      status: status(callsFor("plan").length > 0 || !!plan, approved),
      lines: plan && plan.type === "plan_proposed" ? [`${plan.plan.steps.length} planned steps${approved ? ", approved" : ", awaiting approval"}`] : [],
      calls: callsFor("plan"),
      target: plan ? { kind: "graph" } : null,
    },
    {
      id: "analyse",
      title: "Analyse",
      who: "the analysis engine re-counts molecules under each assignment rule (code)",
      status: status(analyse.started.length > 0, analyse.started.length > 0 && analyse.finished.length >= analyse.started.length),
      lines: [
        `${analyse.finished.length} of ${analyse.started.length} population audit${analyse.started.length === 1 ? "" : "s"} finished`,
        sam > 0 ? `${sam} SAM 3.1 outline request${sam === 1 ? "" : "s"} (exploratory)` : "No SAM 3.1 call in this run",
      ].filter(() => analyse.started.length > 0),
      calls: [],
      target: firstFinding && firstFinding.type === "tool_finished" && firstFinding.artifact_id ? { kind: "finding", id: firstFinding.artifact_id } : null,
    },
    {
      id: "check",
      title: "Check alternatives",
      who: "reads each result and requests controls that could explain it away",
      status: status(callsFor("check").length > 0 || checks.started.length > 0, drafted > 0),
      lines: [
        ...(checks.started.length ? [`${checks.finished.length} control${checks.finished.length === 1 ? "" : "s"} run (random thinning, second labelling rule)`] : []),
        ...(rejected.length ? [`${rejected.length} request${rejected.length === 1 ? "" : "s"} rejected by the registry check, not run`] : []),
      ],
      calls: callsFor("check"),
      target: firstControl && firstControl.type === "tool_finished" && firstControl.artifact_id ? { kind: "finding", id: firstControl.artifact_id } : null,
    },
    {
      id: "review",
      title: "Review evidence",
      who: "drafts claims; code recomputes every number and the model reads each figure",
      status: status(drafted > 0 || callsFor("review").length > 0, verdict),
      lines: [
        ...(drafted ? [`${drafted} claim${drafted === 1 ? "" : "s"} drafted`] : []),
        ...(verified.length ? [`${passed} verified · ${caught} deliberately wrong copy caught`] : []),
      ],
      calls: callsFor("review"),
      target: verified.length ? { kind: "findings", section: "Checked claims" } : null,
    },
    {
      id: "assemble",
      title: "Assemble next steps",
      who: "lab sub-agents: protein cross-check, literature, figures, report",
      status: lab ? "done" : "waiting",
      lines: lab
        ? [
            `${lab.tasks.length} tasks dispatched; up to ${peakConcurrency(lab)} ran at once`,
            `${lab.protein.length} protein check${lab.protein.length === 1 ? "" : "s"} · ${lab.literature.reduce((n, l) => n + l.records.length, 0)} papers read · ${lab.figures.length} figure${lab.figures.length === 1 ? "" : "s"}`,
          ]
        : verdict
          ? ["Not run yet for this investigation: open the findings and run the lab"]
          : [],
      calls: labCalls,
      target: verdict ? { kind: "findings", section: "Lab" } : null,
    },
  ];
}

const DOT: Record<Job["status"], string> = { waiting: "bg-[#3a3d42]", working: "animate-pulse bg-stable", done: "bg-stable" };

export function ResearchTeam({ events, investigationId, complete, onOpen }: { events: InvestigationEvent[]; investigationId: string; complete: boolean; onOpen: (target: TeamTarget) => void }) {
  const [lab, setLab] = useState<LabRun | null>(null);
  useEffect(() => {
    if (!complete) return;
    let live = true;
    api
      .lab(investigationId)
      .then((l) => live && setLab(l))
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, [investigationId, complete]);
  const jobs = jobsOf(events, lab);
  return (
    <ol aria-label="Research team" className="flex h-full flex-col gap-2 overflow-y-auto px-4 pb-4">
      {jobs.map((job, i) => {
        const models = [...new Set(job.calls.map((c) => readable(c.model)))];
        const cost = job.calls.reduce((s, c) => s + (c.estimated_cost_usd ?? 0), 0);
        const latency = job.calls.reduce((s, c) => s + c.latency_ms, 0);
        return (
          <li key={job.id} data-testid="team-job" data-status={job.status}>
            <button
              type="button"
              disabled={!job.target}
              onClick={() => job.target && onOpen(job.target)}
              className="flex w-full gap-3 rounded-2xl bg-raised/70 px-3.5 py-3 text-left transition-colors enabled:hover:bg-[#2a2d32] disabled:cursor-default"
            >
              <span className="mt-1 flex flex-col items-center gap-1">
                <span className={`h-2.5 w-2.5 rounded-full ${DOT[job.status]}`} aria-hidden="true" />
                {i < jobs.length - 1 && <span className="w-px flex-1 bg-line" aria-hidden="true" />}
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-baseline justify-between gap-2">
                  <span className="text-[14px] font-semibold">
                    {i + 1} · {job.title}
                  </span>
                  <span className="text-[11px] text-ink-3">{job.status}</span>
                </span>
                <span className="block text-[12px] text-ink-3">{job.who}</span>
                {job.lines.map((l) => (
                  <span key={l} className="mt-0.5 block text-[12px] text-ink-2">
                    {l}
                  </span>
                ))}
                {job.calls.length > 0 && (
                  <span className="mt-1 block text-[11px] text-ink-3">
                    {models.join(" · ")} · {job.calls.length} call{job.calls.length === 1 ? "" : "s"} · {(latency / 1000).toFixed(1)} s · ${cost.toFixed(3)}
                  </span>
                )}
                {job.calls.length === 0 && job.status !== "waiting" && <span className="mt-1 block text-[11px] text-ink-3">no model call</span>}
              </span>
            </button>
          </li>
        );
      })}
      <li className="px-1 text-[11px] leading-relaxed text-ink-3">
        Read from the recorded events shown so far. The audit runs in order (each control cites an earlier result); only the lab's sub-agents run in parallel.
      </li>
    </ol>
  );
}
