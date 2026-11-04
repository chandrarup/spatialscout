// The dual-section viewer: a control section on the left and a diseased section on the right, each drawn by its own
// dataset adapter as a multichannel image with toggleable channels, with pan and zoom linked (or not), one region
// box per section, the live gate readout for each box, SAM 3.1 on a box, and the region pair kept as context for
// the next question. Verdicts stay at cohort level; the region pair is visual evidence beside them.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Region } from "../contracts/generated";
import type { DatasetAdapter, GateQuery, LoadedSection, SectionChoice } from "../datasets/adapter";
import { type PaneAudit, ProteinAuditPanel } from "./ProteinAuditPanel";
import { type Camera, type GateReadout, type SamState, SectionPane, type Tool } from "./SectionPane";

export interface RegionPair {
  datasetIds: string[];
  regions: Region[];
}

interface Props {
  adapters: DatasetAdapter[];
  /** The adapter both panes open first. */
  defaultDatasetId: string | null;
  /** Called with the left pane's dataset and section when it opens, so the workspace can show its capabilities. */
  onShow?: (datasetId: string, sectionId: string) => void;
  /** The drawn region pair when the researcher keeps it for the next question, else null. */
  onContext: (pair: RegionPair | null) => void;
}

type Side = 0 | 1;
const SIDES: Side[] = [0, 1];
const SIDE_NAMES = ["left", "right"] as const;
const FIT_MARGIN = 0.92;
const MAX_ZOOM = 2.7; // about 0.15 µm per pixel: closer shows nothing the molecule table can resolve

interface PaneSource {
  datasetId: string;
  sectionId: string;
}

