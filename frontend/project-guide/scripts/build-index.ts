/**
 * Builds src/lib/project-guide/knowledge.generated.json from project-guide/corpus.
 *
 *   node project-guide/scripts/build-index.ts          # write the index
 *   node project-guide/scripts/build-index.ts --check  # fail if the committed index is stale
 *
 * Output is deterministic (no timestamps) so CI can detect drift.
 */
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chunkMarkdown, deriveTitle, type KnowledgeBase, type KnowledgeChunk, type ProjectId } from "../../src/lib/project-guide/core.ts";

interface ManifestEntry {
  file: string;
  project: ProjectId;
  source: string;
  url: string;
}

const here = dirname(fileURLToPath(import.meta.url));
const frontendDir = resolve(here, "..", "..");
const corpusDir = join(frontendDir, "project-guide", "corpus");
const outPath = join(frontendDir, "src", "lib", "project-guide", "knowledge.generated.json");

export function buildKnowledgeBase(): KnowledgeBase {
  const manifest = JSON.parse(readFileSync(join(corpusDir, "manifest.json"), "utf8")) as {
    commits: Record<string, string>;
    entries: ManifestEntry[];
  };
  const chunks: KnowledgeChunk[] = [];
  for (const entry of manifest.entries) {
    const md = readFileSync(join(corpusDir, entry.file), "utf8");
    const title = deriveTitle(md, entry.file, entry.project);
    chunks.push(...chunkMarkdown(md, { project: entry.project, doc: entry.file, url: entry.url, title }));
  }
  const commits = Object.entries(manifest.commits)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([p, sha]) => `${p}@${sha}`)
    .join(" ");
  return { version: 1, generatedFrom: `${manifest.entries.length} documents; ${commits}`, chunks };
}

const isMain = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const kb = buildKnowledgeBase();
  const json = JSON.stringify(kb) + "\n";
  if (process.argv.includes("--check")) {
    const current = existsSync(outPath) ? readFileSync(outPath, "utf8") : "";
    if (current !== json) {
      console.error("knowledge.generated.json is stale. Run: node project-guide/scripts/build-index.ts");
      process.exit(1);
    }
    console.log(`index is current: ${kb.chunks.length} chunks (${kb.generatedFrom})`);
  } else {
    writeFileSync(outPath, json);
    const byProject: Record<string, number> = {};
    for (const c of kb.chunks) byProject[c.project] = (byProject[c.project] || 0) + 1;
    console.log(`wrote ${kb.chunks.length} chunks, ${(json.length / 1024).toFixed(0)} KiB ->`, outPath);
    console.log(byProject);
  }
}
