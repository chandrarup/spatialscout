// Measured molecule depth for one box: the molecules drawn at their real x, y and z (orbit, pan, zoom), a depth slice,
// and the box's depth profile counted from every molecule, not the drawn sample. Depth comes from a verified sidecar
// joined by transcript id; a section without one says so and offers the sections that have it. This is new
// descriptive exploration: it shows where molecules sit, not why a signal is present.
import { OrbitView } from "@deck.gl/core";
import { PathLayer, PointCloudLayer } from "@deck.gl/layers";
import DeckGL from "@deck.gl/react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { DepthPoints, DepthProfile, DepthSource, Region } from "../contracts/generated";
import { EXCLUDED_MOLECULE, GENE_SLOTS, rgbOf } from "../palette";
import { regionSize } from "../selection";

const BUDGET = 40_000;
const EXAGGERATIONS = [1, 2, 4];

interface Props {
  region: Region;
  genes: string[];
  cellType: string | null;
  labelRuleId: string | null;
  onOpenSection: (sectionId: string) => void;
}

/** Blue (shallow) to yellow (deep), ordered in lightness and bright enough to read on black. */
function depthColour(t: number): [number, number, number] {
  const stops: [number, number, number][] = [
    [80, 120, 255],
    [40, 170, 230],
    [40, 200, 160],
    [150, 220, 80],
    [253, 231, 37],
  ];
  const s = Math.min(0.9999, Math.max(0, t)) * (stops.length - 1);
  const i = Math.floor(s);
  const f = s - i;
  const a = stops[i]!;
  const b = stops[i + 1]!;
  return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f];
}

