// Export: download the evidence package once it is ready, with its audit-log chain check and review state.
import type { PackageInfo } from "../contracts/generated";

export function ExportButton({ pkg }: { pkg: PackageInfo | null }) {
  if (!pkg) {
    return (
      <button type="button" disabled className="h-11 rounded-full bg-raised px-6 text-[15px] text-ink-3">
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
        className="inline-flex h-11 items-center justify-center rounded-full bg-white px-6 text-center text-[15px] font-medium text-black transition-transform active:scale-95"
      >
        Download evidence package
      </a>
      <p className="text-xs text-ink-2">
        {pkg.review_state === "reviewed" ? "Reviewed by a researcher" : "Not yet reviewed by a researcher"} · audit log {chain.entries} entries,{" "}
        {chain.ok ? "chain verified" : `chain broken at entry ${chain.first_bad_seq}`} · head hash{" "}
        <span className="font-mono">{chain.head_hash?.slice(0, 12) ?? "none"}</span>
      </p>
    </div>
  );
}
