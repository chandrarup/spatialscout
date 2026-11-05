// Two KPMP participants one above the other, each on its side, with the same proteins switched on: a healthy reference
// above and a participant with kidney disease below, each picked from the biopsies in the workspace. They are two
// different people, so nothing links a place on one to a place on the other: each pane has its own camera, box and
// computed protein audit. Linked navigation only shares movement and scale, never a position.
import { useEffect, useRef, useState } from "react";
import type { KpmpManifest, ProteinAuditResult, Region } from "../../contracts/generated";
import type { DatasetAdapter, LoadedSection } from "../../datasets/adapter";
import { KPMP_COLOURS } from "../../datasets/kpmp";
import { type RegionSelection, regionSize, sameRegion } from "../../selection";
import { CodexView, type View } from "./CodexView";
import { pct, roleLabel, type TissueContext } from "./Explore";
import { labelTone } from "./RunCanvas";

interface Props {
  adapter: DatasetAdapter;
  kpmp: KpmpManifest;
  onOpen: (participantId: string) => void;
  onBack: () => void;
  /** The earlier side-by-side viewer, which also opens the Xenium sections with SAM 3.1 outlines. */
  onClassic: () => void;
  onAsk: (context: TissueContext) => void;
}

type Participant = KpmpManifest["participants"][number];
type Nudge = { key: number; dx: number; dy: number; dz: number };
/** One pane's box and the one sentence read back about it, built only from its computed audit. */
type PaneSelection = { selection: RegionSelection; text: string };

interface RegionAudit {
  region: Region;
  results: ProteinAuditResult[] | null;
  pending: boolean;
  problem: string | null;
}

function auditLine(r: ProteinAuditResult): string {
  if (r.population_cells === 0) return `${r.marker} in ${r.population}: no ${r.population} cells in the box`;
  const whole = r.conditions.find((c) => c.condition === "whole_cell");
  const trimmed = r.conditions.find((c) => c.condition === "eroded_2px");
  return `${r.marker} in ${r.population} (${r.population_cells} cells): ${pct(whole?.observed_share ?? null)} → ${pct(trimmed?.observed_share ?? null)} edges trimmed`;
}

const TAKEAWAY: Record<string, string> = {
  stable: "holds when cell edges are trimmed",
  segmentation_sensitive: "changes when cell edges are trimmed",
  insufficient_evidence: "too few cells to call",
};

/** One plain sentence per whole-image audit, so the pane's point lands without reading the badges. */
function takeaway(results: ProteinAuditResult[]): string {
  return results.map((r) => `${r.marker} protein in ${r.population} ${TAKEAWAY[r.label] ?? r.label.replaceAll("_", " ")}`).join("; ");
}

