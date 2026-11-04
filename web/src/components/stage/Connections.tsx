// Model access: the three ways an investigation can reach Meta's models, each with its true availability on this
// server (read from /api/mode). Nothing here takes a key: public bring-your-own-key needs session-scoped
// credentials and ownership checks that are not built yet, so the panel says so and points to what works today.
import { useEffect, useRef } from "react";
import type { ModeInfo } from "../../contracts/generated";

interface Choice {
  title: string;
  state: "available" | "unavailable";
  status: string;
  body: string;
}

function choices(mode: ModeInfo | null): Choice[] {
  const modes = mode?.available_run_modes ?? [];
  const recordings = mode?.recordings.length ?? 0;
  const live = modes.includes("live");
  return [
    {
      title: "Recorded demo",
      state: modes.includes("immutable_replay") ? "available" : "unavailable",
      status: modes.includes("immutable_replay") ? "Available · in use" : "Unavailable",
      body: `${recordings} investigation${recordings === 1 ? "" : "s"} recorded live, played back exactly as recorded with their original timestamps. No model is called and nothing is spent.`,
    },
    {
      title: "Sponsored live trial",
      state: "unavailable",
      status: live ? "Owner-only" : "Unavailable",
      body: live
        ? "Live runs are enabled on this server but gated by the owner's passcode and a daily budget; no public trial is open. Recorded investigations and sample-data audits remain available."
        : "Live trial unavailable. Recorded investigations and compatible sample-data audits remain available.",
    },
    {
      title: "Your model connection",
      state: "unavailable",
      status: "Not on the public site yet",
      body: "Public bring-your-own-key needs per-session credentials, private investigations and per-session budgets, which are not built yet. Today, a lab can use its own provider account by running SpatialScout locally with its keys in .env.",
    },
  ];
}

export function Connections({ mode, onClose }: { mode: ModeInfo | null; onClose: () => void }) {
  const dialog = useRef<HTMLDivElement>(null);
  useEffect(() => {
    dialog.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

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
            <p className="mt-1 text-[13px] text-ink-2">How investigations reach Meta's models on this server.</p>
          </div>
          <button type="button" onClick={onClose} className="h-8 rounded-full bg-raised px-3 text-[13px] text-ink hover:bg-[#2a2d32]">
            Close
          </button>
        </div>
        <ul className="mt-5 flex flex-col gap-3">
          {choices(mode).map((c) => (
            <li key={c.title} className="rounded-2xl bg-raised p-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="text-[15px] font-semibold">{c.title}</h3>
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${c.state === "available" ? "bg-[#222a10] text-stable" : "bg-[#24262a] text-ink-2"}`}>{c.status}</span>
              </div>
              <p className="mt-1.5 text-[13px] leading-relaxed text-ink-2">{c.body}</p>
            </li>
          ))}
        </ul>
        <div className="mt-5 rounded-2xl border border-line p-4">
          <p className="text-[13px] font-medium text-ink">Run with your own keys today</p>
          <pre className="mt-2 overflow-x-auto rounded-xl bg-black/40 p-3 font-mono text-[12px] leading-relaxed text-ink-2">
            {`git clone https://github.com/chandrarup/spatialscout
cd spatialscout && make install
# .env: your Meta, Baseten and Fireworks keys, plus
# SPATIALSCOUT_LIVE_PASSCODE and SPATIALSCOUT_DAILY_BUDGET_USD
make serve

# start a live run (the passcode goes in a header, never the URL)
curl -X POST http://127.0.0.1:8000/api/investigations \\
  -H "X-Live-Passcode: $SPATIALSCOUT_LIVE_PASSCODE" \\
  -H "Content-Type: application/json" \\
  -d '{"question": "…", "run_mode": "live"}'
# then open http://127.0.0.1:8000/#<investigation_id>`}
          </pre>
          <p className="mt-2 text-[12px] leading-relaxed text-ink-3">
            Your keys stay on your machine; the budget you set is enforced under a file lock. The web page itself does not start live runs yet.
          </p>
        </div>
      </div>
    </div>
  );
}
