// Export: download the evidence package once it is ready, with its audit-log chain check and review state.
import type { PackageInfo } from "../contracts/generated";

export function ExportButton({ pkg }: { pkg: PackageInfo | null }) {
  if (!pkg) {
    return (
      <button type="button" disabled className="w-full rounded-md border border-line px-4 py-2 text-sm text-ink-3">
        Evidence package not ready
      </button>
    );
  }
  const chain = pkg.audit_log;
  return (
    <div className="flex flex-col gap-1.5">
      <a
        href={pkg.download_url}
        download
        className="w-full rounded-md bg-accent px-4 py-2 text-center text-sm font-medium text-white hover:brightness-110"
      >
        Download evidence package
      </a>
      <p className="text-xs text-ink-2">
        {pkg.review_state.replaceAll("_", " ")} · audit log {chain.entries} entries,{" "}
        {chain.ok ? "chain verified" : `chain broken at entry ${chain.first_bad_seq}`} · head hash{" "}
        <span className="font-mono">{chain.head_hash?.slice(0, 12) ?? "none"}</span>
      </p>
    </div>
  );
}
