// Typed client for the SpatialScout HTTP/SSE API. Types come from the generated contracts.
import type {
  DatasetManifest,
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

export const api = {
  mode: () => fetch("/api/mode").then(json<ModeInfo>),
  dataset: (datasetId: string) => fetch(`/api/datasets/${encodeURIComponent(datasetId)}`).then(json<DatasetManifest>),
  regionView: (sectionId: string) =>
    fetch(`/api/sections/${encodeURIComponent(sectionId)}/region-view`).then(json<RegionView>),
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

  /** Stream events with seq > afterSeq. EventSource reconnects by itself, sending Last-Event-ID. */
  subscribe(investigationId: string, afterSeq: number, onEvent: (event: InvestigationEvent) => void): () => void {
    const source = new EventSource(`/api/investigations/${investigationId}/events?after_seq=${afterSeq}`);
    source.onmessage = (message: MessageEvent<string>) => {
      const event = JSON.parse(message.data) as InvestigationEvent;
      onEvent(event);
      if (TERMINAL_EVENTS.has(event.type)) source.close();
    };
    return () => source.close();
  },
};
