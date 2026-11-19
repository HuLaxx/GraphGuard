#!/usr/bin/env node
/** Print machine-parseable, inspectable npm lock deltas into CI logs. */
import {readFileSync} from "node:fs";
import {resolve} from "node:path";
const before = resolve(".local/security");
const originalPackage = JSON.parse(readFileSync(before + "/baseline-package.json", "utf8"));
const originalLock = JSON.parse(readFileSync(before + "/baseline-package-lock.json", "utf8"));
const currentPackage = JSON.parse(readFileSync("frontend/package.json", "utf8"));
const currentLock = JSON.parse(readFileSync("frontend/package-lock.json", "utf8"));
if (currentLock.lockfileVersion !== 3 || originalLock.lockfileVersion !== 3)
  throw Error("Unsupported npm lockfile format");
if (currentLock.name !== originalLock.name)
  throw Error("Root package identity changed");
const keys = [...new Set([
  ...Object.keys(originalLock.packages),
  ...Object.keys(currentLock.packages),
])].sort();
let changed = 0, added = 0, removed = 0;
console.log("GG_PATCH_PACKAGE " + JSON.stringify(currentPackage));
for (const key of keys) {
  const a = originalLock.packages[key];
  const b = currentLock.packages[key];
  if (JSON.stringify(a) === JSON.stringify(b)) continue;
  changed++;
  if (a === undefined) added++;
  if (b === undefined) removed++;
  // One record per changed package; never emit auth tokens or local secrets.
  console.log("GG_LOCK_PATCH_RECORD " + JSON.stringify({key, value: b ?? null}));
}
console.log("GG_PATCH_STATS " + JSON.stringify({
  changed, added, removed,
  originalPackages: Object.keys(originalLock.packages).length,
  updatedPackages: Object.keys(currentLock.packages).length,
  previousZod: originalPackage.dependencies.zod ?? null,
  nextZod: currentPackage.dependencies.zod ?? null,
  vitest: currentPackage.devDependencies.vitest,
  coverage: currentPackage.devDependencies["@vitest/coverage-v8"],
}));
