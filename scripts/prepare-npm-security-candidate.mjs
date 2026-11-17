#!/usr/bin/env node
/** Reproducible, review-first npm remediation candidate. NEVER commits changes. */
import { readFileSync, writeFileSync, mkdirSync, readdirSync } from "node:fs";
import { resolve, join } from "node:path";
const root = resolve("frontend");
const output = resolve(".local/security");
mkdirSync(output, {recursive: true});
for (const file of ["package.json", "package-lock.json"]) {
  writeFileSync(join(output, "baseline-" + file), readFileSync(join(root, file)));
}
const references = [];
function scan(dir) {
  for (const entry of readdirSync(dir, {withFileTypes: true})) {
    const target = join(dir, entry.name);
    if (entry.isDirectory()) scan(target);
    else if (entry.isFile() && /\.(tsx?|mjs|js)$/.test(entry.name)) {
      const source = readFileSync(target, "utf8");
      if (/\b(?:from\s*["']zod(?:\/[^"']*)?["']|require\s*\(\s*["']zod(?:\/[^"']*)?["']\s*\)|import\s*\(\s*["']zod(?:\/[^"']*)?["']\s*\))/.test(source)) {
        references.push(target);
      }
    }
  }
}
scan(join(root, "src"));
scan(join(root, "scripts"));
if (references.length) {
  console.log("ZOD_SOURCE_IMPORTS " + JSON.stringify(references));
  throw Error("Explicit Zod imports found: do not remove without a code migration");
}
const path = join(root, "package.json");
const pkg = JSON.parse(readFileSync(path, "utf8"));
if (pkg.dependencies?.zod) delete pkg.dependencies.zod;
pkg.devDependencies.vitest = "5.1.0";
pkg.devDependencies["@vitest/coverage-v8"] = "5.1.0";
writeFileSync(path, JSON.stringify(pkg, null, 4) + "\n");
console.log("NPM_CANDIDATE_PLAN " + JSON.stringify({
  removedUnusedDirectDependency: "zod",
  vitest: pkg.devDependencies.vitest,
  coverage: pkg.devDependencies["@vitest/coverage-v8"],
  sourceFilesScanned: "frontend/src and frontend/scripts",
  note: "Use package-lock-only npm resolution, no --force, no automatic commits"
}));
