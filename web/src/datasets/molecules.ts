// The molecule dataset adapter (GSE286184 and the synthetic fixture): each channel is rendered from the section's
// molecules (nuclei from its cells), drawn as points blended additively on black, so a channel's brightness
// follows molecule density. Nothing here is a microscope image, and every pane says so.
import { type Layer } from "@deck.gl/core";
import { ScatterplotLayer } from "@deck.gl/layers";
import { api } from "../api";
import type { ChannelSet, DatasetManifest } from "../contracts/generated";
import { decodeSection } from "../packed";
import { CHANNEL_COLOURS, OTHER_CHANNEL, rgbOf } from "../palette";
import type { ChannelChoice, DatasetAdapter, GateQuery, LoadedSection, SectionChoice } from "./adapter";

/** luma.gl v9 additive blending: each channel adds its light, as overlapping fluorophores do. */
export const ADDITIVE = {
  blend: true,
  blendColorOperation: "add",
  blendColorSrcFactor: "src-alpha",
  blendColorDstFactor: "one",
  blendAlphaOperation: "add",
  blendAlphaSrcFactor: "one",
  blendAlphaDstFactor: "one",
  depthWriteEnabled: false,
  depthCompare: "always",
} as const;

/**
 * Exposure: a channel's point opacity at REFERENCE_UM_PER_PX, scaled by (reference / µm per pixel)², so stacked
 * points neither saturate at overview nor vanish when zoomed in. It depends only on the channel and the zoom, never
 * on a section's own counts, so the same channel is exposed identically on both panes and brightness stays comparable.
 */
const BASE_OPACITY: Record<string, number> = { nuclei: 0.25, umod: 0.06, lrp2_cubn: 0.16 }; // UMOD is dense: kept dim so stacked orange does not read as the yellow reserved for excluded molecules
const DEFAULT_OPACITY = 0.9;
const REFERENCE_UM_PER_PX = 6;
const MIN_OPACITY = 0.025;
const MAX_OPACITY = 0.95;
const MOLECULE_RADIUS_UM = 0.4;
const NUCLEI_MAX_OPACITY = 0.45; // nuclei stay a dim counterstain under the marker channels

function exposure(channelId: string, gain: number, zoom: number): number {
  const base = BASE_OPACITY[channelId];
  // Sparse markers (NPHS1, lymphocyte genes, POSTN) rarely stack, so they keep one opacity at every zoom.
  if (base === undefined) return Math.min(MAX_OPACITY, DEFAULT_OPACITY * gain);
  const umPerPx = 2 ** -zoom;
  const ceiling = channelId === "nuclei" ? NUCLEI_MAX_OPACITY : MAX_OPACITY;
  return Math.min(ceiling, Math.max(MIN_OPACITY, base * gain * (REFERENCE_UM_PER_PX / umPerPx) ** 2));
}

const GENE_SETS = [
  { label: "LRP2/CUBN", genes: ["LRP2", "CUBN"] },
  { label: "NPHS1", genes: ["NPHS1"] },
  { label: "UMOD", genes: ["UMOD"] },
  { label: "CD3D/CD8A/MS4A1", genes: ["CD3D", "CD8A", "MS4A1"] },
  { label: "POSTN", genes: ["POSTN"] },
];

interface ChannelData {
  id: string;
  radii: Float32Array | null;
  /** deck.gl binary data, built once. */
  data: { length: number; attributes: Record<string, { value: Float32Array; size: number }> };
}

function binary(id: string, length: number, positions: Float32Array, radii: Float32Array | null): ChannelData {
  const attributes: ChannelData["data"]["attributes"] = { getPosition: { value: positions, size: 2 } };
  if (radii) attributes.getRadius = { value: radii, size: 1 };
  return { id, radii, data: { length, attributes } };
}

export function moleculeAdapter(manifest: DatasetManifest): DatasetAdapter {
  const datasetId = manifest.dataset_id;
  const synthetic = manifest.synthetic;
  return {
    datasetId,
    label: synthetic ? `${datasetId} (synthetic)` : datasetId,
    sections: async () =>
      manifest.sections.map(
        (s): SectionChoice => ({
          sectionId: s.section_id,
          name: s.name,
          group: s.group,
          detail: s.molecules !== null ? `${s.molecules.toLocaleString()} molecules` : undefined,
          duplicateOf: s.duplicate_of,
        }),
      ),
    defaultPair: (sections) => {
      // Control x2 vs DKD x3 on GSE286184 (revision 3); otherwise the first control and the first other section.
      const byName = (name: string) => sections.find((s) => s.name === name)?.sectionId;
      const control = byName("x2") ?? sections.find((s) => s.group.toLowerCase() === "control")?.sectionId ?? sections[0]?.sectionId;
      const diseased =
        (byName("x2") ? byName("x3") : undefined) ??
        sections.find((s) => s.sectionId !== control && s.group.toLowerCase() !== "control")?.sectionId ??
        sections.find((s) => s.sectionId !== control)?.sectionId ??
        control;
      return [control ?? "", diseased ?? ""];
    },
    load: (sectionId) => loadSection(sectionId, synthetic),
    geneSets: GENE_SETS,
    defaultGateQuery: { cellType: "Podocyte", genes: ["LRP2", "CUBN"] },
    gateStatus: (sectionId: string, query: GateQuery, box, signal) => api.gateStatus(sectionId, query.cellType, query.genes, box, signal),
    sam: {
      maxBoxSideUm: 768, // the SAM route's crop (1024 px at 1 µm) less a 128 µm margin each side
      recordedBoxes: (sectionId) => api.samBoxes(sectionId).then((r) => r.boxes),
      outline: (sectionId, box) => api.samOutline(sectionId, box),
    },
  };
}

