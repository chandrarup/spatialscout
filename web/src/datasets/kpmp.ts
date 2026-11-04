// The KPMP CODEX adapter (ticket 02c): real multiplexed antibody images of two participants, one display image per
// channel drawn as tinted strips and blended additively on black. Nothing from GSE286184 is drawn on these panes:
// they are different people and a different assay, and every pane names its dataset and participant.
import { type Layer } from "@deck.gl/core";
import { BitmapLayer } from "@deck.gl/layers";
import { api } from "../api";
import type { KpmpManifest, KpmpParticipant, ProteinAuditResult, Region } from "../contracts/generated";
import { OTHER_CHANNEL, rgbOf } from "../palette";
import type { ChannelChoice, DatasetAdapter, LoadedSection, SectionChoice } from "./adapter";
import { ADDITIVE } from "./molecules";

export const KPMP_COLOURS: Record<string, string> = {
  nuclei: "#4a63ff",
  podocalyxin: "#ff3fd0",
  lrp2: "#2fd36b",
  umod: "#ff8a1f",
  cd20: "#ff2e4f",
  cd3: "#b48cff",
  asma: "#c3c2b7",
};
/** The protein audit's two results: a marker's positive share in a population, as [population, marker]. */
export const PROTEIN_RESULTS: [string, string][] = [
  ["Podocalyxin", "LRP2"],
  ["CD20", "UMOD"],
];
const BASE_OPACITY = 0.9;
const DEFAULT_HIDDEN = new Set(["cd3", "asma"]);

function group(p: KpmpParticipant): string {
  return p.role === "healthy reference" ? "Healthy reference" : "Diseased";
}

export function kpmpAdapter(manifest: KpmpManifest): DatasetAdapter {
  const byId = new Map(manifest.participants.map((p) => [p.participant_id, p]));
  return {
    datasetId: manifest.dataset_id,
    label: "KPMP CODEX",
    sections: async () =>
      manifest.participants.map(
        (p): SectionChoice => ({ sectionId: p.participant_id, name: p.participant_id, group: group(p), detail: `${p.cells.toLocaleString()} cells` }),
      ),
    defaultPair: (sections) => {
      const healthy = sections.find((s) => s.group === "Healthy reference")?.sectionId ?? sections[0]?.sectionId ?? "";
      const diseased = sections.find((s) => s.group === "Diseased")?.sectionId ?? sections[1]?.sectionId ?? healthy;
      return [healthy, diseased];
    },
    load: async (sectionId) => {
      const p = byId.get(sectionId);
      if (!p) throw new Error(`No KPMP participant ${sectionId}.`);
      return loadParticipant(p, manifest);
    },
    geneSets: [],
    defaultGateQuery: { cellType: "", genes: [] },
    defaultHidden: DEFAULT_HIDDEN,
    proteinAudit: (sectionId: string, box: Region | null, signal?: AbortSignal): Promise<ProteinAuditResult[]> =>
      Promise.all(PROTEIN_RESULTS.map(([population, marker]) => api.kpmpProteinAudit(sectionId, population, marker, box, signal))),
  };
}

function loadParticipant(p: KpmpParticipant, manifest: KpmpManifest): LoadedSection {
  const channels = p.channels.map(
    (c): ChannelChoice => ({
      id: c.channel_id,
      label: c.label,
      colour: KPMP_COLOURS[c.channel_id] ?? OTHER_CHANNEL,
      description: c.description,
      available: true,
      note: null,
      amount: `antibody image, white at intensity ${Math.round(c.display_max)}`,
    }),
  );
  const strips = p.channels.flatMap((c) => c.tiles.map((t, n) => ({ channel: c.channel_id, n, url: api.kpmpFileUrl(t.path), bounds: t.bounds })));
  return {
    datasetId: manifest.dataset_id,
    sectionId: p.participant_id,
    title: `${group(p)} · KPMP participant ${p.participant_id} · CODEX panel ${p.panel_id}`,
    group: group(p),
    extent: p.extent,
    channels,
    provenance: `Real CODEX microscopy · KPMP ${p.participant_id}`,
    provenanceDetail: `${manifest.display_rule} ${p.mask_note} ${p.clinical_note}`,
    cellTypes: [],
    layers: ({ idPrefix, visibleChannels, gain }): Layer[] =>
      strips.map((s) => {
        const colour = rgbOf(KPMP_COLOURS[s.channel] ?? OTHER_CHANNEL);
        return new BitmapLayer({
          id: `${idPrefix}-kpmp-${p.participant_id}-${s.channel}-${s.n}`,
          image: s.url,
          bounds: [s.bounds.x0, s.bounds.y1, s.bounds.x1, s.bounds.y0],
          visible: visibleChannels.has(s.channel),
          tintColor: colour,
          opacity: Math.min(1, BASE_OPACITY * gain),
          parameters: ADDITIVE,
          pickable: false,
        });
      }),
  };
}
