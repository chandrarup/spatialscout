"""The evidence package's verification notebook (ticket 11), and the same code as a plain script.

It needs only the Python standard library and the unzipped package. It checks the file checksums against the
manifest, the audit log's hash chain and head hash, every claim's cited numbers against the exported artifacts, and
each audit result's arithmetic recomputed from its own counts. The independent recompute from the molecule tables
needs the raw data; RERUN.md says how to run it.
"""

import json

CELLS: list[tuple[str, str]] = [
    (
        "# Verify this evidence package\n\nRun every cell from the unzipped package's folder. Only the Python standard "
        "library is used. Each check prints what it compared and stops with an `AssertionError` at the first mismatch.",
        '''import hashlib
import json
import re
from pathlib import Path

ROOT = Path(".")
manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
claims = json.loads((ROOT / "claims.json").read_text(encoding="utf-8"))
artifacts = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "artifacts").glob("*.json"))}
print(f"investigation {manifest['investigation_id']}, run mode {manifest['run_mode']}: {len(claims)} claims, {len(artifacts)} artifacts")''',
    ),
    (
        "## 1. File checksums\n\nEvery file the manifest lists has the sha256 it records.",
        '''for entry in manifest["files"]:
    digest = hashlib.sha256((ROOT / entry["path"]).read_bytes()).hexdigest()
    assert digest == entry["sha256"], f"{entry['path']} does not match its checksum"
print(f"{len(manifest['files'])} files match their checksums")''',
    ),
    (
        "## 2. Audit log chain\n\nEach entry's hash is the sha256 of its canonical JSON without `entry_hash`, and links to "
        "the entry before it; the last hash is the manifest's head hash.",
        '''def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


head, entries = "0" * 64, 0
for line in (ROOT / "audit_log.jsonl").read_text(encoding="utf-8").splitlines():
    entry = json.loads(line)
    stored = entry.pop("entry_hash")
    assert entry["seq"] == entries + 1 and entry["prev_hash"] == head, f"entry {entries + 1} breaks the chain"
    assert hashlib.sha256(canonical(entry).encode("utf-8")).hexdigest() == stored, f"entry {entries + 1} was edited"
    head, entries = stored, entries + 1
assert head == manifest["audit_log"]["head_hash"], "the log's head hash is not the manifest's"
print(f"audit log: {entries} entries, head hash {head[:16]}... matches the manifest")''',
    ),
    (
        "## 3. Cited numbers\n\nEvery number a claim cites is the value at its source path in the claim's finding or "
        "controls, allowing only the rounding its written precision implies.",
        '''SEGMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(?:\\[([^\\]]+)\\])?$")
ID_FIELDS = ("section_id", "condition", "label_rule_id", "left_out_section_id", "rank")


def split_source(source):
    parts, depth, current = [], 0, ""
    for char in source:
        depth += char == "["
        depth -= char == "]"
        if char == "." and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    return parts + [current]


def resolve(source, finding, controls):
    segments = split_source(source.strip())
    node = finding
    first = SEGMENT.match(segments[0])
    if first and first[1] == "controls":
        node, segments = controls[first[2]], segments[1:]
    for segment in segments:
        if segment == "count" and isinstance(node, list):
            node = len(node)
            continue
        field, key = SEGMENT.match(segment).groups()
        node = node[field]
        if key is not None:
            node = node[key] if isinstance(node, dict) else next(
                item for item in node if any(str(item.get(f)) == key for f in ID_FIELDS if item.get(f) is not None))
    return node


def same_number(cited, actual):
    if cited is None or actual is None:
        return cited is None and actual is None
    text = repr(float(cited)) if isinstance(cited, float) else str(cited)
    decimals = len(text.split(".")[1]) if "." in text and "e" not in text.lower() else 0
    tolerance = 0.5 * 10 ** -decimals if isinstance(cited, float) else 0.0
    return abs(float(cited) - float(actual)) <= tolerance + 1e-12


checked = 0
for claim in claims:
    finding = artifacts[claim["finding"]["finding_id"]]
    controls = {c: artifacts[c] for c in claim["controls"].values() if c}
    for name, number in claim["cited"].items():
        actual = resolve(number["source"], finding, controls)
        assert same_number(number["value"], actual), f"{claim['claim_id']} cites {name} = {number['value']}, the artifact has {actual}"
        checked += 1
print(f"{checked} cited numbers match their artifacts")''',
    ),
    (
        "## 4. Arithmetic recomputed from each audit result's own counts\n\nPer section and condition: the observed share "
        "is cells expressing / cells labelled, retention is molecules / default-condition molecules, and each excess "
        "drop is its expectation minus the observed value. Pooled shares are ratios of sums over the eligible sections.",
        '''def close(a, b):
    return a is None or b is None or abs(a - b) <= 1e-9


recomputed = 0
for artifact in artifacts.values():
    if artifact.get("finding_kind") != "audit":
        continue
    share = artifact["measure"] in ("share_expressing", "gene_set_share_expressing")
    for section in artifact["sections"]:
        rows = {row["condition"]: row for row in section["conditions"]}
        default_molecules = rows.get("default", {}).get("molecules")
        for row in section["conditions"]:
            where = f"{artifact['finding_id']} {section['section_id']} {row['condition']}"
            if share and section["cells_labelled"] and row.get("cells_expressing") is not None:
                assert close(row["observed_value"], row["cells_expressing"] / section["cells_labelled"]), f"observed share, {where}"
            if default_molecules:
                assert close(row["retention"], row["molecules"] / default_molecules), f"retention, {where}"
            for kind in ("home_matched", "cell_matched"):
                if row[f"expectation_{kind}"] is not None and row["observed_value"] is not None:
                    assert close(row[f"excess_drop_{kind}"], row[f"expectation_{kind}"] - row["observed_value"]), f"excess drop, {where}"
            recomputed += 1
    if share:
        eligible = set(artifact["eligible_section_ids"])
        for pooled in artifact["pooled"]:
            pairs = [(s["cells_labelled"], r.get("cells_expressing")) for s in artifact["sections"] if s["section_id"] in eligible
                     for r in s["conditions"] if r["condition"] == pooled["condition"]]
            if pairs and all(e is not None for _, e in pairs) and sum(c for c, _ in pairs):
                assert close(pooled["observed_value"], sum(e for _, e in pairs) / sum(c for c, _ in pairs)), f"pooled {artifact['finding_id']}"
                recomputed += 1
print(f"{recomputed} values recomputed from the artifacts' own counts")''',
    ),
    (
        "## 5. Claims and their recorded statuses",
        '''for claim in claims:
    print(f"{claim['claim_id']} v{claim['version']}: evidence {claim['evidence_status']}, verification "
          f"{claim['verification_status']}, review {claim['review_status']}")
print("every check passed")''',
    ),
]


def notebook() -> str:
    cells = []
    for markdown, code in CELLS:
        cells.append({"cell_type": "markdown", "metadata": {}, "source": markdown.splitlines(keepends=True)})
        cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": code.splitlines(keepends=True)})
    document = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}, "language_info": {"name": "python"}},
        "cells": cells,
    }
    return json.dumps(document, indent=1) + "\n"


def script() -> str:
    header = '"""Verify this evidence package: run `python3 verify_package.py` in its folder (standard library only)."""\n\n'
    return header + "\n\n".join(code for _, code in CELLS) + "\n"
