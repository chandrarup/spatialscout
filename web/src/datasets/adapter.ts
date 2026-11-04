// The dataset adapter: everything the dual-section viewer needs from one dataset, so a second dataset (KPMP CODEX
// images, ticket 02c) plugs into the same viewports without changing them.
//
// Each pane holds exactly one adapter and draws layers only from the section that adapter loaded, so nothing from
// one dataset is ever drawn over another's section. Coordinates are section micrometres throughout, y down.
import type { Layer } from "@deck.gl/core";
import type { GateStatus, ProteinAuditResult, Region, StructureRun } from "../contracts/generated";

/** A section the adapter can open. */
export interface SectionChoice {
  sectionId: string;
  /** Short display name, for example "x2". */
  name: string | null;
  /** The group it belongs to, for example "Control" or "DKD". */
  group: string;
  /** Extra text for the section picker, for example its molecule count. */
  detail?: string;
  /** Another section holding the same data; the picker marks it. */
  duplicateOf?: string | null;
}

/** One toggleable channel of a loaded section. */
export interface ChannelChoice {
  id: string;
  label: string;
  /** Display colour (hex) on the black viewport; channels blend additively. */
  colour: string;
  description: string;
  available: boolean;
  /** Why the channel is unavailable, or a note such as the genes missing from this section. */
  note: string | null;
  /** What the channel draws in this section, for example "47,296 molecules". */
  amount: string;
}

/** A population for the gate readout: a cell type and the genes counted in its cells. */
export interface GateQuery {
  cellType: string;
  genes: string[];
}

export interface LayerOptions {
  /** Prefix for layer ids, unique per pane. */
  idPrefix: string;
  visibleChannels: ReadonlySet<string>;
  /** Multiplies every channel's opacity, 0.25–4. */
  gain: number;
  /** The pane's current zoom (log2 pixels per micrometre), so a renderer can adapt its exposure. */
  zoom: number;
}

/** A section loaded for drawing. Layer data is built once on load; `layers` only sets visibility and opacity. */
export interface LoadedSection {
  datasetId: string;
  sectionId: string;
  /** "Control section x2 · GSM8720410" style title. */
  title: string;
  group: string;
  /** The section's bounds in micrometres. */
  extent: Region;
  channels: ChannelChoice[];
  /** Always shown on the pane, never hideable: what the image is, for example "Rendered from molecules". */
  provenance: string;
  /** One line under it: where each channel comes from. */
  provenanceDetail: string;
  /** Cell types the gate readout can count; empty when the dataset has none. */
  cellTypes: string[];
  layers(options: LayerOptions): Layer[];
}

export interface SamCapability {
  /** The largest box side, in micrometres, SAM accepts. */
  maxBoxSideUm: number;
  /** Boxes whose response is stored, so they outline without a model call. */
  recordedBoxes(sectionId: string): Promise<Region[]>;
  outline(sectionId: string, box: Region): Promise<StructureRun>;
}

export interface DatasetAdapter {
  datasetId: string;
  /** Short dataset label for the picker. */
  label: string;
  sections(): Promise<SectionChoice[]>;
  /** The [left, right] pair opened first: a control section and a diseased one. */
  defaultPair(sections: SectionChoice[]): [string, string];
  load(sectionId: string): Promise<LoadedSection>;
  /** Gene sets the gate readout can count, by label. */
  geneSets: { label: string; genes: string[] }[];
  defaultGateQuery: GateQuery;
  /** Population and molecule gates for a box (or the whole section); absent when the dataset has no molecules. */
  gateStatus?(sectionId: string, query: GateQuery, box: Region | null, signal?: AbortSignal): Promise<GateStatus>;
  sam?: SamCapability;
  /** Channels hidden when a section of this dataset first opens. */
  defaultHidden?: ReadonlySet<string>;
  /** The protein audit of a box (or the whole image) on an antibody-image dataset. */
  proteinAudit?(sectionId: string, box: Region | null, signal?: AbortSignal): Promise<ProteinAuditResult[]>;
}
