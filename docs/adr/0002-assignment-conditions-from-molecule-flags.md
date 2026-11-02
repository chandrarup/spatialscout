# Assignment conditions come from molecule flags, not re-segmentation

GSE286184 deposits molecules with `cell_id`, `overlaps_nucleus` and `nucleus_distance`, but no cell or nucleus boundaries and no images. So SpatialScout compares assignment conditions derived from those flags (default, nucleus-only, distance caps, and a structure-constrained condition from structure masks) instead of re-segmenting with Proseg, Cellpose-SAM or cellAdmix, all of which need inputs or runtimes we do not have. Every condition is a subset of the default molecules, so pseudobulk counts stay integers; that satisfies a count model's input format, not its independence assumptions (see ADR-0007). Cell type labels are assigned once from default counts and frozen, so a changed effect is attributable to assignment rather than relabelling.

## Considered options

- Re-segmentation with published tools: rejected for the hackathon. They need boundaries, images or an R runtime, and a comparison across them would dominate the build. Kept on the roadmap.
- Reassigning excluded molecules to a neighbour: rejected for now. Without boundaries the target cell is a guess, and dropping is the conservative, explainable choice.
