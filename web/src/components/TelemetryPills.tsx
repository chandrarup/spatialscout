// Telemetry pills: one per provider that handled a model call in this investigation, summed from its model_call
// events. Each pill says which models ran, how many calls were live or stored, tokens, latency and live spend.
import type { InvestigationEvent, ModelCallRecord } from "../contracts/generated";

const PROVIDER_NAMES: Record<ModelCallRecord["provider"], string> = {
  meta: "Meta Model API",
  baseten: "Baseten",
  fireworks: "Fireworks",
};

interface ProviderTotals {
  provider: ModelCallRecord["provider"];
  models: Set<string>;
  live: number;
  stored: number;
  failed: number;
  failovers: number;
  tokens: number;
  latencyMs: number;
  costUsd: number;
}

export function TelemetryPills({ events }: { events: InvestigationEvent[] }) {
  const totals = new Map<string, ProviderTotals>();
  for (const event of events) {
    if (event.type !== "model_call") continue;
    const call = event.call;
    const provider = call.served_by ?? call.provider;
    const entry = totals.get(provider) ?? {
      provider,
      models: new Set<string>(),
      live: 0,
      stored: 0,
      failed: 0,
      failovers: 0,
      tokens: 0,
      latencyMs: 0,
      costUsd: 0,
    };
    entry.models.add(call.model);
    if (call.source === "live") entry.live += 1;
    else entry.stored += 1;
    if (call.error_code) entry.failed += 1;
    if (call.failover_from) entry.failovers += 1;
    entry.tokens += (call.usage?.prompt_tokens ?? 0) + (call.usage?.completion_tokens ?? 0);
    entry.latencyMs += call.latency_ms;
    entry.costUsd += call.estimated_cost_usd ?? 0;
    totals.set(provider, entry);
  }
  if (totals.size === 0) return null;
  return (
    <ul aria-label="Model telemetry by provider" className="flex flex-wrap gap-2">
      {[...totals.values()].map((t) => (
        <li
          key={t.provider}
          title={[...t.models].join(", ")}
          className="flex items-center gap-2 rounded-full border border-line bg-raised px-3 py-1 text-xs text-ink-2"
        >
          <strong className="font-semibold text-ink">{PROVIDER_NAMES[t.provider]}</strong>
          <span>{[...t.models].join(", ")}</span>
          <span className="text-ink-3">
            {describe(t)}
          </span>
        </li>
      ))}
    </ul>
  );
}

function describe(t: ProviderTotals): string {
  const parts = [];
  if (t.live) parts.push(`${t.live} live`);
  if (t.stored) parts.push(`${t.stored} stored`);
  if (t.failed) parts.push(`${t.failed} failed`);
  if (t.failovers) parts.push(`${t.failovers} via failover`);
  if (t.tokens) parts.push(`${t.tokens.toLocaleString()} tokens`);
  parts.push(`${(t.latencyMs / 1000).toFixed(1)} s`);
  if (t.costUsd) parts.push(`$${t.costUsd.toFixed(4)}`);
  return parts.join(" · ");
}
