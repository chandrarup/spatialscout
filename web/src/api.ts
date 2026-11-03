// Typed client for the SpatialScout HTTP/SSE API. Types come from the generated contracts.
import type {
  CapabilityReport,
  DatasetManifest,
  LabelRuleSet,
  PackedRegionView,
  InvestigationEvent,
  InvestigationSnapshot,
  ModeInfo,
  RegionView,
  StartInvestigationRequest,
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
  investigation: (investigationId: string) =>
    fetch(`/api/investigations/${investigationId}`).then(json<InvestigationSnapshot>),
  start: (body: StartInvestigationRequest) =>
    fetch("/api/investigations", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    }).then(json<InvestigationSnapshot>),
  approve: (investigationId: string) =>
    fetch(`/api/investigations/${investigationId}/approve`, { method: "POST" }).then(json<InvestigationSnapshot>),

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
