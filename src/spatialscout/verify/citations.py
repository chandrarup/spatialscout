"""Cited-number sources: the field path a claim gives for each number it uses, resolved in the cited artifacts.

Grammar (dot-separated segments, each a field name with an optional `[key]` selector):

- `sections[SYN-01].conditions[nucleus_only].retention`: a list element is chosen by its id field
  (`section_id`, `condition`, `label_rule_id`, `left_out_section_id` or `rank`);
- `pooled[distance_cap_1um].observed_value`, `sections[GSM8720409].cells_labelled`;
- `eligible_section_ids.count`: `count` after a list gives its length;
- `controls[ctl-…].arms[full-panel-v1].cells_labelled`: a path inside one of the claim's controls.

The claim-drafting gate (ticket 09a) uses this to check that every cited number is the artifact's own value. The
independent recompute (ticket 10) checks the values against the molecule tables.
"""

import math
import re
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

_SEGMENT = re.compile(r"^(?P<field>[A-Za-z_][A-Za-z0-9_]*)(?:\[(?P<key>[^\]]+)\])?$")
_ID_FIELDS = ("section_id", "condition", "label_rule_id", "left_out_section_id", "rank")


class UnresolvedSource(LookupError):
    """A cited source that names no number in the cited artifacts."""


def split_source(source: str) -> list[str]:
    """Split on dots outside brackets, so keys such as `ctl-…` or `1.5` stay whole."""
    parts, depth, current = [], 0, ""
    for char in source:
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
        if char == "." and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    parts.append(current)
    return parts


def resolve_source(source: str, finding: BaseModel, controls: Mapping[str, BaseModel] | None = None) -> Any:
    """The value at `source` in the finding, or in a control when the path starts with `controls[<id>]`."""
    segments = split_source(source.strip())
    node: Any = finding
    first = _SEGMENT.match(segments[0])
    if first and first["field"] == "controls":
        if not first["key"] or first["key"] not in (controls or {}):
            raise UnresolvedSource(f"{source}: names no control this claim cites")
        node, segments = (controls or {})[first["key"]], segments[1:]
    for segment in segments:
        node = _step(node, segment, source)
    if isinstance(node, BaseModel | list | dict):
        raise UnresolvedSource(f"{source}: names a group of values, not one number")
    return node


def _step(node: Any, segment: str, source: str) -> Any:
    if segment == "count" and isinstance(node, list):
        return len(node)
    match = _SEGMENT.match(segment)
    if match is None:
        raise UnresolvedSource(f"{source}: cannot read segment {segment!r}")
    field, key = match["field"], match["key"]
    if isinstance(node, BaseModel):
        if field not in type(node).model_fields:
            raise UnresolvedSource(f"{source}: there is no field {field!r}")
        node = getattr(node, field)
    elif isinstance(node, dict) and field in node:
        node = node[field]
    else:
        raise UnresolvedSource(f"{source}: there is no field {field!r}")
    if key is None:
        return node
    if isinstance(node, dict):
        if key not in node:
            raise UnresolvedSource(f"{source}: no {field} entry {key!r}")
        return node[key]
    if isinstance(node, list):
        for item in node:
            for id_field in _ID_FIELDS:
                value = getattr(item, id_field, None)
                if value is not None and str(getattr(value, "value", value)) == key:
                    return item
        raise UnresolvedSource(f"{source}: no {field} entry {key!r}")
    raise UnresolvedSource(f"{source}: {field} has no entries to select from")


def same_number(cited: float | int | None, actual: Any) -> bool:
    """Whether a cited value is the artifact's value, allowing the rounding its written precision implies (0.76 for
    0.7612; 21 for 21). A missing value matches only a missing value."""
    if cited is None or actual is None:
        return cited is None and actual is None
    if isinstance(actual, bool) or not isinstance(actual, int | float):
        return False
    if isinstance(cited, float) and not math.isfinite(cited):
        return False
    text = repr(float(cited)) if isinstance(cited, float) else str(cited)
    decimals = len(text.split(".")[1]) if "." in text and "e" not in text.lower() else 0
    tolerance = 0.5 * 10**-decimals if isinstance(cited, float) else 0.0
    return abs(float(cited) - float(actual)) <= tolerance + 1e-12
