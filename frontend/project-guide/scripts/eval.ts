/**
 * Retrieval evaluation against project-guide/eval/golden.json.
 *
 *   node project-guide/scripts/eval.ts                         # report
 *   node project-guide/scripts/eval.ts --json out.json         # also write machine-readable results
 *   node project-guide/scripts/eval.ts --min-hit5 0.9 --min-refusal 1   # CI gate
 *
 * Metrics: hit@1, hit@3, hit@5 (any chunk from an expected document in the
 * top k), MRR@10, refusal accuracy on off-topic questions, retrieval latency
 * p50/p95/p99 over repeated runs, and index build time.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { performance } from "node:perf_hooks";
import { createRetriever, type KnowledgeBase, type ProjectId } from "../../src/lib/project-guide/core.ts";

interface GoldenCase {
  q: string;
  expect: string[] | "none";
}

const here = dirname(fileURLToPath(import.meta.url));
const frontendDir = resolve(here, "..", "..");

function arg(name: string): string | undefined {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : undefined;
}

function percentile(sorted: number[], p: number): number {
  if (!sorted.length) return 0;
  const idx = Math.min(sorted.length - 1, Math.ceil((p / 100) * sorted.length) - 1);
  return sorted[Math.max(0, idx)];
}

const config = readFileSync(join(frontendDir, "src", "lib", "project-guide", "config.ts"), "utf8");
const homeFromConfig = /homeProject:\s*"(\w+)"/.exec(config)?.[1];
const home = (arg("--home") || homeFromConfig || "fleetflow") as Exclude<ProjectId, "profile">;

const kb = JSON.parse(readFileSync(join(frontendDir, "src", "lib", "project-guide", "knowledge.generated.json"), "utf8")) as KnowledgeBase;
const golden = JSON.parse(readFileSync(join(frontendDir, "project-guide", "eval", "golden.json"), "utf8")) as {
  cases: GoldenCase[];
  holdout?: GoldenCase[];
};

const buildStart = performance.now();
const retriever = createRetriever(kb, { homeProject: home });
const buildMs = performance.now() - buildStart;

interface SetScore {
  answerable: number;
  offTopic: number;
  hitAt1: number;
  hitAt3: number;
  hitAt5: number;
  mrrAt10: number;
  refusalAccuracy: number;
  falseRefusalRate: number;
  failures: string[];
}

function score(cases: GoldenCase[]): SetScore {
  let answerable = 0;
  let hit1 = 0;
  let hit3 = 0;
  let hit5 = 0;
  let mrr = 0;
  let offTopic = 0;
  let refusedCorrectly = 0;
  let falseRefusals = 0;
  const failures: string[] = [];
  for (const c of cases) {
    const r = retriever.search(c.q, [], 10);
    if (c.expect === "none") {
      offTopic++;
      if (!r.confident) refusedCorrectly++;
      else failures.push(`answered off-topic: "${c.q}" (top=${r.topScore.toFixed(2)} ${r.results[0]?.chunk.doc})`);
      continue;
    }
    answerable++;
    if (!r.confident) {
      falseRefusals++;
      failures.push(`refused answerable: "${c.q}" (top=${r.topScore.toFixed(2)})`);
    }
    const expected = new Set(c.expect);
    const rank = r.results.findIndex((x) => expected.has(x.chunk.doc));
    if (rank === 0) hit1++;
    if (rank >= 0 && rank < 3) hit3++;
    if (rank >= 0 && rank < 5) hit5++;
    if (rank >= 0) mrr += 1 / (rank + 1);
    if (rank < 0 || rank >= 5) {
      failures.push(`miss@5: "${c.q}" -> ${r.results.slice(0, 3).map((x) => x.chunk.doc).join(", ")}`);
    }
  }
  const n = Math.max(1, answerable);
  return {
    answerable,
    offTopic,
    hitAt1: hit1 / n,
    hitAt3: hit3 / n,
    hitAt5: hit5 / n,
    mrrAt10: mrr / n,
    refusalAccuracy: offTopic ? refusedCorrectly / offTopic : 1,
    falseRefusalRate: falseRefusals / n,
    failures,
  };
}

const dev = score(golden.cases);
const holdout = score(golden.holdout || []);
const allCases = [...golden.cases, ...(golden.holdout || [])];

// Latency: every golden question, repeated, after one warm-up pass.
const repeats = Number(arg("--repeats") || 20);
for (const c of allCases) retriever.search(c.q);
const timings: number[] = [];
for (let i = 0; i < repeats; i++) {
  for (const c of allCases) {
    const t0 = performance.now();
    retriever.search(c.q);
    timings.push(performance.now() - t0);
  }
}
timings.sort((a, b) => a - b);

const report = {
  homeProject: home,
  corpus: { chunks: retriever.size, vocabulary: retriever.vocabularySize, generatedFrom: kb.generatedFrom },
  dev,
  holdout,
  latencyMs: {
    samples: timings.length,
    p50: percentile(timings, 50),
    p95: percentile(timings, 95),
    p99: percentile(timings, 99),
    max: timings[timings.length - 1],
  },
  indexBuildMs: buildMs,
  environment: { node: process.version, platform: `${process.platform}-${process.arch}` },
};

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
console.log(`Retrieval eval — home=${home}, ${report.corpus.chunks} chunks, ${report.corpus.vocabulary} terms`);
for (const [name, set] of [["dev", dev], ["holdout", holdout]] as const) {
  if (!set.answerable && !set.offTopic) continue;
  console.log(
    `  ${name.padEnd(7)} hit@1 ${pct(set.hitAt1)}  hit@3 ${pct(set.hitAt3)}  hit@5 ${pct(set.hitAt5)}  MRR@10 ${set.mrrAt10.toFixed(3)}  (${set.answerable} answerable) | refusal ${pct(set.refusalAccuracy)} of ${set.offTopic} off-topic, false refusals ${pct(set.falseRefusalRate)}`,
  );
}
console.log(
  `  retrieval latency p50 ${report.latencyMs.p50.toFixed(2)} ms  p95 ${report.latencyMs.p95.toFixed(2)} ms  p99 ${report.latencyMs.p99.toFixed(2)} ms  (n=${timings.length})  index build ${buildMs.toFixed(1)} ms`,
);
const failures = [...dev.failures.map((f) => `[dev] ${f}`), ...holdout.failures.map((f) => `[holdout] ${f}`)];
if (failures.length) {
  console.log("  failures:");
  for (const f of failures) console.log(`   - ${f}`);
}

const jsonOut = arg("--json");
if (jsonOut) writeFileSync(jsonOut, JSON.stringify(report, null, 2) + "\n");

const minHit5 = Number(arg("--min-hit5") || 0);
const minRefusal = Number(arg("--min-refusal") || 0);
const maxFalseRefusal = Number(arg("--max-false-refusal") ?? 1);
let failed = false;
for (const [name, set] of [["dev", dev], ["holdout", holdout]] as const) {
  if (set.answerable && set.hitAt5 < minHit5) {
    console.error(`FAIL ${name} hit@5 ${pct(set.hitAt5)} < ${pct(minHit5)}`);
    failed = true;
  }
  if (set.offTopic && set.refusalAccuracy < minRefusal) {
    console.error(`FAIL ${name} refusal accuracy ${pct(set.refusalAccuracy)} < ${pct(minRefusal)}`);
    failed = true;
  }
  if (set.answerable && set.falseRefusalRate > maxFalseRefusal) {
    console.error(`FAIL ${name} false refusal rate ${pct(set.falseRefusalRate)} > ${pct(maxFalseRefusal)}`);
    failed = true;
  }
}
if (failed) process.exit(1);
