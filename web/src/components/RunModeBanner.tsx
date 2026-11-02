// The run-mode banner: always says how this investigation's events were produced, and when they were recorded.
import type { ReplayInfo, RunMode } from "../contracts/generated";

const LABELS: Record<RunMode, string> = {
  immutable_replay: "Immutable replay",
  cached_tool_rerun: "Cached tool rerun",
  live: "Live run",
};

const EXPLANATIONS: Record<RunMode, string> = {
  immutable_replay: "recorded events played back verbatim, with their original timestamps",
  cached_tool_rerun: "tools re-run on the current data; model responses come from a recording",
  live: "fresh model calls under the spend budget",
};

export function RunModeBanner({ runMode, replay }: { runMode: RunMode; replay: ReplayInfo | null }) {
  return (
    <div role="status" className="flex flex-wrap items-center gap-x-3 gap-y-1 bg-run-mode px-4 py-1.5 text-sm text-black">
      <strong className="font-semibold uppercase tracking-wide">{LABELS[runMode]}</strong>
      <span>{EXPLANATIONS[runMode]}</span>
      {replay && (
        <span>
          · recorded <time dateTime={replay.recorded_at}>{formatUtc(replay.recorded_at)}</time>
          {replay.origin === "hand_authored" && " · responses hand-authored, no model was called"}
        </span>
      )}
    </div>
  );
}

export function formatUtc(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : `${date.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}
