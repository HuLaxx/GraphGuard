#!/usr/bin/env node
/**
 * Print a deterministic, sanitized npm advisory inventory from npm audit JSON.
 * This diagnostic script does not silently waive high/critical findings.
 * Usage: node scripts/print-npm-audit.mjs <report.json> <full|production>
 */
import { readFileSync } from "node:fs";

const path = process.argv[2];
const scope = process.argv[3] ?? "unknown";
if (!path) throw new Error("Expected npm audit JSON report path");
const data = JSON.parse(readFileSync(path, "utf8"));
if (!data?.metadata?.vulnerabilities || !data?.vulnerabilities) {
  throw new Error("No npm advisory metadata; audit could not be trusted");
}
const counts = data.metadata.vulnerabilities;
console.log("NPM_AUDIT_SCOPE " + scope);
console.log("NPM_AUDIT_TOTAL " + counts.total);
console.log("NPM_AUDIT_COUNTS " + JSON.stringify({
  critical: counts.critical ?? 0,
  high: counts.high ?? 0,
  moderate: counts.moderate ?? 0,
  low: counts.low ?? 0,
  info: counts.info ?? 0
}));
const bySeverity = { critical: 0, high: 1, moderate: 2, low: 3, info: 4 };
for (const [name, info] of Object.entries(data.vulnerabilities).sort(
  ([nameA, a], [nameB, b]) =>
    (bySeverity[a.severity] ?? 99) - (bySeverity[b.severity] ?? 99) ||
    nameA.localeCompare(nameB)
)) {
  const via = (info.via ?? []).map((value) => typeof value === "string"
    ? { through: value }
    : {
      name: value.name,
      title: value.title,
      advisory: value.url,
      vulnerableVersions: value.range,
    }
  );
  console.log("NPM_AUDIT_FINDING " + JSON.stringify({
    name, severity: info.severity, direct: info.isDirect,
    vulnerableRange: info.range,
    installed: (info.nodes ?? []).map(node => node.replace(/^node_modules\//, "")),
    fixAvailable: info.fixAvailable, effects: info.effects ?? [], via
  }));
}
if (data.error) throw new Error("npm audit returned an error: " + String(data.error.code));