function Pane({
  pane,
  adapter,
  kpmp,
  participant,
  choices,
  onChoose,
  visible,
  onOpen,
  onSelected,
  onViewChange,
  nudge,
}: {
  pane: string;
  adapter: DatasetAdapter;
  kpmp: KpmpManifest;
  participant: Participant;
  choices: Participant[];
  onChoose: (id: string) => void;
  visible: ReadonlySet<string>;
  onOpen: () => void;
  onSelected: (selected: PaneSelection | null) => void;
  onViewChange: (from: View, to: View) => void;
  nudge: Nudge | null;
}) {
  const { participant_id: participantId, role, cells } = participant;
  const [section, setSection] = useState<LoadedSection | null>(null);
  const [whole, setWhole] = useState<ProteinAuditResult[] | null>(null);
  const [boxMode, setBoxMode] = useState(false);
  const [box, setBox] = useState<Region | null>(null);
  const [fitKey, setFitKey] = useState(0);
  const [regionAudit, setRegionAudit] = useState<RegionAudit | null>(null);
  const request = useRef<AbortController | null>(null);

  useEffect(() => {
    let live = true;
    adapter
      .load(participantId)
      .then((s) => live && setSection(s))
      .catch(() => live && setSection(null));
    adapter.proteinAudit?.(participantId, null).then((r) => live && setWhole(r)).catch(() => live && setWhole(null));
    return () => {
      live = false;
      request.current?.abort();
    };
  }, [adapter, participantId]);

  const analyse = () => {
    if (!box || !adapter.proteinAudit) return;
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    const region = box;
    setRegionAudit({ region, results: null, pending: true, problem: null });
    adapter
      .proteinAudit(participantId, region, controller.signal)
      .then((results) => !controller.signal.aborted && setRegionAudit({ region, results, pending: false, problem: null }))
      .catch((error: unknown) => !controller.signal.aborted && setRegionAudit({ region, results: null, pending: false, problem: String(error) }));
  };
  const clear = () => {
    request.current?.abort();
    setBox(null);
    setRegionAudit(null);
  };
  const current = regionAudit && sameRegion(regionAudit.region, box) ? regionAudit : null;
  useEffect(() => {
    if (!box) return onSelected(null);
    const lines = current?.results?.map(auditLine) ?? [];
    onSelected({
      selection: { datasetId: kpmp.dataset_id, sourceId: participantId, assay: "CODEX protein", region: box, units: "µm", markers: ["LRP2", "UMOD"], pane, scope: "box" },
      text: `${regionSize(box)} box on KPMP participant ${participantId} (${roleLabel(participant)}): ${lines.length ? `computed protein audit of exactly this box: ${lines.join("; ")}` : "not analysed yet"}`,
    });
  }, [box, current?.results]); // eslint-disable-line react-hooks/exhaustive-deps

  const tool = "h-7 rounded-full px-2.5 text-[12px]";
  return (
    <section
      aria-label={`Participant ${participantId}`}
      data-testid={role === "healthy reference" ? "provenance-left" : "provenance-right"}
      data-pane={pane}
      className="relative min-h-0 flex-1 overflow-hidden rounded-3xl bg-black"
    >
      {section ? (
        <CodexView
          section={section}
          visible={visible}
          fill={1.6}
          boxMode={boxMode}
          box={box}
          onBox={(b) => {
            setBoxMode(false);
            setBox(b);
          }}
          fitKey={fitKey}
          onViewChange={onViewChange}
          nudge={nudge}
        />
      ) : (
        <div className="grid h-full place-items-center text-[13px] text-ink-3" role="status">
          Loading {participantId}…
        </div>
      )}
      <div className="pointer-events-none absolute inset-x-3 top-3 flex flex-wrap items-start justify-between gap-2">
        <div className="pointer-events-auto rounded-2xl bg-[#16171b]/95 px-3.5 py-2.5 ring-1 ring-white/[0.06]">
          <p className="text-[15px] font-semibold">
            {participantId}{" "}
            <span className={`ml-1 rounded-full px-2 py-0.5 text-[12px] font-medium ${role === "healthy reference" ? "bg-[#222a10] text-stable" : "bg-[#2b2414] text-sensitive"}`}>
              {roleLabel(participant)}
            </span>
          </p>
          {choices.length > 1 && (
            <div className="mt-1.5 flex flex-wrap gap-1" role="group" aria-label={role === "healthy reference" ? "Healthy reference biopsies" : "Disease biopsies"}>
              {choices.map((c) => (
                <button
                  key={c.participant_id}
                  type="button"
                  aria-pressed={c.participant_id === participantId}
                  onClick={() => onChoose(c.participant_id)}
                  className="h-6 rounded-full bg-raised px-2.5 text-[11px] text-ink-2 hover:text-ink aria-pressed:bg-white aria-pressed:text-black"
                >
                  {roleLabel(c) === c.role ? c.participant_id : `${c.participant_id} · ${c.clinical["KPMP enrollment category"]}`}
                </button>
              ))}
            </div>
          )}
          <p className="mt-0.5 text-[12px] text-ink-3">
            {kpmp.dataset_id} · CODEX protein · {cells.toLocaleString()} cells · real microscopy
          </p>
          {whole && whole.length > 0 && <p className="mt-1 max-w-[300px] text-[12px] leading-snug text-ink-2">{takeaway(whole)}</p>}
          <div className="mt-2 flex flex-wrap gap-1" role="group" aria-label={`Tools for ${participantId}`}>
            <button type="button" aria-pressed={!boxMode} onClick={() => setBoxMode(false)} className={`${tool} bg-raised text-ink-2 aria-pressed:bg-white aria-pressed:text-black`}>
              Pan
            </button>
            <button type="button" aria-pressed={boxMode} onClick={() => setBoxMode(true)} className={`${tool} bg-raised text-ink-2 aria-pressed:bg-white aria-pressed:text-black`}>
              {boxMode ? "Drag on the image…" : "Draw box"}
            </button>
            <button type="button" onClick={() => setFitKey((k) => k + 1)} className={`${tool} bg-raised text-ink-2 hover:text-ink`}>
              Fit
            </button>
            <button type="button" onClick={onOpen} className={`${tool} bg-raised text-ink-2 hover:text-ink`}>
              Open
            </button>
          </div>
        </div>
        <div className="pointer-events-auto flex max-w-[min(420px,100%)] flex-col gap-1.5 rounded-2xl bg-[#16171b]/95 px-3 py-2 ring-1 ring-white/[0.06]">
          {box ? (
            <>
              <p className="text-[12px] text-ink-2">
                <span className="font-medium text-ink">Your box</span> · {regionSize(box)} on {participantId}
              </p>
              <div className="flex flex-wrap gap-1">
                <button type="button" onClick={analyse} disabled={current?.pending} className={`${tool} bg-white font-medium text-black disabled:opacity-60`}>
                  Analyse this region
                </button>
                <button type="button" onClick={clear} className={`${tool} text-ink-3 hover:text-ink`}>
                  Clear
                </button>
              </div>
              {current?.pending && <p className="shimmer-text text-[12px]">Computing the protein audit of this box…</p>}
              {current?.problem && <p className="text-[12px] text-bad">{current.problem}</p>}
              {current?.results && (
                <ul data-testid="region-protein-audit" data-pane={pane} className="flex flex-col gap-0.5">
                  {current.results.map((r) => (
                    <li key={r.result_id} className="flex items-center justify-between gap-2 text-[12px] text-ink-2" title={r.inference}>
                      <span>{auditLine(r)}</span>
                      <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${labelTone(r.label)}`}>{r.label.replaceAll("_", " ")}</span>
                    </li>
                  ))}
                  <li className="text-[11px] text-ink-3">Computed on exactly this box with the frozen KPMP thresholds; no model call.</li>
                </ul>
              )}
              {regionAudit && !current && !regionAudit.pending && <p className="text-[11px] text-ink-3">The box changed; analyse it again.</p>}
            </>
          ) : (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[11px] text-ink-3">Whole image:</span>
              {whole?.map((r) => (
                <span key={r.result_id} data-testid="protein-audit-result" data-label={r.label} className="flex items-center gap-1.5 text-[12px] text-ink-2" title={r.inference}>
                  {r.marker} in {r.population}+ {pct(r.conditions[0]?.observed_share ?? null)}
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${labelTone(r.label)}`}>{r.label.replaceAll("_", " ")}</span>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

export function CompareView({ adapter, kpmp, onOpen, onBack, onClassic, onAsk }: Props) {
  const healthy = kpmp.participants.filter((p) => p.role === "healthy reference");
  const disease = kpmp.participants.filter((p) => p.role !== "healthy reference");
  const [top, setTop] = useState(healthy[0]?.participant_id ?? "");
  const [bottom, setBottom] = useState(disease[0]?.participant_id ?? "");
  const [linked, setLinked] = useState(false);
  const [nudges, setNudges] = useState<[Nudge | null, Nudge | null]>([null, null]);
  const [picked, setPicked] = useState<Record<string, PaneSelection | null>>({});
  const chosen = ["top", "bottom"].flatMap((p) => (picked[p] ? [picked[p]!] : []));
  const askBoth = () => {
    if (chosen.length === 0) return;
    const both = chosen.length === 2;
    onAsk({
      participantId: chosen.map((c) => c.selection.sourceId).join(" and "),
      label: both ? "both boxes" : `your box on ${chosen[0]!.selection.sourceId}`,
      markers: ["LRP2", "UMOD", "CD20"],
      summary: `${both ? "Two boxes on two different people (separate specimens, not registered; each has its own denominator)" : "One box"}. ${chosen.map((c, i) => `${both ? (i === 0 ? "First" : "Second") : "The"}: ${c.text}.`).join(" ")}`,
      selection: chosen[0]!.selection,
      selections: chosen.map((c) => c.selection),
    });
  };
  const shown = [
    { pane: "top", p: healthy.find((p) => p.participant_id === top) ?? healthy[0], choices: healthy, choose: setTop },
    { pane: "bottom", p: disease.find((p) => p.participant_id === bottom) ?? disease[0], choices: disease, choose: setBottom },
  ];
  const channels = kpmp.participants[0]?.channels ?? [];
  const [visible, setVisible] = useState<Set<string>>(() => new Set(channels.map((c) => c.channel_id).filter((id) => !adapter.defaultHidden?.has(id))));
  const moved = (index: number) => (from: View, to: View) => {
    if (!linked) return;
    const other = 1 - index;
    setNudges((n) => {
      const next: [Nudge | null, Nudge | null] = [...n];
      next[other] = { key: (n[other]?.key ?? 0) + 1, dx: to.target[0] - from.target[0], dy: to.target[1] - from.target[1], dz: to.zoom - from.zoom };
      return next;
    });
  };
  return (
    <div className="flex h-full flex-col gap-3 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-[20px] font-semibold tracking-tight">Two different specimens: healthy reference above, diseased below</h1>
          <p className="text-[13px] text-ink-3">
            Each pane has its own camera, box and protein audit. The proteins switch on and off together.{" "}
            {linked ? "Navigation is linked: both move and zoom by the same amount. The biopsies are not registered, so the same screen position is not the same place." : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {channels.map((c) => {
            const on = visible.has(c.channel_id);
            return (
              <button
                key={c.channel_id}
                type="button"
                aria-pressed={on}
                title={c.description}
                onClick={() =>
                  setVisible((v) => {
                    const next = new Set(v);
                    if (on) next.delete(c.channel_id);
                    else next.add(c.channel_id);
                    return next;
                  })
                }
                className={`flex h-8 items-center gap-2 rounded-full px-3 text-[13px] ${on ? "bg-raised text-ink" : "text-ink-3 hover:text-ink-2"}`}
              >
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: on ? KPMP_COLOURS[c.channel_id] : "transparent", boxShadow: `inset 0 0 0 1.5px ${KPMP_COLOURS[c.channel_id] ?? "#fff"}` }} />
                {c.label}
              </button>
            );
          })}
          <button
            type="button"
            onClick={askBoth}
            disabled={chosen.length === 0}
            title={chosen.length === 0 ? "Draw a box on one or both biopsies first" : undefined}
            className="ml-2 h-8 rounded-full bg-white px-3 text-[13px] font-medium text-black disabled:bg-raised disabled:text-ink-3"
          >
            {chosen.length === 2 ? "Ask SpatialScout about both regions" : chosen.length === 1 ? "Ask SpatialScout about this region" : "Draw boxes, then ask about them"}
          </button>
          <button type="button" aria-pressed={linked} onClick={() => setLinked((l) => !l)} className="ml-2 h-8 rounded-full bg-raised px-3 text-[13px] text-ink-2 hover:text-ink aria-pressed:bg-white aria-pressed:text-black">
            Link navigation
          </button>
          <button
            type="button"
            onClick={onClassic}
            title="A power tool for inspecting molecule-level sections and exploratory SAM outlines; not part of the guided demo."
            className="ml-2 h-8 rounded-full px-3 text-[13px] text-ink-2 underline decoration-ink-3 underline-offset-4 hover:text-ink"
          >
            Expert: Xenium viewer with SAM outlines
          </button>
          <button type="button" onClick={onBack} className="ml-2 h-8 rounded-full bg-raised px-3 text-[13px] text-ink hover:bg-[#2a2d32]">
            Back to one biopsy
          </button>
        </div>
      </div>
      {shown.map(({ pane, p, choices, choose }, index) =>
        p ? (
          <Pane
            key={`${pane}-${p.participant_id}`}
            pane={pane}
            adapter={adapter}
            kpmp={kpmp}
            participant={p}
            choices={choices}
            onChoose={choose}
            visible={visible}
            onOpen={() => onOpen(p.participant_id)}
            onSelected={(s) => setPicked((all) => ({ ...all, [pane]: s }))}
            onViewChange={moved(index)}
            nudge={nudges[index] ?? null}
          />
        ) : null,
      )}
    </div>
  );
}
