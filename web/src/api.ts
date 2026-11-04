// Typed client for the SpatialScout HTTP/SSE API. Types come from the generated contracts.
import type {
  AuditIndex,
  AuditResult,
  CapabilityReport,
  ChannelSet,
  ContrastIndex,
  ContrastResult,
  DatasetManifest,
  GateStatus,
  LabelRuleSet,
  PackedRegionView,
  InvestigationEvent,
  InvestigationSnapshot,
  ModeInfo,
  RecordedBoxes,
  Region,
  RegionView,
  StartInvestigationRequest,
  StructureRun,
  Transcription,
} from "./contracts/generated";

async function json<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}: ${await response.text()}`);
  }
  return (await response.json()) as T;
}

const TERMINAL_EVENTS = new Set<InvestigationEvent["type"]>(["package_ready", "error"]);
const RECONNECT_MIN_MS = 500;
const RECONNECT_MAX_MS = 10_000;

export const api = {
  mode: () => fetch("/api/mode").then(json<ModeInfo>),
  dataset: (datasetId: string) => fetch(`/api/datasets/${encodeURIComponent(datasetId)}`).then(json<DatasetManifest>),
  regionView: (sectionId: string) =>
    fetch(`/api/sections/${encodeURIComponent(sectionId)}/region-view`).then(json<RegionView>),
  datasets: () => fetch("/api/datasets").then(json<DatasetManifest[]>),
  capabilityReport: (datasetId: string) =>
    fetch(`/api/datasets/${encodeURIComponent(datasetId)}/capability-report`).then(json<CapabilityReport>),
  labelRules: (datasetId: string) =>
    fetch(`/api/datasets/${encodeURIComponent(datasetId)}/label-rules`).then(json<LabelRuleSet>),
  packedRegionView: (sectionId: string, labelRuleId?: string) =>
    fetch(
      `/api/sections/${encodeURIComponent(sectionId)}/region-view/packed` +
        (labelRuleId ? `?label_rule_id=${encodeURIComponent(labelRuleId)}` : ""),
    ).then(json<PackedRegionView>),
  auditResults: (datasetId: string) =>
    fetch(`/api/datasets/${encodeURIComponent(datasetId)}/audit-results`).then(json<AuditIndex>),
  auditResult: (datasetId: string, findingId: string) =>
    fetch(`/api/datasets/${encodeURIComponent(datasetId)}/audit-results/${encodeURIComponent(findingId)}`).then(json<AuditResult>),
  auditFigureUrl: (datasetId: string, findingId: string) =>
    `/api/datasets/${encodeURIComponent(datasetId)}/audit-results/${encodeURIComponent(findingId)}/figure.png`,
  contrastResults: (datasetId: string) =>
    fetch(`/api/datasets/${encodeURIComponent(datasetId)}/contrast-results`).then(json<ContrastIndex>),
  contrastResult: (datasetId: string, findingId: string) =>
    fetch(`/api/datasets/${encodeURIComponent(datasetId)}/contrast-results/${encodeURIComponent(findingId)}`).then(json<ContrastResult>),
  contrastFigureUrl: (datasetId: string, findingId: string) =>
    `/api/datasets/${encodeURIComponent(datasetId)}/contrast-results/${encodeURIComponent(findingId)}/figure.png`,
  investigation: (investigationId: string) =>
    fetch(`/api/investigations/${investigationId}`).then(json<InvestigationSnapshot>),
  start: (body: StartInvestigationRequest) =>
    fetch("/api/investigations", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    }).then(json<InvestigationSnapshot>),
  /** Transcribe a spoken question. Errors carry the server's message, which says to type instead. */
  transcribe: async (wav: Blob): Promise<Transcription> => {
    let response: Response;
    try {
      response = await fetch("/api/voice/transcribe", { method: "POST", headers: { "content-type": "audio/wav" }, body: wav });
    } catch {
      throw new Error("The server could not be reached to transcribe the recording. Type your question instead.");
    }
    if (response.ok) return (await response.json()) as Transcription;
    const detail = await response
      .json()
      .then((body: { detail?: { message?: string } }) => body.detail?.message)
      .catch(() => undefined);
    throw new Error(detail ?? `Transcription failed (HTTP ${response.status}). Type your question instead.`);
  },
  sampleClip: () =>
    fetch("/api/voice/sample.wav").then((response) => {
      if (!response.ok) throw new Error("This server has no recorded clip.");
      return response.blob();
    }),
  channels: (sectionId: string) => fetch(`/api/sections/${encodeURIComponent(sectionId)}/channels`).then(json<ChannelSet>),
  /** Population cells and their molecules of `genes` in a box (the whole section without one), against the frozen gates. */
  gateStatus: (sectionId: string, cellType: string, genes: string[], box: Region | null, signal?: AbortSignal) => {
    const query = new URLSearchParams({ cell_type: cellType });
    for (const gene of genes) query.append("genes", gene);
    if (box) for (const key of ["x0", "y0", "x1", "y1"] as const) query.set(key, String(box[key]));
    return fetch(`/api/sections/${encodeURIComponent(sectionId)}/gate-status?${query}`, { signal }).then(json<GateStatus>);
  },
  samBoxes: (sectionId: string) => fetch(`/api/sections/${encodeURIComponent(sectionId)}/sam-boxes`).then(json<RecordedBoxes>),
  /** SAM 3.1 on a drawn box. Errors carry the server's message (for example: no stored response for this box). */
  samOutline: async (sectionId: string, box: Region): Promise<StructureRun> => {
    const response = await fetch(`/api/sections/${encodeURIComponent(sectionId)}/sam-outline`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(box),
    });
    if (response.ok) return (await response.json()) as StructureRun;
    const detail = await response
      .json()
      .then((body: { detail?: { message?: string } | string }) => (typeof body.detail === "string" ? body.detail : body.detail?.message))
      .catch(() => undefined);
    throw new Error(detail ?? `SAM 3.1 failed (HTTP ${response.status}).`);
  },
  approve: (investigationId: string) =>
    fetch(`/api/investigations/${investigationId}/approve`, { method: "POST" }).then(json<InvestigationSnapshot>),
  reject: (investigationId: string) =>
    fetch(`/api/investigations/${investigationId}/reject`, { method: "POST" }).then(json<InvestigationSnapshot>),

  /**
   * Stream events with seq > afterSeq until a terminal event. The server ends each connection after a bounded
   * window (so a host's request limit, such as Modal's 150 s, never cuts one), and on any close or error this
   * reopens the stream with `after_seq` set to the last event seen, so nothing is lost or repeated. Retries back
   * off while the server is unreachable (for example during a redeploy) and reset once a connection opens.
   */
  subscribe(investigationId: string, afterSeq: number, onEvent: (event: InvestigationEvent) => void): () => void {
    let lastSeq = afterSeq;
    let source: EventSource | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let delayMs = RECONNECT_MIN_MS;
    let stopped = false;

    const stop = () => {
      stopped = true;
      clearTimeout(retryTimer);
      source?.close();
    };
    const connect = () => {
      if (stopped) return;
      source = new EventSource(`/api/investigations/${investigationId}/events?after_seq=${lastSeq}`);
      source.onopen = () => {
        delayMs = RECONNECT_MIN_MS;
      };
      source.onmessage = (message: MessageEvent<string>) => {
        const event = JSON.parse(message.data) as InvestigationEvent;
        if (event.seq <= lastSeq) return;
        lastSeq = event.seq;
        onEvent(event);
        if (TERMINAL_EVENTS.has(event.type)) stop();
      };
      source.onerror = () => {
        source?.close();
        if (stopped) return;
        retryTimer = setTimeout(connect, delayMs);
        delayMs = Math.min(delayMs * 2, RECONNECT_MAX_MS);
      };
    };
    connect();
    return stop;
  },
};
