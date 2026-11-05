// How the verifier scores on valid and deliberately altered claims, from the committed benchmark results. Both
// sides are shown: what it caught and what it wrongly flagged, with the figure-read check named as the source of
// the false flags. Renders nothing when the dataset has no committed benchmark.
import { useEffect, useState } from "react";
import { api } from "../api";
import type { VerificationBenchmark } from "../contracts/generated";

export function BenchmarkCard({ datasetId }: { datasetId: string }) {
  const [bench, setBench] = useState<VerificationBenchmark | null>(null);
  useEffect(() => {
    let live = true;
    api
      .verificationBenchmark(datasetId)
      .then((b) => live && setBench(b))
      .catch(() => live && setBench(null));
    return () => {
      live = false;
    };
  }, [datasetId]);
  if (!bench) return null;
  return (
    <section aria-label="Verifier benchmark" className="rounded-3xl bg-raised p-5">
      <h3 className="text-[16px] font-semibold">How well does the verifier work?</h3>
      <p className="mt-1 text-[13px] text-ink-3">
        {bench.valid_claims} valid and {bench.injected_claims} deliberately altered claims, each put through the same three checks.
      </p>
      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
        <div>
          <p className="text-[28px] leading-none font-semibold tracking-tight tabular-nums">
            {bench.injected_caught} <span className="text-[16px] font-normal text-ink-2">of {bench.injected_claims}</span>
          </p>
          <p className="mt-1 text-[13px] text-ink-2">altered claims caught by at least one check</p>
        </div>
        <div>
          <p className="text-[28px] leading-none font-semibold tracking-tight tabular-nums">
            {bench.valid_flagged} <span className="text-[16px] font-normal text-ink-2">of {bench.valid_claims}</span>
          </p>
          <p className="mt-1 text-[13px] text-ink-2">
            valid claims flagged{bench.valid_flagged_visual_only === bench.valid_flagged && bench.valid_flagged > 0 ? ", all by the figure-read check alone" : ""};
            flagged claims stay visible for review
          </p>
        </div>
      </div>
    </section>
  );
}
