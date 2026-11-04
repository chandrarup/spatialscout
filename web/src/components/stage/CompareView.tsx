// Two KPMP participants one above the other, each on its side, with the same proteins switched on. They are two
// different people, so nothing links a place on one to a place on the other; each strip carries its own computed
// whole-image protein audit.
import { useEffect, useState } from "react";
import type { KpmpManifest, ProteinAuditResult } from "../../contracts/generated";
import type { DatasetAdapter, LoadedSection } from "../../datasets/adapter";
import { KPMP_COLOURS } from "../../datasets/kpmp";
import { CodexView } from "./CodexView";
import { pct } from "./Explore";
import { labelTone } from "./RunCanvas";

interface Props {
  adapter: DatasetAdapter;
  kpmp: KpmpManifest;
  onOpen: (participantId: string) => void;
  onBack: () => void;
  /** The earlier side-by-side viewer, which also opens the Xenium sections with SAM 3.1 outlines. */
  onClassic: () => void;
}

function Strip({ adapter, participantId, role, cells, visible, onOpen }: { adapter: DatasetAdapter; participantId: string; role: string; cells: number; visible: ReadonlySet<string>; onOpen: () => void }) {
  const [section, setSection] = useState<LoadedSection | null>(null);
  const [audit, setAudit] = useState<ProteinAuditResult[] | null>(null);
  useEffect(() => {
    adapter.load(participantId).then(setSection).catch(() => setSection(null));
    adapter.proteinAudit?.(participantId, null).then(setAudit).catch(() => setAudit(null));
  }, [adapter, participantId]);
  return (
    <section aria-label={`Participant ${participantId}`} data-testid={role === "healthy reference" ? "provenance-left" : "provenance-right"} className="relative min-h-0 flex-1 overflow-hidden rounded-3xl bg-black">
      {section && <CodexView section={section} visible={visible} fill={1.6} />}
      <div className="pointer-events-none absolute inset-x-3 top-3 flex flex-wrap items-start justify-between gap-2">
        <div className="pointer-events-auto rounded-2xl bg-[#16171b]/95 ring-1 ring-white/[0.06] px-3.5 py-2.5">
          <p className="text-[15px] font-semibold">
            {participantId}{" "}
            <span className={`ml-1 rounded-full px-2 py-0.5 text-[12px] font-medium ${role === "healthy reference" ? "bg-[#222a10] text-stable" : "bg-[#2b2414] text-sensitive"}`}>{role}</span>
          </p>
          <p className="mt-0.5 text-[12px] text-ink-3">Kidney biopsy · CODEX · {cells.toLocaleString()} cells · real microscopy, KPMP</p>
        </div>
        <div className="pointer-events-auto flex flex-wrap items-center gap-1.5 rounded-2xl bg-[#16171b]/95 ring-1 ring-white/[0.06] px-3 py-2">
          {audit?.map((r) => (
            <span key={r.result_id} data-testid="protein-audit-result" data-label={r.label} className="flex items-center gap-1.5 text-[12px] text-ink-2" title={r.inference}>
              {r.marker} in {r.population}+ {pct(r.conditions[0]?.observed_share ?? null)}
              <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${labelTone(r.label)}`}>{r.label.replaceAll("_", " ")}</span>
            </span>
          ))}
          <button type="button" onClick={onOpen} className="ml-1 h-7 rounded-full bg-white px-3 text-[12px] font-medium text-black">
            Open
          </button>
        </div>
      </div>
    </section>
  );
}

export function CompareView({ adapter, kpmp, onOpen, onBack, onClassic }: Props) {
  const ordered = [...kpmp.participants].sort((a, b) => (a.role === "healthy reference" ? -1 : b.role === "healthy reference" ? 1 : 0));
  const channels = kpmp.participants[0]?.channels ?? [];
  const [visible, setVisible] = useState<Set<string>>(() => new Set(channels.map((c) => c.channel_id).filter((id) => !adapter.defaultHidden?.has(id))));
  return (
    <div className="flex h-full flex-col gap-3 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-[20px] font-semibold tracking-tight">Healthy reference above, diseased below</h1>
          <p className="text-[13px] text-ink-3">Two different people. Drag and zoom each strip on its own; the proteins switch on and off together.</p>
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
          <button type="button" onClick={onClassic} className="ml-2 h-8 rounded-full px-3 text-[13px] text-ink-2 underline decoration-ink-3 underline-offset-4 hover:text-ink">
            Xenium viewer with SAM outlines
          </button>
          <button type="button" onClick={onBack} className="ml-2 h-8 rounded-full bg-raised px-3 text-[13px] text-ink hover:bg-[#2a2d32]">
            Back to one biopsy
          </button>
        </div>
      </div>
      {ordered.map((p) => (
        <Strip key={p.participant_id} adapter={adapter} participantId={p.participant_id} role={p.role} cells={p.cells} visible={visible} onOpen={() => onOpen(p.participant_id)} />
      ))}
    </div>
  );
}
