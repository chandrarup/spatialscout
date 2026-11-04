// One KPMP participant's CODEX image across the whole screen, on its side. The left rail says what the tissue is,
// switches biopsy, toggles proteins and the marker-positive cells; a click on a cell or a drawn box opens a selection
// card with the computed protein audit of that area and a way to ask SpatialScout about it.
import { ScatterplotLayer } from "@deck.gl/layers";
import { useEffect, useMemo, useState } from "react";
import { api } from "../../api";
import type { KpmpCellMap, KpmpManifest, ProteinAuditResult, Region } from "../../contracts/generated";
import type { DatasetAdapter, LoadedSection } from "../../datasets/adapter";
import { KPMP_COLOURS } from "../../datasets/kpmp";
import type { RegionSelection } from "../../selection";
import { CodexView } from "./CodexView";
import { labelTone } from "./RunCanvas";

const CONDITION_LABELS: Record<string, string> = {
  whole_cell: "Whole label",
  eroded_1px: "Eroded 1 px",
  eroded_2px: "Eroded 2 px",
  nucleus_region: "Nucleus region",
};
/** What each audit marker marks, in plain words. */
const MARKER_MEANS: Record<string, string> = {
  Podocalyxin: "glomerulus (podocytes, endothelium)",
  LRP2: "proximal tubule",
  UMOD: "thick ascending limb",
  CD20: "B cells",
};
const AROUND_UM = 60;

export function pct(v: number | null): string {
  return v === null ? "–" : `${(v * 100).toFixed(1)}%`;
}

