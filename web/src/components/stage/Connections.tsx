// Model access: how the next investigation reaches Meta's models, chosen here, with each option's true availability on
// this server (read from /api/mode). Recorded investigations replay what was recorded and call nothing. The live
// trial runs on the server's keys under a small daily budget. Your own keys stay in this tab's memory, are sent only
// with the request that starts your run, and are never stored by the server.
import { useEffect, useRef, useState } from "react";
import type { LiveConnection } from "../../api";
import type { ModeInfo } from "../../contracts/generated";

interface Props {
  mode: ModeInfo | null;
  connection: LiveConnection;
  onConnection: (connection: LiveConnection) => void;
  onClose: () => void;
}

const MAX_CAP = 5;

export function Connections({ mode, connection, onConnection, onClose }: Props) {
  const dialog = useRef<HTMLDivElement>(null);
  const [meta, setMeta] = useState(connection.kind === "byok" ? connection.keys.meta : "");
  const [baseten, setBaseten] = useState(connection.kind === "byok" ? (connection.keys.baseten ?? "") : "");
  const [fireworks, setFireworks] = useState(connection.kind === "byok" ? (connection.keys.fireworks ?? "") : "");
  const [cap, setCap] = useState(connection.kind === "byok" ? connection.capUsd : 1);
  useEffect(() => {
    dialog.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const access = mode?.live_access ?? [];
  const recordings = mode?.recordings.length ?? 0;
  const trialOpen = access.includes("trial");
  const byokOpen = access.includes("byok");
  const byokReady = meta.trim().length > 0 && (baseten.trim().length > 0 || fireworks.trim().length > 0) && cap > 0 && cap <= MAX_CAP;
  const chosen = connection.kind;
  const badge = (on: boolean, text: string) => (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${on ? "bg-[#222a10] text-stable" : "bg-[#24262a] text-ink-2"}`}>{text}</span>
  );
  const input = "h-9 w-full rounded-xl border border-line bg-black/30 px-3 font-mono text-[12px] text-ink placeholder:text-ink-3";

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4" onClick={onClose}>
      <div
        ref={dialog}
        role="dialog"
        aria-modal="true"
        aria-label="Connections"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        className="max-h-[90vh] w-full max-w-[640px] overflow-y-auto rounded-3xl bg-panel p-6 shadow-[0_16px_50px_rgb(0_0_0/0.6)] ring-1 ring-white/[0.08] outline-none"
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-[20px] font-semibold">Connections</h2>
            <p className="mt-1 text-[13px] text-ink-2">Choose how your next investigation reaches Meta's models.</p>
          </div>
          <button type="button" onClick={onClose} className="h-8 rounded-full bg-raised px-3 text-[13px] text-ink hover:bg-[#2a2d32]">
            Close
          </button>
        </div>
        <p className="mt-4 rounded-2xl bg-raised p-4 text-[13px] leading-relaxed text-ink-2">
          <span className="font-medium text-ink">New here? Start with the recorded demo.</span> Follow the featured investigation end to end, then ask your
          own question — recorded questions replay instantly, and anything else gets a data check with sample-data and public-dataset routes.
        </p>
        <ul className="mt-5 flex flex-col gap-3" role="radiogroup" aria-label="Model connection">
          <li className={`rounded-2xl bg-raised p-4 ring-1 ${chosen === "recorded" ? "ring-white/60" : "ring-transparent"}`}>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="text-[15px] font-semibold">Recorded demo</h3>
              {badge(true, chosen === "recorded" ? "In use" : "Available")}
            </div>
            <p className="mt-1.5 text-[13px] leading-relaxed text-ink-2">
              {recordings} investigation{recordings === 1 ? "" : "s"} recorded live, played back exactly as recorded with their original timestamps. No model is called and nothing is spent. Only the recorded questions can be asked.
            </p>
            <button type="button" role="radio" aria-checked={chosen === "recorded"} onClick={() => onConnection({ kind: "recorded" })} className="mt-3 h-8 rounded-full bg-white px-3 text-[12px] font-medium text-black disabled:opacity-50" disabled={chosen === "recorded"}>
              Use recordings
            </button>
          </li>
          <li className={`rounded-2xl bg-raised p-4 ring-1 ${chosen === "trial" ? "ring-white/60" : "ring-transparent"}`}>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="text-[15px] font-semibold">Live trial</h3>
              {badge(trialOpen, trialOpen ? (chosen === "trial" ? "In use" : `Open · $${(mode?.trial_remaining_usd ?? 0).toFixed(2)} left today`) : "Not open on this server")}
            </div>
            <p className="mt-1.5 text-[13px] leading-relaxed text-ink-2">
              Ask any question about the GSE286184 kidney sections. The models are called live on this server's account, under a shared daily trial budget; you approve the plan before any analysis runs. A run costs roughly $0.30.
            </p>
            <button type="button" role="radio" aria-checked={chosen === "trial"} disabled={!trialOpen || chosen === "trial"} onClick={() => onConnection({ kind: "trial" })} className="mt-3 h-8 rounded-full bg-white px-3 text-[12px] font-medium text-black disabled:opacity-50">
              Use the live trial
            </button>
          </li>
          <li className={`rounded-2xl bg-raised p-4 ring-1 ${chosen === "byok" ? "ring-white/60" : "ring-transparent"}`}>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="text-[15px] font-semibold">Your own keys</h3>
              {badge(byokOpen, chosen === "byok" ? "In use" : byokOpen ? "Available" : "Unavailable")}
            </div>
            <p className="mt-1.5 text-[13px] leading-relaxed text-ink-2">
              Live runs on your provider accounts. Meta (Muse Wonder, Muse Spark) is required, plus Baseten or Fireworks (Muse Spark Open drafts the claims). Keys stay in this tab's memory and are sent only with the request that starts your run; the server holds them in memory for that run, never writes them to disk, events or logs, and forgets them on restart. Your cap stops the run's spending.
            </p>
            <div className="mt-3 grid gap-2">
              <input aria-label="Meta API key" type="password" autoComplete="off" placeholder="Meta API key (required)" value={meta} onChange={(e) => setMeta(e.target.value)} className={input} />
              <input aria-label="Baseten API key" type="password" autoComplete="off" placeholder="Baseten API key" value={baseten} onChange={(e) => setBaseten(e.target.value)} className={input} />
              <input aria-label="Fireworks API key" type="password" autoComplete="off" placeholder="Fireworks API key (Baseten or Fireworks)" value={fireworks} onChange={(e) => setFireworks(e.target.value)} className={input} />
              <label className="flex items-center gap-2 text-[12px] text-ink-2">
                Spend cap for the run (USD, up to ${MAX_CAP})
                <input aria-label="Spend cap (USD)" type="number" min={0.1} max={MAX_CAP} step={0.1} value={cap} onChange={(e) => setCap(Number(e.target.value))} className="h-8 w-20 rounded-lg border border-line bg-black/30 px-2 text-ink" />
              </label>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                role="radio"
                aria-checked={chosen === "byok"}
                disabled={!byokOpen || !byokReady}
                onClick={() =>
                  onConnection({ kind: "byok", keys: { meta: meta.trim(), ...(baseten.trim() ? { baseten: baseten.trim() } : {}), ...(fireworks.trim() ? { fireworks: fireworks.trim() } : {}) }, capUsd: cap })
                }
                className="h-8 rounded-full bg-white px-3 text-[12px] font-medium text-black disabled:opacity-50"
              >
                Use my keys
              </button>
              {chosen === "byok" && (
                <button
                  type="button"
                  onClick={() => {
                    setMeta("");
                    setBaseten("");
                    setFireworks("");
                    onConnection({ kind: "recorded" });
                  }}
                  className="h-8 rounded-full bg-raised px-3 text-[12px] text-ink ring-1 ring-line hover:bg-[#2a2d32]"
                >
                  Forget my keys
                </button>
              )}
            </div>
          </li>
        </ul>
        <p className="mt-4 text-[12px] leading-relaxed text-ink-3">
          With a live connection, questions that match a recording still run live (fresh calls, labelled "Live run"). Every live run proposes a plan you approve first, and every number it shows is computed by the analysis engine. Running locally with your keys in .env also works: <span className="font-mono">make serve</span>.
        </p>
      </div>
    </div>
  );
}