async function loadSection(sectionId: string, synthetic: boolean): Promise<LoadedSection> {
  const [view, channelSet] = await Promise.all([api.packedRegionView(sectionId), api.channels(sectionId)]);
  const section = decodeSection(view);
  const data = channelData(channelSet, section);
  const channels = channelSet.channels.map(
    (c): ChannelChoice => ({
      id: c.channel_id,
      label: c.label,
      colour: CHANNEL_COLOURS[c.channel_id] ?? OTHER_CHANNEL,
      description: c.description,
      available: c.available,
      note: c.unavailable_reason ?? (c.missing_genes.length ? `No ${c.missing_genes.join(", ")} molecule in this section.` : null),
      amount: c.source === "nuclei" ? `${c.count.toLocaleString()} nuclei` : `${c.count.toLocaleString()} molecules`,
    }),
  );
  const group = view.group ?? "";
  const name = view.section_name ? `${group ? `${group} section ` : "Section "}${view.section_name}` : `Section ${view.section_id}`;
  return {
    datasetId: view.dataset_id,
    sectionId: view.section_id,
    title: `${name} · ${view.section_id}`,
    group,
    extent: view.region,
    channels,
    provenance: synthetic ? "Rendered from molecules · synthetic section" : "Rendered from molecules",
    provenanceDetail: "Marker channels: every molecule of the channel's genes, assigned or not. Nuclei: segmented nuclei drawn as discs of their area.",
    cellTypes: view.cell_types,
    layers: ({ idPrefix, visibleChannels, gain, zoom }): Layer[] =>
      data.map((d) => {
        const colour = rgbOf(CHANNEL_COLOURS[d.id] ?? OTHER_CHANNEL);
        return new ScatterplotLayer({
          id: `${idPrefix}-channel-${d.id}`,
          data: d.data, // the same object every call, so deck.gl keeps the GPU buffers
          visible: visibleChannels.has(d.id),
          getFillColor: [colour[0], colour[1], colour[2], 255],
          ...(d.radii ? {} : { getRadius: MOLECULE_RADIUS_UM }),
          radiusUnits: "common",
          radiusMinPixels: d.radii ? 0.5 : BASE_OPACITY[d.id] === undefined ? 1.4 : 0.7, // sparse markers stay visible as dots
          opacity: exposure(d.id, gain, zoom),
          parameters: ADDITIVE,
          pickable: false,
        });
      }),
  };
}

/** One position buffer per channel, built once per section. */
function channelData(channelSet: ChannelSet, section: ReturnType<typeof decodeSection>): ChannelData[] {
  const genes = section.view.genes;
  return channelSet.channels.map((channel) => {
    if (channel.source === "nuclei") {
      let count = 0;
      for (let i = 0; i < section.cellCount; i++) if ((section.nucleusRadius[i] ?? 0) > 0) count++;
      const positions = new Float32Array(count * 2);
      const radii = new Float32Array(count);
      let n = 0;
      for (let i = 0; i < section.cellCount; i++) {
        const r = section.nucleusRadius[i] ?? 0;
        if (r <= 0) continue;
        positions[2 * n] = section.cellPositions[2 * i] ?? 0;
        positions[2 * n + 1] = section.cellPositions[2 * i + 1] ?? 0;
        radii[n++] = r;
      }
      return binary(channel.channel_id, count, positions, radii);
    }
    const member = genes.map((g) => channel.genes.includes(g));
    let count = 0;
    for (let i = 0; i < section.moleculeCount; i++) if (member[section.geneIndex[i] ?? 0]) count++;
    const positions = new Float32Array(count * 2);
    let n = 0;
    for (let i = 0; i < section.moleculeCount; i++) {
      if (!member[section.geneIndex[i] ?? 0]) continue;
      positions[2 * n] = section.positions[2 * i] ?? 0;
      positions[2 * n + 1] = section.positions[2 * i + 1] ?? 0;
      n++;
    }
    return binary(channel.channel_id, count, positions, null);
  });
}