export function DualViewer({ adapters, defaultDatasetId, onShow, onContext }: Props) {
  const byId = useMemo(() => new Map(adapters.map((a) => [a.datasetId, a])), [adapters]);
  const [sectionLists, setSectionLists] = useState<Record<string, SectionChoice[]>>({});
  const [sources, setSources] = useState<[PaneSource | null, PaneSource | null]>([null, null]);

  // Open the default pair once the default adapter's sections are known.
  useEffect(() => {
    const first = (defaultDatasetId && byId.get(defaultDatasetId)) || adapters[0];
    if (!first) return;
    let current = true;
    Promise.all(adapters.map((a) => a.sections().then((s) => [a.datasetId, s] as const))).then((lists) => {
      if (!current) return;
      const all = Object.fromEntries(lists);
      setSectionLists(all);
      const [left, right] = first.defaultPair(all[first.datasetId] ?? []);
      setSources((s) => (s[0] && s[1] ? s : [{ datasetId: first.datasetId, sectionId: left }, { datasetId: first.datasetId, sectionId: right }]));
    });
    return () => {
      current = false;
    };
  }, [adapters, byId, defaultDatasetId]);

  const panes = [usePane(sources[0], byId), usePane(sources[1], byId)] as const;

  useEffect(() => {
    if (sources[0] && onShow) onShow(sources[0].datasetId, sources[0].sectionId);
  }, [sources, onShow]);

  // --- cameras ---------------------------------------------------------------------------------------------------
  const [linked, setLinked] = useState(true);
  const [cameras, setCameras] = useState<[Camera | null, Camera | null]>([null, null]);
  const [sizes, setSizes] = useState<[{ width: number; height: number } | null, { width: number; height: number } | null]>([null, null]);
  const onSizes = useMemo(
    () =>
      SIDES.map((i) => (s: { width: number; height: number }) =>
        setSizes((current) => {
          if (current[i]?.width === s.width && current[i]?.height === s.height) return current;
          const out: typeof current = [...current];
          out[i] = s;
          return out;
        }),
      ),
    [],
  );
  const fitted = useRef<string>("");
  const fits = SIDES.map((i) => fitZoom(panes[i].loaded, sizes[i]));
  const zoomRange = useMemo(() => {
    const lowest = Math.min(...fits.filter((f): f is number => f !== null), 0);
    return { min: lowest - 2, max: MAX_ZOOM };
  }, [fits[0], fits[1]]); // eslint-disable-line react-hooks/exhaustive-deps

  const fitBoth = useCallback(() => {
    const zooms = SIDES.map((i) => fitZoom(panes[i].loaded, sizes[i]));
    const shared = Math.min(...zooms.filter((z): z is number => z !== null));
    setCameras(
      SIDES.map((i) => {
        const loaded = panes[i].loaded;
        const zoom = zooms[i];
        if (!loaded || zoom === null) return null;
        const { x0, y0, x1, y1 } = loaded.extent;
        // Linked panes share one scale, so a micrometre is the same length on both and the scale bars agree.
        return { target: [(x0 + x1) / 2, (y0 + y1) / 2], zoom: linked ? shared : zoom };
      }) as [Camera | null, Camera | null],
    );
  }, [panes[0].loaded, panes[1].loaded, sizes, linked]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const key = `${panes[0].loaded?.sectionId}|${panes[1].loaded?.sectionId}|${!!sizes[0]}|${!!sizes[1]}`;
    if (!panes[0].loaded || !panes[1].loaded || !sizes[0] || !sizes[1] || fitted.current === key) return;
    fitted.current = key;
    fitBoth();
  }, [panes[0].loaded, panes[1].loaded, sizes, fitBoth]); // eslint-disable-line react-hooks/exhaustive-deps

  const moveCamera = (side: Side, next: Camera) => {
    setCameras((current) => {
      const out: [Camera | null, Camera | null] = [...current];
      const previous = current[side];
      out[side] = next;
      const other = (1 - side) as Side;
      const twin = current[other];
      if (linked && previous && twin) {
        // Apply the same zoom change and the same pan in micrometres, so each pane keeps its own place in its section.
        out[other] = {
          target: [twin.target[0] + next.target[0] - previous.target[0], twin.target[1] + next.target[1] - previous.target[1]],
          zoom: twin.zoom + next.zoom - previous.zoom,
        };
      }
      return out;
    });
  };
  const flyPaneTo = (side: Side, box: Region) => {
    const size = sizes[side];
    if (!size) return;
    const span = Math.max(box.x1 - box.x0, box.y1 - box.y0, 1);
    const zoom = Math.log2(Math.min(size.width, size.height) / (span * 3));
    setCameras((current) => {
      const out: [Camera | null, Camera | null] = [...current];
      const previous = current[side];
      out[side] = { target: [(box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2], zoom };
      const other = (1 - side) as Side;
      const twin = current[other];
      if (linked && previous && twin) out[other] = { ...twin, zoom: twin.zoom + zoom - previous.zoom };
      return out;
    });
  };

  // --- channels, tool and population ----------------------------------------------------------------------------
  const channelIds = unique(panes.flatMap((p) => p.loaded?.channels.map((c) => c.id) ?? []));
  const [hidden, setHidden] = useState<ReadonlySet<string>>(new Set());
  const visibleChannels = useMemo(() => new Set(channelIds.filter((id) => !hidden.has(id))), [channelIds.join(","), hidden]); // eslint-disable-line react-hooks/exhaustive-deps
  const [gain, setGain] = useState(1);
  const [tool, setTool] = useState<Tool>("pan");

  const leftAdapter = sources[0] ? byId.get(sources[0].datasetId) : undefined;
  useEffect(() => {
    setHidden(new Set(leftAdapter?.defaultHidden ?? []));
  }, [leftAdapter]);
  const hasGates = SIDES.some((i) => !!(sources[i] && byId.get(sources[i]!.datasetId)?.gateStatus));
  const [query, setQuery] = useState<GateQuery | null>(null);
  useEffect(() => {
    if (leftAdapter && query === null) setQuery(leftAdapter.defaultGateQuery);
  }, [leftAdapter, query]);
  const cellTypes = unique(panes.flatMap((p) => p.loaded?.cellTypes ?? []));
  const geneSets = leftAdapter?.geneSets ?? [];

  // --- region pair as investigation context ------------------------------------------------------------------------
  const [keep, setKeep] = useState(false);
  const boxes = panes.map((p) => p.box);
  useEffect(() => {
    const regions = boxes.filter((b): b is Region => b !== null);
    if (!keep || regions.length === 0) {
      onContext(null);
      return;
    }
    onContext({ datasetIds: unique(SIDES.filter((i) => boxes[i]).map((i) => sources[i]?.datasetId ?? "")), regions });
  }, [keep, boxes[0], boxes[1], sources, onContext]); // eslint-disable-line react-hooks/exhaustive-deps

  const gates = [useGate(panes[0], sources[0], byId, query), useGate(panes[1], sources[1], byId, query)];
  const audits = [useProteinAudit(panes[0], sources[0], byId), useProteinAudit(panes[1], sources[1], byId)];
  const auditPanes = SIDES.flatMap((i) => (audits[i] ? [audits[i]!] : []));

  const pick = (side: Side, value: string) => {
    const [datasetId, sectionId] = value.split("::");
    if (!datasetId || !sectionId) return;
    setSources((s) => {
      const out: [PaneSource | null, PaneSource | null] = [...s];
      out[side] = { datasetId, sectionId };
      return out;
    });
  };

  return (
    <section aria-label="Dual-section viewer" className="flex h-full min-h-[34rem] flex-col gap-2">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-md border border-line bg-panel px-3 py-2 text-xs">
        <div className="flex items-center gap-1" role="group" aria-label="Tool">
          <ToolButton active={tool === "pan"} onClick={() => setTool("pan")} label="Pan & zoom" />
          <ToolButton active={tool === "box"} onClick={() => setTool("box")} label="Draw region box" />
        </div>
        <label className="flex items-center gap-1.5 text-ink-2">
          <input type="checkbox" checked={linked} onChange={(e) => setLinked(e.target.checked)} className="accent-[var(--color-accent)]" />
          Link pan and zoom
        </label>
        <button type="button" onClick={fitBoth} className="rounded border border-line px-2 py-0.5 text-ink-2 hover:border-ink-3 hover:text-ink">
          Fit both
        </button>
        <div className={`ml-auto flex items-center gap-2 text-ink-3 ${hasGates ? "" : "hidden"}`}>
          <span>Gate population</span>
          <select
            aria-label="Cell type"
            className="rounded border border-line bg-raised px-1.5 py-0.5 text-ink"
            value={query?.cellType ?? ""}
            onChange={(e) => setQuery((q) => ({ cellType: e.target.value, genes: q?.genes ?? [] }))}
          >
            {cellTypes.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
          <span>cells ·</span>
          <select
            aria-label="Genes"
            className="rounded border border-line bg-raised px-1.5 py-0.5 text-ink"
            value={query?.genes.join("/") ?? ""}
            onChange={(e) => setQuery((q) => ({ cellType: q?.cellType ?? "", genes: e.target.value.split("/") }))}
          >
            {geneSets.map((g) => (
              <option key={g.label} value={g.genes.join("/")}>
                {g.label}
              </option>
            ))}
          </select>
          <span>molecules</span>
        </div>
      </div>

      {/* Channels */}
      <div className="flex flex-wrap items-center gap-1.5 text-xs" role="group" aria-label="Channels">
        {channelIds.map((id) => {
          const choices = panes.map((p) => p.loaded?.channels.find((c) => c.id === id) ?? null);
          const any = choices.find((c) => c !== null);
          if (!any) return null;
          const on = visibleChannels.has(id);
          const notes = choices.flatMap((c, i) => (c && (c.note || !c.available) ? [`${panes[i]?.loaded?.title}: ${c.note ?? "unavailable"}`] : []));
          return (
            <button
              key={id}
              type="button"
              aria-pressed={on}
              data-channel={id}
              title={[any.description, ...choices.map((c, i) => (c ? `${panes[i]?.loaded?.title}: ${c.amount}` : "")), ...notes].filter(Boolean).join("\n")}
              onClick={() =>
                setHidden((h) => {
                  const next = new Set(h);
                  if (next.has(id)) next.delete(id);
                  else next.add(id);
                  return next;
                })
              }
              className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 transition-colors ${
                on ? "border-white/25 bg-white/5 text-ink" : "border-line text-ink-3 line-through decoration-ink-3/60"
              }`}
            >
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: any.colour, boxShadow: on ? `0 0 8px ${any.colour}` : "none", opacity: on ? 1 : 0.35 }} />
              {any.label}
              {choices.some((c) => c && !c.available) && <span className="text-[10px] text-ink-3">(absent in one)</span>}
            </button>
          );
        })}
        <label className="ml-auto flex items-center gap-1.5 text-ink-3">
          Brightness
          <input
            type="range"
            min={-2}
            max={2}
            step={0.25}
            value={Math.log2(gain)}
            onChange={(e) => setGain(2 ** Number(e.target.value))}
            className="w-24 accent-[var(--color-accent)]"
            aria-label="Brightness"
          />
        </label>
      </div>

      {/* Panes */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-2 md:grid-cols-2">
        {SIDES.map((i) => {
          const pane = panes[i];
          const adapter = sources[i] ? byId.get(sources[i]!.datasetId) : undefined;
          return (
            <div key={i} className="flex min-h-0 flex-col gap-1">
              <select
                aria-label={`${i === 0 ? "Left" : "Right"} section`}
                className="w-full min-w-0 rounded border border-line bg-raised px-2 py-1 text-xs text-ink"
                value={sources[i] ? `${sources[i]!.datasetId}::${sources[i]!.sectionId}` : ""}
                onChange={(e) => pick(i, e.target.value)}
              >
                {adapters.map((a) =>
                  groupSections(sectionLists[a.datasetId] ?? []).map(([group, sections]) => (
                    <optgroup key={`${a.datasetId}/${group}`} label={`${a.label} · ${group}`}>
                      {sections.map((s) => (
                        <option key={s.sectionId} value={`${a.datasetId}::${s.sectionId}`}>
                          {s.name ? `${group} ${s.name} · ${s.sectionId}` : s.sectionId}
                          {s.detail ? ` · ${s.detail}` : ""}
                          {s.duplicateOf ? ` · same data as ${s.duplicateOf}` : ""}
                        </option>
                      ))}
                    </optgroup>
                  )),
                )}
              </select>
              <div className="min-h-0 flex-1">
                <SectionPane
                  side={SIDE_NAMES[i]}
                  loaded={pane.loaded}
                  loading={pane.loading}
                  problem={pane.problem}
                  camera={cameras[i]}
                  zoomRange={zoomRange}
                  onCamera={(c) => moveCamera(i, c)}
                  onSize={onSizes[i]!}
                  tool={tool}
                  visibleChannels={visibleChannels}
                  gain={gain}
                  box={pane.box}
                  onBox={pane.setBox}
                  gate={gates[i]!}
                  recordedBoxes={pane.recordedBoxes}
                  onPickRecorded={(b) => {
                    pane.setBox(b);
                    flyPaneTo(i, b);
                  }}
                  sam={pane.sam}
                  samMaxSideUm={adapter?.sam?.maxBoxSideUm ?? null}
                  onRunSam={pane.runSam}
                />
              </div>
            </div>
          );
        })}
      </div>

      {auditPanes.length > 0 && <ProteinAuditPanel panes={auditPanes} />}

      {/* Region pair */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-md border border-line bg-panel px-3 py-2 text-xs text-ink-2">
        <span className="font-semibold text-ink">Region pair</span>
        {SIDES.map((i) => (
          <span key={i} className="font-mono text-[11px]">
            {panes[i].loaded?.title.split(" · ")[0] ?? "…"}:{" "}
            {boxes[i] ? `${fmt(boxes[i]!.x0)}–${fmt(boxes[i]!.x1)} × ${fmt(boxes[i]!.y0)}–${fmt(boxes[i]!.y1)} µm` : "no box drawn"}
            {boxes[i] && (
              <button type="button" className="ml-1.5 text-ink-3 underline hover:text-ink" onClick={() => panes[i].setBox(null)}>
                clear
              </button>
            )}
          </span>
        ))}
        <label className="ml-auto flex items-center gap-1.5">
          <input
            type="checkbox"
            checked={keep}
            disabled={!boxes[0] && !boxes[1]}
            onChange={(e) => setKeep(e.target.checked)}
            className="accent-[var(--color-accent)]"
          />
          Keep this region pair with the next question
        </label>
        <span className="w-full text-[11px] text-ink-3">
          {auditPanes.length > 0
            ? "Protein audits are computed per participant for each box and are descriptive: one person against one person."
            : "Verdicts stay at cohort level; the region pair is shown beside them as visual evidence and does not scope the analysis."}
        </span>
      </div>
    </section>
  );
}

// --- one pane's section, box and SAM ---------------------------------------------------------------------------------

interface PaneModel {
  loaded: LoadedSection | null;
  loading: boolean;
  problem: string | null;
  box: Region | null;
  setBox: (box: Region | null) => void;
  recordedBoxes: Region[];
  sam: SamState;
  runSam: () => void;
}

function usePane(source: PaneSource | null, adapters: Map<string, DatasetAdapter>): PaneModel {
  const [loaded, setLoaded] = useState<LoadedSection | null>(null);
  const [loading, setLoading] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [box, setBoxState] = useState<Region | null>(null);
  const [recordedBoxes, setRecordedBoxes] = useState<Region[]>([]);
  const [sam, setSam] = useState<SamState>({ run: null, busy: false, problem: null });
  const adapter = source ? adapters.get(source.datasetId) : undefined;

  useEffect(() => {
    if (!source || !adapter) return;
    let current = true;
    setLoading(true);
    setProblem(null);
    setLoaded(null);
    setBoxState(null);
    setSam({ run: null, busy: false, problem: null });
    adapter
      .load(source.sectionId)
      .then((l) => current && setLoaded(l))
      .catch((e: unknown) => current && setProblem(String(e)))
      .finally(() => current && setLoading(false));
    adapter.sam
      ?.recordedBoxes(source.sectionId)
      .then((b) => current && setRecordedBoxes(b))
      .catch(() => current && setRecordedBoxes([]));
    return () => {
      current = false;
    };
  }, [source?.datasetId, source?.sectionId, adapter]); // eslint-disable-line react-hooks/exhaustive-deps

  const setBox = useCallback((next: Region | null) => {
    setBoxState(next);
    setSam((s) => (s.run || s.problem ? { run: null, busy: false, problem: null } : s)); // an outline belongs to the box it was run on
  }, []);

  const runSam = useCallback(() => {
    if (!adapter?.sam || !box || !source) return;
    setSam({ run: null, busy: true, problem: null });
    adapter.sam
      .outline(source.sectionId, box)
      .then((run) => setSam({ run, busy: false, problem: null }))
      .catch((e: unknown) =>
        setSam({ run: null, busy: false, problem: e instanceof Error ? e.message : String(e) }),
      );
  }, [adapter, box, source]);

  return { loaded, loading, problem, box, setBox, recordedBoxes, sam, runSam };
}

/**
 * The gate readout for a pane's box: at most one request in flight, and the latest box is always sent next, so
 * readouts never arrive out of order and a fast drag never queues stale boxes. Without a box, the whole section
 * (which also warms the server's section cache before the first drag).
 */
function useGate(pane: PaneModel, source: PaneSource | null, adapters: Map<string, DatasetAdapter>, query: GateQuery | null): GateReadout {
  const adapter = source ? adapters.get(source.datasetId) : undefined;
  const [readout, setReadout] = useState<GateReadout>({ status: null, latencyMs: null, pending: false, problem: null });
  const latest = useRef<{ key: string; box: Region | null; at: number } | null>(null);
  const sent = useRef<string | null>(null);
  const inFlight = useRef(false);
  const generation = useRef(0);
  const sectionId = pane.loaded?.sectionId ?? null;

  const pump = useCallback(() => {
    const request = latest.current;
    if (inFlight.current || !request || request.key === sent.current || !adapter?.gateStatus || !query || !sectionId) return;
    inFlight.current = true;
    sent.current = request.key;
    const mine = generation.current;
    setReadout((r) => ({ ...r, pending: true }));
    adapter
      .gateStatus(sectionId, query, request.box)
      .then((status) => {
        if (mine !== generation.current) return;
        setReadout({ status, latencyMs: request.box ? performance.now() - request.at : null, pending: latest.current?.key !== request.key, problem: null });
      })
      .catch((e: unknown) => mine === generation.current && setReadout((r) => ({ ...r, pending: false, problem: String(e) })))
      .finally(() => {
        if (mine !== generation.current) return;
        inFlight.current = false;
        pump();
      });
  }, [adapter, query, sectionId]);

  useEffect(() => {
    generation.current += 1;
    inFlight.current = false;
    sent.current = null;
    setReadout({ status: null, latencyMs: null, pending: false, problem: null });
  }, [sectionId, query?.cellType, query?.genes.join("/")]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!sectionId || !query) return;
    const box = pane.box;
    latest.current = { key: `${sectionId}|${query.cellType}|${query.genes.join("/")}|${box ? [box.x0, box.y0, box.x1, box.y1].join(",") : "all"}`, box, at: performance.now() };
    pump();
  }, [pane.box, sectionId, query, pump]);

  return readout;
}

/** The protein audit of a pane's box (or whole image) on a dataset that has one, refreshed shortly after the box settles. */
function useProteinAudit(pane: PaneModel, source: PaneSource | null, adapters: Map<string, DatasetAdapter>): PaneAudit | null {
  const adapter = source ? adapters.get(source.datasetId) : undefined;
  const [audit, setAudit] = useState<PaneAudit | null>(null);
  const sectionId = pane.loaded?.sectionId ?? null;
  const title = pane.loaded?.title.split(" · ").slice(0, 2).join(" · ") ?? "";
  useEffect(() => {
    if (!adapter?.proteinAudit || !sectionId) {
      setAudit(null);
      return;
    }
    const controller = new AbortController();
    setAudit((a) => ({ title, results: a?.title === title ? a.results : null, pending: true, problem: null }));
    const timer = window.setTimeout(() => {
      adapter.proteinAudit!(sectionId, pane.box, controller.signal)
        .then((results) => setAudit({ title, results, pending: false, problem: null }))
        .catch((e: unknown) => {
          if (!controller.signal.aborted) setAudit({ title, results: null, pending: false, problem: String(e) });
        });
    }, 200);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [adapter, sectionId, pane.box, title]);
  return audit;
}

// --- helpers ----------------------------------------------------------------------------------------------------------

function fitZoom(loaded: LoadedSection | null, size: { width: number; height: number } | null): number | null {
  if (!loaded || !size) return null;
  const { x0, y0, x1, y1 } = loaded.extent;
  return Math.log2(Math.min(size.width / Math.max(x1 - x0, 1), size.height / Math.max(y1 - y0, 1)) * FIT_MARGIN);
}

function unique<T>(values: T[]): T[] {
  return [...new Set(values)];
}

function fmt(v: number): string {
  return Math.round(v).toLocaleString();
}

function groupSections(sections: SectionChoice[]): [string, SectionChoice[]][] {
  const groups = new Map<string, SectionChoice[]>();
  for (const s of sections) groups.set(s.group, [...(groups.get(s.group) ?? []), s]);
  return [...groups.entries()];
}

function ToolButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`rounded px-2 py-0.5 ${active ? "bg-accent text-white" : "border border-line text-ink-2 hover:text-ink"}`}
    >
      {label}
    </button>
  );
}
