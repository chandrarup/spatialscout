"""Tissue geometry contracts: structure masks and the region view the viewer draws."""

from typing import Literal

from .base import SCHEMA_VERSION, Contract


class StructureMask(Contract):
    """The outline of one structure in section coordinates (micrometres), as a closed polygon.

    `source` says where the outline came from: drawn by construction in a synthetic fixture, or proposed
    by SAM 3.1 from a box prompt (ADR-0005), which the UI must label as a proposal.
    """

    schema_version: str = SCHEMA_VERSION
    structure_id: str
    section_id: str
    kind: Literal["glomerulus"]
    outline: list[list[float]]
    source: Literal["synthetic", "sam-3.1"]
