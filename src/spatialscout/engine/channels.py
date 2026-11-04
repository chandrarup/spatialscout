"""Rendered channels: the frozen marker groups the dual-section viewer draws as a multichannel image.

Each molecule channel draws every molecule of its genes (assigned to a cell or not), so the image shows the
tissue as measured, before any assignment condition. The nuclei channel draws each cell's nucleus from the
instrument's segmentation. The viewer colours and blends the channels; this module only says what each draws.
"""

from dataclasses import dataclass

import numpy as np

from ..contracts import ChannelSet, RenderedChannel
from ..data import SectionTables


@dataclass(frozen=True)
class ChannelSpec:
    channel_id: str
    label: str
    genes: tuple[str, ...]
    description: str


NUCLEI = ChannelSpec(
    "nuclei", "Nuclei", (),
    "Each cell's nucleus from the instrument's segmentation, drawn as a disc of the nucleus's area (an approximation).",
)
CHANNELS: tuple[ChannelSpec, ...] = (
    NUCLEI,
    ChannelSpec("nphs1", "NPHS1", ("NPHS1",), "Podocyte marker: glomeruli."),
    ChannelSpec("lrp2_cubn", "LRP2/CUBN", ("LRP2", "CUBN"), "Proximal-tubule markers."),
    ChannelSpec("umod", "UMOD", ("UMOD",), "Thick-ascending-limb marker."),
    ChannelSpec("lymphocyte", "CD3D/CD8A/MS4A1", ("CD3D", "CD8A", "MS4A1"), "T-cell and B-cell markers."),
    ChannelSpec("postn", "POSTN", ("POSTN",), "Periostin: fibroblasts and matrix."),
)


def section_channels(section: SectionTables) -> ChannelSet:
    """Every channel of the section with its molecule count; a channel none of whose genes has a molecule here is
    reported unavailable, with the genes missing."""
    counts = section.molecules["gene"].astype(str).value_counts()
    nuclei = int(np.isfinite(section.cells["nucleus_area"].to_numpy(dtype=float)).sum())
    channels = []
    for spec in CHANNELS:
        if spec is NUCLEI:
            count, missing = nuclei, []
        else:
            count = int(sum(int(counts.get(g, 0)) for g in spec.genes))
            missing = [g for g in spec.genes if int(counts.get(g, 0)) == 0]
        available = count > 0
        reason = None
        if not available:
            reason = "No cell in this section has a detected nucleus." if spec is NUCLEI else f"No {', '.join(spec.genes)} molecule in this section."
        channels.append(
            RenderedChannel(
                channel_id=spec.channel_id,
                label=spec.label,
                source="nuclei" if spec is NUCLEI else "molecules",
                genes=list(spec.genes),
                description=spec.description,
                count=count,
                available=available,
                missing_genes=missing,
                unavailable_reason=reason,
            )
        )
    return ChannelSet(dataset_id=section.dataset_id, section_id=section.section_id, channels=channels)
