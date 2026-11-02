# Disease contrasts are descriptive in this release

GSE286184 has 22 sections from 19 donors and GEO does not map sections to donors; DKD, MCD and MN each contain a repeated donor. Control (3 sections, 3 patients) and IgAN (4, 4) are donor-distinct only by arithmetic on the paper's published counts, unconfirmed by metadata. So every contrast reports per-section library-size-normalised log2 values, an effect per assignment condition and leave-one-section-out influence, with `inference_eligibility: descriptive_only`, and no p-values or confidence intervals that assume independent sections. PyDESeq2 leaves the primary path; integer molecule counts satisfy its input format but not its independence assumption. Donor identity is never inferred from expression similarity.

## Consequences

- The independent recompute can reproduce every cited number, since no fitted model is involved.
- The capability report records IgAN vs Control as "conditionally donor-distinct by published counts, unconfirmed"; inferential contrasts move to the roadmap pending donor metadata.
