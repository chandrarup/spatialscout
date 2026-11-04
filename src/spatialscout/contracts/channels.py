"""Rendered channels: the multichannel image the dual-section viewer draws, rendered from a section's molecules
(and, for the nuclei channel, from its cells' nuclei). Nothing here is a microscope image."""

from typing import Literal

from pydantic import Field

from .base import SCHEMA_VERSION, Contract
from .finding import Region


class RenderedChannel(Contract):
    """One channel of a section: which molecules (or nuclei) it draws, and whether the section has any."""

    channel_id: str
    label: str
    source: Literal["molecules", "nuclei"]
    genes: list[str] = Field(description="The genes whose molecules the channel draws; empty for the nuclei channel.")
    description: str
    count: int = Field(description="Molecules of the channel's genes in the section, assigned or not; for nuclei, cells with a detected nucleus.")
    available: bool
    missing_genes: list[str] = Field(description="The channel's genes with no molecule in the section.")
    unavailable_reason: str | None = None


class ChannelSet(Contract):
    """Every rendered channel of one section, in a fixed order."""

    schema_version: str = SCHEMA_VERSION
    dataset_id: str
    section_id: str
    provenance: Literal["rendered from molecules"] = "rendered from molecules"
    channels: list[RenderedChannel]


class RecordedBoxes(Contract):
    """Boxes on a section whose SAM 3.1 box-prompt response is stored, so a cached tool rerun can outline them
    without a model call. Any other box needs a live run."""

    section_id: str
    boxes: list[Region]
