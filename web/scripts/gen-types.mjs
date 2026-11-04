// Generate src/contracts/generated.ts from the Pydantic contracts, the single source of truth.
// Usage (from the repo root): npm --prefix web run gen:types
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { compile } from "json-schema-to-typescript";

const webDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(webDir, "..");
const schemaPath = resolve(webDir, "src/contracts/contracts.schema.json");
const typesPath = resolve(webDir, "src/contracts/generated.ts");

execFileSync("uv", ["run", "--project", repoRoot, "python", "-m", "spatialscout.contracts.schema", schemaPath], {
  cwd: repoRoot,
  stdio: "inherit",
});

const schema = JSON.parse(readFileSync(schemaPath, "utf8"));
const types = await compile(schema, "SpatialScoutContracts", {
  additionalProperties: false,
  unreachableDefinitions: true,
  bannerComment:
    "/* Generated from the Pydantic contracts by `npm --prefix web run gen:types`. Do not edit by hand. */",
});
writeFileSync(typesPath, types);
console.log(`wrote ${typesPath}`);
