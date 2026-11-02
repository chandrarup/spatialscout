# Every number on screen is computed; injected errors are labelled

The PRD scripted headline results before any analysis ran ("34.2% → 3.8% contamination", "≥30% of top hits are artifacts", a podocyte CD3D claim that "vanishes"). The de-risking spikes on GSE286184 show a different, real picture: most DKD-vs-control effects are stable across assignment conditions, a few are segmentation-sensitive, and many have insufficient evidence. We show only numbers produced by the analysis engine from the stored data, label every finding with its evidence label rather than "artifact", and demonstrate verification with injected errors that the interface always marks as injected. Judges who probe the demo should find it holds up; a scripted result would not.

## Consequences

- The demo narrative is written after the analysis, from its outputs. It must work whether a given finding is stable or sensitive.
- The UI never hard-codes a metric. A missing value is shown as missing with its reason.