function rgb(hex: string): [number, number, number] {
  const n = Number.parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/** What the researcher picked on the image, handed to the assistant. */
export interface TissueContext {
  participantId: string;
  label: string;
  markers: string[];
  /** One sentence read back to the researcher, built only from computed values. */
  summary: string;
  /** The exact region and source the summary was computed on. */
  selection: RegionSelection | null;
  /** Several regions asked about together (for example one box on each of two specimens). */
  selections?: RegionSelection[];
}

type Selection = { kind: "cell"; index: number } | { kind: "box"; region: Region };

interface Props {
  adapter: DatasetAdapter;
  kpmp: KpmpManifest;
  participantId: string;
  onParticipant: (participantId: string) => void;
  onAsk: (context: TissueContext | null) => void;
  onCompare: () => void;
  /** Open with the protein audit expanded. */
  auditFirst?: boolean;
}

/** "healthy reference", or "diseased · AKI" with KPMP's enrollment category when the atlas gave one. */
export function roleLabel(p: { role: string; clinical: Record<string, string> }): string {
  const category = p.clinical["KPMP enrollment category"];
  return p.role === "healthy reference" || !category ? p.role : `${p.role} · ${category}`;
}

export function Explore({ adapter, kpmp, participantId, onParticipant, onAsk, onCompare, auditFirst = false }: Props) {
  const participant = kpmp.participants.find((p) => p.participant_id === participantId) ?? kpmp.participants[0]!;
  const [section, setSection] = useState<LoadedSection | null>(null);
  const [cells, setCells] = useState<KpmpCellMap | null>(null);
  const [visible, setVisible] = useState<Set<string> | null>(null);
  const [cellMarkers, setCellMarkers] = useState<Set<string>>(new Set());
  const [boxMode, setBoxMode] = useState(false);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [auditOpen, setAuditOpen] = useState(auditFirst);
  const [railOpen, setRailOpen] = useState(() => typeof window === "undefined" || window.matchMedia("(min-width: 1024px)").matches);
  const [audit, setAudit] = useState<{ results: ProteinAuditResult[] | null; pending: boolean; problem: string | null }>({ results: null, pending: false, problem: null });

  useEffect(() => {
    let live = true;
    setSection(null);
    setCells(null);
    setSelection(null);
    adapter.load(participant.participant_id).then((s) => {
      if (!live) return;
      setSection(s);
      setVisible((v) => v ?? new Set(s.channels.filter((c) => !adapter.defaultHidden?.has(c.id)).map((c) => c.id)));
    });
    api
      .kpmpCells(participant.participant_id)
      .then((c) => live && setCells(c))
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, [adapter, participant.participant_id]);

  const region: Region | null = useMemo(() => {
    if (!selection) return null;
    if (selection.kind === "box") return selection.region;
    if (!cells) return null;
    const x = cells.x_um[selection.index]!;
    const y = cells.y_um[selection.index]!;
    return { section_id: participant.participant_id, x0: x - AROUND_UM, y0: y - AROUND_UM, x1: x + AROUND_UM, y1: y + AROUND_UM };
  }, [selection, cells, participant.participant_id]);

  useEffect(() => {
    if (!adapter.proteinAudit) return;
    const controller = new AbortController();
    setAudit((a) => ({ ...a, pending: true, problem: null }));
    adapter
      .proteinAudit(participant.participant_id, region, controller.signal)
      .then((results) => setAudit({ results, pending: false, problem: null }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setAudit({ results: null, pending: false, problem: String(error) });
      });
    return () => controller.abort();
  }, [adapter, participant.participant_id, region]);

  const counts = useMemo(() => {
    const out: Record<string, number> = {};
    if (!cells) return out;
    cells.markers.forEach((m, bit) => {
      out[m] = cells.positive.reduce((n, b) => n + ((b >> bit) & 1), 0);
    });
    return out;
  }, [cells]);

  const overlays = useMemo(() => {
    if (!cells || cellMarkers.size === 0) return [];
    const bits = cells.markers.map((m, bit) => (cellMarkers.has(m) ? 1 << bit : 0)).reduce((a, b) => a | b, 0);
    const index = cells.positive.map((b, i) => ((b & bits) !== 0 ? i : -1)).filter((i) => i >= 0);
    const colourOf = (i: number): [number, number, number] => {
      const b = cells.positive[i]!;
      const first = cells.markers.findIndex((m, bit) => cellMarkers.has(m) && ((b >> bit) & 1) === 1);
      return rgb(KPMP_COLOURS[cells.markers[first]!.toLowerCase()] ?? "#ffffff");
    };
    const chosen = selection?.kind === "cell" ? selection.index : -1;
    return [
      new ScatterplotLayer<number>({
        id: "kpmp-cells",
        data: index,
        getPosition: (i) => [cells.x_um[i]!, cells.y_um[i]!],
        getRadius: (i) => (i === chosen ? 7 : 3.2),
        radiusUnits: "pixels",
        stroked: true,
        filled: true,
        getFillColor: (i) => [...colourOf(i), i === chosen ? 255 : 150],
        getLineColor: (i) => (i === chosen ? [255, 255, 255, 255] : [0, 0, 0, 160]),
        lineWidthUnits: "pixels",
        getLineWidth: (i) => (i === chosen ? 2 : 0.5),
        pickable: true,
        updateTriggers: { getRadius: chosen, getFillColor: [chosen, [...cellMarkers].join()], getLineColor: chosen, getLineWidth: chosen },
        onClick: (info) => {
          if (typeof info.object === "number") setSelection({ kind: "cell", index: info.object });
          return true;
        },
      }),
    ];
  }, [cells, cellMarkers, selection]);

  const toggle = (set: Set<string>, id: string): Set<string> => {
    const next = new Set(set);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    return next;
  };

  const selectedMarkers =
    selection?.kind === "cell" && cells ? cells.markers.filter((_, bit) => ((cells.positive[selection.index]! >> bit) & 1) === 1) : [];
  const auditLines = (audit.results ?? []).map((r) => {
    if (r.population_cells === 0) return `no ${r.population}`;
    const whole = r.conditions.find((c) => c.condition === "whole_cell");
    const trimmed = r.conditions.find((c) => c.condition === "eroded_2px");
    return `${pct(whole?.observed_share ?? null)} of ${r.population_cells} ${r.population} are ${r.marker}+, ${pct(trimmed?.observed_share ?? null)} once edges are trimmed (${r.label.replaceAll("_", " ")})`;
  });
  const askContext = (): TissueContext => {
    const around = auditLines.length ? ` Around it: ${auditLines.join("; ")}.` : "";
    const selected: RegionSelection | null = region
      ? {
          datasetId: kpmp.dataset_id,
          sourceId: participant.participant_id,
          assay: "CODEX protein",
          region,
          units: "µm",
          markers: selection?.kind === "cell" ? selectedMarkers : [...cellMarkers],
          pane: "explore",
          scope: selection?.kind === "cell" ? "around a cell" : "box",
        }
      : null;
    if (selection?.kind === "cell" && cells) {
      const i = selection.index;
      const strongest = cells.markers
        .map((m, k) => ({ m, mean: cells.means[i]![k]!, t: cells.thresholds[k]!.value }))
        .filter((x) => x.mean >= x.t)
        .map((x) => `${x.m} ${x.mean.toFixed(0)} against a threshold of ${x.t}`)
        .join(", ");
      return {
        participantId: participant.participant_id,
        label: `cell ${cells.cell_id[i]} (${selectedMarkers.map((m) => `${m}+`).join(" ")})`,
        markers: selectedMarkers,
        summary: `Cell ${cells.cell_id[i]} on ${participant.participant_id} is ${selectedMarkers.map((m) => `${m}+`).join(" ")}: ${strongest}.${around}`,
        selection: selected,
      };
    }
    const markers = [...cellMarkers];
    const size = region ? `${Math.round(region.x1 - region.x0)} × ${Math.round(region.y1 - region.y0)} µm` : "";
    return {
      participantId: participant.participant_id,
      label: `your ${size} box`,
      markers: markers.length ? markers : ["LRP2", "UMOD", "CD20"],
      summary: `Your ${size} box on ${participant.participant_id}.${around}`,
      selection: selected,
    };
  };

  return (
    <div className="relative h-full w-full overflow-hidden">
      <div className={`absolute inset-y-0 right-0 transition-[left] duration-300 ${railOpen ? "left-0 lg:left-[318px]" : "left-0"}`}>
        {section && visible ? (
          <CodexView
            key={section.sectionId}
            section={section}
            visible={visible}
            boxMode={boxMode}
            box={region}
            onBox={(b) => {
              setBoxMode(false);
              setSelection(b ? { kind: "box", region: b } : null);
            }}
            onPick={() => setSelection(null)}
            overlays={overlays}
            fill={2.4}
          />
        ) : (
          <div className="grid h-full place-items-center text-[14px] text-ink-3">Loading the biopsy…</div>
        )}
      </div>

      {/* Left rail: the biopsy, its proteins and its cells. */}
      <aside
        aria-label="Biopsy and layers"
        className={`absolute top-4 bottom-4 left-4 z-10 flex w-[min(290px,calc(100vw-32px))] flex-col gap-3 overflow-y-auto rounded-3xl bg-[#16171b]/95 ring-1 ring-white/[0.06] p-4 backdrop-blur transition-transform duration-300 ${
          railOpen ? "" : "-translate-x-[calc(100%+24px)]"
        }`}
      >
        <div>
          <div className="flex items-start justify-between gap-2">
            <p className="text-[12px] text-ink-3">Human kidney biopsy</p>
            <button type="button" onClick={() => setRailOpen(false)} className="-mt-1 -mr-1 rounded-full px-2 py-1 text-[12px] text-ink-3 hover:bg-raised hover:text-ink" aria-label="Hide the layers">
              Hide
            </button>
          </div>
          <h1 className="text-[20px] leading-tight font-semibold tracking-tight">Participant {participant.participant_id}</h1>
          <p className="mt-1 text-[13px] leading-relaxed text-ink-2">
            <span className={`mr-1.5 rounded-full px-2 py-0.5 text-[12px] font-medium ${participant.role === "healthy reference" ? "bg-[#222a10] text-stable" : "bg-[#2b2414] text-sensitive"}`}>
              {roleLabel(participant)}
            </span>
            CODEX protein imaging, panel {participant.panel_id}, {participant.cells.toLocaleString()} segmented cells. From the KPMP Kidney Tissue Atlas.
          </p>
          <p className="mt-1 text-[12px] text-ink-3">{participant.clinical_note}</p>
        </div>

        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Biopsies">
          {kpmp.participants.map((p) => (
            <button
              key={p.participant_id}
              type="button"
              aria-pressed={p.participant_id === participant.participant_id}
              onClick={() => onParticipant(p.participant_id)}
              className="h-8 rounded-full bg-raised px-3 text-[13px] text-ink-2 hover:text-ink aria-pressed:bg-white aria-pressed:text-black"
            >
              {p.participant_id} · {p.role === "healthy reference" ? "healthy" : (p.clinical["KPMP enrollment category"] ?? "diseased")}
            </button>
          ))}
          <button type="button" onClick={onCompare} className="h-8 rounded-full px-3 text-[13px] text-ink underline decoration-ink-3 underline-offset-4 hover:decoration-white">
            Side by side
          </button>
        </div>

        <section aria-label="Proteins">
          <h2 className="text-[13px] font-semibold">Proteins</h2>
          <ul className="mt-1.5 flex flex-col gap-0.5">
            {section?.channels.map((c) => {
              const on = visible?.has(c.id) ?? false;
              return (
                <li key={c.id}>
                  <button
                    type="button"
                    aria-pressed={on}
                    onClick={() => setVisible((v) => toggle(v ?? new Set(), c.id))}
                    className="flex w-full items-center gap-2.5 rounded-xl px-2 py-1.5 text-left hover:bg-raised"
                  >
                    <span className="h-3 w-3 shrink-0 rounded-full" style={{ background: on ? c.colour : "transparent", boxShadow: `inset 0 0 0 1.5px ${c.colour}` }} />
                    <span className="min-w-0">
                      <span className={`block text-[13px] ${on ? "text-ink" : "text-ink-3"}`}>{c.label}</span>
                      <span className="block truncate text-[12px] text-ink-3">{c.description}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </section>

        <section aria-label="Cells">
          <h2 className="text-[13px] font-semibold">Marker-positive cells</h2>
          <p className="mt-0.5 text-[12px] leading-relaxed text-ink-3">
            Dots on KPMP's segmented cells whose signal passes the frozen threshold. Click one to inspect it.
          </p>
          <ul className="mt-1.5 flex flex-col gap-0.5">
            {(cells?.markers ?? []).map((m) => {
              const on = cellMarkers.has(m);
              const colour = KPMP_COLOURS[m.toLowerCase()] ?? "#fff";
              return (
                <li key={m}>
                  <button
                    type="button"
                    aria-pressed={on}
                    onClick={() => setCellMarkers((s) => toggle(s, m))}
                    className="flex w-full items-center justify-between gap-2 rounded-xl px-2 py-1.5 text-left hover:bg-raised"
                  >
                    <span className="flex items-center gap-2.5">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: on ? colour : "transparent", boxShadow: `inset 0 0 0 1.5px ${colour}` }} />
                      <span className={`text-[13px] ${on ? "text-ink" : "text-ink-3"}`}>
                        {m}+ <span className="text-ink-3">· {MARKER_MEANS[m]}</span>
                      </span>
                    </span>
                    <span className="text-[12px] text-ink-3 tabular-nums">{counts[m]?.toLocaleString() ?? "–"}</span>
                  </button>
                </li>
              );
            })}
            {!cells && <li className="px-2 text-[12px] text-ink-3">Loading cells…</li>}
          </ul>
          {cells && <p className="mt-1 text-[11px] leading-relaxed text-ink-3">{cells.rule}</p>}
        </section>

        <details className="group rounded-2xl bg-raised/60 px-3 py-2 text-[12px] text-ink-2">
          <summary className="cursor-pointer text-[13px] text-ink">More biopsies</summary>
          <p className="mt-1.5 leading-relaxed">
            The KPMP atlas holds CODEX images for more participants. Once one with the same markers is processed into this workspace it joins the list above,
            so a signal missing from this biopsy can be checked on another. This workspace has {kpmp.participants.length}: {kpmp.participants.filter((p) => p.role === "healthy reference").length} healthy
            reference and {kpmp.participants.filter((p) => p.role !== "healthy reference").length} from people with kidney disease (KPMP enrollment: {[...new Set(kpmp.participants.filter((p) => p.role !== "healthy reference").map((p) => p.clinical["KPMP enrollment category"] ?? "diseased"))].join(", ")}).
          </p>
        </details>
      </aside>
      {!railOpen && (
        <button type="button" onClick={() => setRailOpen(true)} className="absolute top-4 left-4 z-10 h-9 rounded-full bg-[#16171b]/95 ring-1 ring-white/[0.06] px-4 text-[13px] text-ink hover:bg-raised">
          Layers · {participant.participant_id}
        </button>
      )}

      {/* Top right: tools and the way forward. */}
      <div className="absolute top-4 right-4 z-10 flex flex-wrap justify-end gap-2">
        <button
          type="button"
          aria-pressed={boxMode}
          onClick={() => setBoxMode((m) => !m)}
          className={`h-9 rounded-full px-4 text-[13px] ${boxMode ? "bg-white text-black" : "bg-[#16171b]/95 ring-1 ring-white/[0.06] text-ink hover:bg-raised"}`}
        >
          {boxMode ? "Drag on the image…" : "Draw a box"}
        </button>
        <button type="button" onClick={onCompare} className="h-9 rounded-full bg-[#16171b]/95 ring-1 ring-white/[0.06] px-4 text-[13px] text-ink hover:bg-raised">
          Compare with the healthy reference
        </button>
      </div>

      {/* The selection: a cell or a box, with what is computed about it. */}
      {selection && (
        <section aria-label="Selection" className="rise absolute top-16 right-4 z-10 w-[min(340px,calc(100vw-32px))] rounded-3xl bg-[#16171b]/95 ring-1 ring-white/[0.06] p-4 backdrop-blur">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-[12px] text-ink-3">{selection.kind === "cell" ? "Selected cell" : "Your box"}</p>
              {selection.kind === "cell" && cells ? (
                <h2 className="text-[16px] font-semibold">
                  Cell {cells.cell_id[selection.index]} · {selectedMarkers.map((m) => `${m}+`).join(" ")}
                </h2>
              ) : (
                region && (
                  <h2 className="text-[16px] font-semibold">
                    {Math.round(region.x1 - region.x0)} × {Math.round(region.y1 - region.y0)} µm
                  </h2>
                )
              )}
            </div>
            <button type="button" onClick={() => setSelection(null)} aria-label="Clear the selection" className="grid h-8 w-8 place-items-center rounded-full text-ink-2 hover:bg-raised hover:text-ink">
              ×
            </button>
          </div>
          {selection.kind === "cell" && cells && (
            <ul className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[12px]">
              {cells.markers.map((m, i) => {
                const mean = cells.means[selection.index]![i]!;
                const threshold = cells.thresholds[i]!.value;
                return (
                  <li key={m} className="flex justify-between">
                    <span className="text-ink-3">{m}</span>
                    <span className={mean >= threshold ? "text-ink" : "text-ink-3"}>
                      {mean.toFixed(0)} <span className="text-ink-3">/ {threshold}</span>
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
          {selection.kind === "cell" && <p className="mt-1.5 text-[11px] text-ink-3">Mean signal in the cell's label / frozen threshold.</p>}
          <div className="mt-3 border-t border-line pt-3">
            <p className="text-[12px] text-ink-3">{selection.kind === "cell" ? `Protein audit, ${AROUND_UM * 2} µm around it` : "Protein audit of your box"}</p>
            {audit.pending && <p className="shimmer-text mt-1 text-[13px]">Computing…</p>}
            <ul className="mt-1 flex flex-col gap-1">
              {!audit.pending &&
                audit.results?.map((r) => {
                  const whole = r.conditions.find((c) => c.condition === "whole_cell");
                  const trimmed = r.conditions.find((c) => c.condition === "eroded_2px");
                  if (r.population_cells === 0)
                    return (
                      <li key={r.result_id} className="text-[13px] text-ink-3">
                        {r.marker} in {r.population}: none here
                      </li>
                    );
                  return (
                    <li key={r.result_id} className="flex items-center justify-between gap-2 text-[13px]">
                      <span className="text-ink-2">
                        {r.marker} in {r.population} <span className="text-ink-3">({r.population_cells})</span>
                      </span>
                      <span className="flex items-center gap-2">
                        <span className="text-ink tabular-nums">
                          {pct(whole?.observed_share ?? null)} → {pct(trimmed?.observed_share ?? null)}
                        </span>
                        <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-medium ${labelTone(r.label)}`}>{r.label.replaceAll("_", " ")}</span>
                      </span>
                    </li>
                  );
                })}
            </ul>
            <button type="button" onClick={() => setAuditOpen(true)} className="mt-1 text-[12px] text-ink-3 underline underline-offset-4 hover:text-ink">
              How to read this
            </button>
          </div>
          <button type="button" onClick={() => onAsk(askContext())} className="mt-3 h-9 w-full rounded-full bg-white px-4 text-[13px] font-medium text-black active:scale-95">
            Ask SpatialScout about this
          </button>
        </section>
      )}

      {/* The protein audit: collapsed to one line until asked for. */}
      <section
        aria-label="Protein audit"
        className="absolute right-4 bottom-24 z-10 w-[min(400px,calc(100vw-32px))] rounded-3xl bg-[#16171b]/95 ring-1 ring-white/[0.06] backdrop-blur"
      >
        <button type="button" aria-expanded={auditOpen} onClick={() => setAuditOpen((o) => !o)} className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left">
          <span>
            <span className="block text-[14px] font-semibold">
              Protein audit · {region ? (selection?.kind === "cell" ? "around the cell" : "your box") : "whole image"}
            </span>
            <span className="block text-[12px] text-ink-3">Does a marker survive when the cell's edge is trimmed away?</span>
          </span>
          <span className="flex items-center gap-2">
            {audit.pending && <span className="h-2 w-2 animate-pulse rounded-full bg-stable" aria-label="computing" />}
            {!auditOpen &&
              audit.results?.map((r) => (
                <span key={r.result_id} className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${labelTone(r.label)}`}>
                  {r.marker}
                </span>
              ))}
            <span className="text-[12px] text-ink-2">{auditOpen ? "Hide" : "Show"}</span>
          </span>
        </button>
        <div className={auditOpen ? "max-h-[46vh] overflow-y-auto px-4 pb-4" : "sr-only"}>
          {audit.problem && <p className="text-[13px] text-bad">{audit.problem}</p>}
          <div className="space-y-3">
            {audit.results?.map((r) => (
              <div key={r.result_id} data-testid="protein-audit-result" data-label={r.label}>
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[13px] text-ink">
                    {r.marker}+ share of {r.population} <span className="text-ink-3">({r.population_cells.toLocaleString()} cells)</span>
                  </p>
                  <span className={`shrink-0 whitespace-nowrap rounded-full px-2.5 py-0.5 text-[12px] font-medium ${labelTone(r.label)}`}>{r.label.replaceAll("_", " ")}</span>
                </div>
                <ul className="mt-1.5 space-y-1">
                  {r.conditions.map((c) => (
                    <li key={c.condition} className="grid grid-cols-[96px_1fr_52px] items-center gap-2 text-[12px]">
                      <span className="text-ink-3">{CONDITION_LABELS[c.condition] ?? c.condition}</span>
                      <span className="relative h-2 rounded-full bg-raised">
                        <span className="absolute inset-y-0 left-0 rounded-full bg-white" style={{ width: `${Math.min(100, (c.observed_share ?? 0) * 100)}%` }} />
                        {c.expected_share !== null && (
                          <span className="absolute -top-0.5 h-3 w-0.5 bg-stable" style={{ left: `${Math.min(100, c.expected_share * 100)}%` }} title={`Random-pixel-loss expectation ${pct(c.expected_share)}`} />
                        )}
                      </span>
                      <span className="text-right text-ink">{pct(c.observed_share)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            {audit.results && audit.results.length > 0 && (
              <p className="text-[12px] leading-relaxed text-ink-3">
                White bar: the share of cells still positive as each cell's outline is trimmed. Green tick: what random pixel loss alone would leave. Far below
                the tick means the signal sat at the edge, where a neighbour's protein bleeds in. {audit.results[0]?.inference}
              </p>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
