"""Export every contract as one JSON Schema, the input for the web app's generated TypeScript types.

    uv run python -m spatialscout.contracts.schema <out.json>

`npm --prefix web run gen:types` runs this and then json-schema-to-typescript. Schemas use serialization mode
(what the API sends), so fields with defaults are required. Property titles are dropped, otherwise every
property would become its own named TypeScript type.
"""

import inspect
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, TypeAdapter
from pydantic.json_schema import models_json_schema

from . import Contract, Finding, FindingKind, InvestigationEvent, RunMode
from . import __dict__ as _namespace

# Unions and literal aliases that get a named TypeScript type of their own.
NAMED_UNIONS: dict[str, Any] = {
    "InvestigationEvent": InvestigationEvent,
    "Finding": Finding,
    "RunMode": RunMode,
    "FindingKind": FindingKind,
}
REF_TEMPLATE = "#/definitions/{model}"


def contract_models() -> list[type[BaseModel]]:
    """Every contract the package exports, in name order."""
    models = {obj for obj in _namespace.values() if inspect.isclass(obj) and issubclass(obj, Contract) and obj is not Contract}
    return sorted(models, key=lambda model: model.__name__)


def build_schema() -> dict[str, Any]:
    _, top = models_json_schema([(model, "serialization") for model in contract_models()], ref_template=REF_TEMPLATE)
    definitions: dict[str, Any] = dict(top.get("$defs", {}))
    for name, union in NAMED_UNIONS.items():
        schema = TypeAdapter(union).json_schema(mode="serialization", ref_template=REF_TEMPLATE)
        definitions.update(schema.pop("$defs", {}))
        definitions[name] = {**schema, "title": name}
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "SpatialScoutContracts",
        "type": "object",
        "definitions": {name: _tidy(definitions[name], keep_title=True) for name in sorted(definitions)},
    }


def _tidy(node: Any, keep_title: bool = False) -> Any:
    """Drop property titles, and anything beside a `$ref` (draft-07 ignores it, and json2ts would otherwise
    emit a duplicate type such as `ReviewStatus1`)."""
    if isinstance(node, dict):
        if "$ref" in node:
            return {"$ref": node["$ref"]}
        return {key: _tidy(value) for key, value in node.items() if keep_title or key != "title" or not isinstance(value, str)}
    if isinstance(node, list):
        return [_tidy(item) for item in node]
    return node


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: python -m spatialscout.contracts.schema <out.json>", file=sys.stderr)
        return 2
    out = Path(argv[0])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_schema(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(build_schema()['definitions'])} contract schemas to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