export function DepthView({ region, genes, cellType, labelRuleId, onOpenSection }: Props) {
  const [source, setSource] = useState<DepthSource | null>(null);
  const [missing, setMissing] = useState<{ reason: string; verified: string[] } | null>(null);
  const [zRange, setZRange] = useState<[number, number] | null>(null);
  const [points, setPoints] = useState<DepthPoints | null>(null);
  const [profile, setProfile] = useState<DepthProfile | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [colourBy, setColourBy] = useState<"depth" | "gene" | "rule">("depth");
  const [exaggeration, setExaggeration] = useState(1);
  const [viewKey, setViewKey] = useState(0);
  const sectionId = region.section_id;

  useEffect(() => {
    let live = true;
    setSource(null);
    setMissing(null);
    setZRange(null);
    api
      .depth(sectionId)
      .then((s) => {
        if (!live) return;
        setSource(s);
        if (s.z_min !== null && s.z_max !== null) setZRange([s.z_min, s.z_max]);
      })
      .catch((error: unknown) => {
        if (!live) return;
        api
          .depthSections()
          .then((verified) => live && setMissing({ reason: String(error).replace(/^Error:\s*\d+ [^:]*:\s*/, ""), verified }))
          .catch(() => live && setMissing({ reason: String(error), verified: [] }));
      });
    return () => {
      live = false;
    };
  }, [sectionId]);

  const key = JSON.stringify([region, genes, zRange]);
  useEffect(() => {
    if (!source || !zRange || genes.length === 0) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      api
        .depthPoints(region, genes, zRange, BUDGET, controller.signal)
        .then(setPoints)
        .catch((error: unknown) => !controller.signal.aborted && setProblem(String(error)));
    }, 150);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [source, key]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!source || genes.length === 0) return;
    const controller = new AbortController();
    setProfile(null);
    api
      .depthProfile({ region, genes: genes as [string, ...string[]], bin_um: 1, cell_type: cellType, label_rule_id: labelRuleId }, controller.signal)
      .then(setProfile)
      .catch((error: unknown) => !controller.signal.aborted && setProblem(String(error)));
    return () => controller.abort();
  }, [source, JSON.stringify([region, genes, cellType, labelRuleId])]); // eslint-disable-line react-hooks/exhaustive-deps

  const cx = (region.x0 + region.x1) / 2;
  const cy = (region.y0 + region.y1) / 2;
  const zc = source && source.z_min !== null && source.z_max !== null ? (source.z_min + source.z_max) / 2 : 0;
  const span = Math.max(region.x1 - region.x0, region.y1 - region.y0, 1);
  const data = useMemo(() => {
    if (!points || !source) return null;
    const n = points.displayed;
    const positions = new Float32Array(n * 3);
    const colours = new Uint8Array(n * 4);
    const zmin = source.z_min ?? 0;
    const zspan = Math.max((source.z_max ?? 1) - zmin, 1e-6);
    const slots = GENE_SLOTS.map(rgbOf);
    const dropped = rgbOf(EXCLUDED_MOLECULE);
    for (let i = 0; i < n; i++) {
      positions[3 * i] = points.x[i]! - cx;
      positions[3 * i + 1] = points.y[i]! - cy;
      positions[3 * i + 2] = (points.z[i]! - zc) * exaggeration;
      const c: readonly number[] =
        colourBy === "depth"
          ? depthColour((points.z[i]! - zmin) / zspan)
          : colourBy === "gene"
            ? (slots[points.gene_index[i]! % slots.length] ?? [255, 255, 255])
            : points.kept_stricter[i]
              ? [235, 235, 235]
              : points.assigned[i]
                ? dropped
                : [90, 90, 90];
      colours.set([c[0] ?? 255, c[1] ?? 255, c[2] ?? 255, 230], 4 * i);
    }
    return { length: n, attributes: { getPosition: { value: positions, size: 3 }, getColor: { value: colours, size: 4, normalized: true } } };
  }, [points, source, cx, cy, zc, exaggeration, colourBy]);

  const plane = useMemo(() => {
    const hx = (region.x1 - region.x0) / 2;
    const hy = (region.y1 - region.y0) / 2;
    const z = ((zRange?.[0] ?? zc) - zc) * exaggeration;
    return new PathLayer({
      id: "depth-plane",
      data: [[[-hx, -hy, z], [hx, -hy, z], [hx, hy, z], [-hx, hy, z], [-hx, -hy, z]]],
      getPath: (d: number[][]) => d as [number, number, number][],
      getColor: [255, 255, 255, 110],
      getWidth: 1,
      widthUnits: "pixels",
    });
  }, [region, zRange, zc, exaggeration]);

  if (missing) {
    const others = missing.verified.filter((s) => s !== sectionId);
    return (
      <div className="flex h-full flex-col items-start justify-center gap-2 rounded-lg border border-line p-6 text-[13px] text-ink-2" data-testid="depth-unavailable">
        <p className="text-ink">No verified measured depth for section {sectionId}.</p>
        <p className="text-ink-3">{missing.reason}</p>
        {others.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-ink-3">Sections with verified depth:</span>
            {others.map((s) => (
              <button key={s} type="button" onClick={() => onOpenSection(s)} className="h-7 rounded-full bg-raised px-3 text-[12px] text-ink hover:bg-[#2a2d32]">
                Open {s}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  const zmin = source?.z_min ?? 0;
  const zmax = source?.z_max ?? 1;
  const gene = genes[0] ?? "";
  const peak = profile ? Math.max(1, ...profile.bins.map((b) => b.counts[gene]?.all ?? 0)) : 1;
  const inSlice = profile && zRange ? profile.bins.filter((b) => b.z1 > zRange[0] && b.z0 <= zRange[1]) : [];
  const sliceSum = (condition: string) => inSlice.reduce((n, b) => n + (b.counts[gene]?.[condition] ?? 0), 0);

  return (
    <div className="grid h-full min-h-0 grid-cols-1 gap-2 lg:grid-cols-[1fr_300px]" data-testid="depth-view">
      <div className="relative min-h-[260px] overflow-hidden rounded-lg border border-line bg-black">
        {data && (
          <DeckGL
            key={viewKey}
            views={new OrbitView({ id: "depth", orbitAxis: "Z", fovy: 40 })}
            initialViewState={{ target: [0, 0, 0], rotationX: 35, rotationOrbit: -30, zoom: Math.log2(500 / span), minZoom: -4, maxZoom: 12 }}
            controller={{ dragPan: true, dragRotate: true, scrollZoom: true, inertia: false }}
            layers={[plane, new PointCloudLayer({ id: "depth-points", data, pointSize: 3.5, sizeUnits: "pixels", material: false })]}
          />
        )}
        {!data && !problem && <p className="shimmer-text absolute top-3 left-3 text-[12px]">Loading measured depths…</p>}
        {problem && <p className="absolute top-3 left-3 text-[12px] text-bad">{problem}</p>}
        <div className="pointer-events-none absolute inset-x-3 bottom-2 text-[11px] text-ink-3">
          {points && (
            <p data-testid="depth-counts">
              {points.displayed.toLocaleString()} drawn of {points.eligible.toLocaleString()} molecules in the slice ({points.total_in_box.toLocaleString()} in the box) ·{" "}
              {points.sampling} · x, y, z in µm{exaggeration > 1 ? ` · z exaggerated ${exaggeration}×` : " · true aspect"} · drag to orbit, right-drag to pan
            </p>
          )}
          {source && (
            <p>
              Measured z from {source.raw_file}, joined by transcript id ({source.with_depth.toLocaleString()} of {source.molecules.toLocaleString()} with depth, x/y match{" "}
              {source.max_xy_disagreement_um} µm). Cell outlines are not reconstructed in 3D.
            </p>
          )}
        </div>
      </div>
      <aside aria-label="Depth controls and profile" className="flex min-h-0 flex-col gap-2 overflow-y-auto rounded-lg border border-line p-3 text-[12px]">
        <p className="text-ink">
          <span className="font-medium">3D molecule depth</span> · {sectionId} · {regionSize(region)}
        </p>
        <div className="flex flex-wrap gap-1" role="group" aria-label="Colour by">
          {(["depth", "gene", "rule"] as const).map((c) => (
            <button key={c} type="button" aria-pressed={colourBy === c} onClick={() => setColourBy(c)} className="h-7 rounded-full bg-raised px-2.5 text-ink-2 aria-pressed:bg-white aria-pressed:text-black">
              {c === "depth" ? "Colour by depth" : c === "gene" ? "By gene" : "Kept / dropped (nucleus-only)"}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Z exaggeration">
          <span className="text-ink-3">z scale</span>
          {EXAGGERATIONS.map((e) => (
            <button key={e} type="button" aria-pressed={exaggeration === e} onClick={() => setExaggeration(e)} className="h-7 rounded-full bg-raised px-2.5 text-ink-2 aria-pressed:bg-white aria-pressed:text-black">
              {e === 1 ? "1× (true)" : `${e}×`}
            </button>
          ))}
          <button type="button" onClick={() => setViewKey((k) => k + 1)} className="ml-auto h-7 rounded-full bg-raised px-2.5 text-ink-2 hover:text-ink">
            Reset view
          </button>
        </div>
        {zRange && (
          <fieldset className="flex flex-col gap-1">
            <legend className="text-ink-3">
              Depth slice: {zRange[0].toFixed(1)}–{zRange[1].toFixed(1)} µm
            </legend>
            <input aria-label="Slice from (µm)" type="range" min={zmin} max={zmax} step={0.25} value={zRange[0]} onChange={(e) => setZRange([Math.min(Number(e.target.value), zRange[1]), zRange[1]])} />
            <input aria-label="Slice to (µm)" type="range" min={zmin} max={zmax} step={0.25} value={zRange[1]} onChange={(e) => setZRange([zRange[0], Math.max(Number(e.target.value), zRange[0])])} />
          </fieldset>
        )}
        <section aria-label="Depth profile" data-testid="depth-profile" className="mt-1 border-t border-line pt-2">
          <p className="font-medium text-ink">New descriptive depth exploration</p>
          <p className="text-ink-3">
            {gene} molecules {profile?.scope ?? ""} per 1 µm of depth, counted from every molecule (not the drawn sample). Separate from the recorded 2D analysis.
          </p>
          {profile && (
            <>
              <ul className="mt-1.5 flex flex-col gap-px">
                {profile.bins.map((b) => {
                  const all = b.counts[gene]?.all ?? 0;
                  const kept = b.counts[gene]?.nucleus_only ?? 0;
                  const lit = zRange ? b.z1 > zRange[0] && b.z0 <= zRange[1] : true;
                  return (
                    <li key={b.z0} className={`grid grid-cols-[44px_1fr_40px] items-center gap-1.5 tabular-nums ${lit ? "" : "opacity-35"}`} title={`${b.z0}–${b.z1} µm: ${all} molecules, ${kept} kept under nucleus-only`}>
                      <span className="text-ink-3">{b.z0.toFixed(0)}</span>
                      <span className="relative h-2.5 rounded-sm bg-raised">
                        <span className="absolute inset-y-0 left-0 rounded-sm bg-white/35" style={{ width: `${(all / peak) * 100}%` }} />
                        <span className="absolute inset-y-0 left-0 rounded-sm bg-white" style={{ width: `${(kept / peak) * 100}%` }} />
                      </span>
                      <span className="text-right text-ink-2">{all}</span>
                    </li>
                  );
                })}
              </ul>
              <p className="mt-1.5 text-ink-2" data-testid="depth-slice-counts">
                In the slice: {sliceSum("all")} {gene} molecules, {sliceSum("default")} counted by default, {sliceSum("nucleus_only")} under nucleus-only. Whole box:{" "}
                {profile.totals[gene]?.all ?? 0} with depth, {profile.missing_depth[gene] ?? 0} without.
              </p>
              <p className="mt-1 text-[11px] text-ink-3">Faint bar: all molecules; white: kept under nucleus-only. This does not show that vertical overlap caused a signal.</p>
            </>
          )}
        </section>
      </aside>
    </div>
  );
}
