/**
 * Copies the documents listed in project-guide/sources.json from local clones of
 * FleetFlow, GraphGuard and Sentinance into project-guide/corpus, and writes
 * project-guide/corpus/manifest.json.
 *
 *   node project-guide/scripts/sync-corpus.ts --root ../..        # folder holding the three clones
 *   node project-guide/scripts/sync-corpus.ts --root ~/code --only fleetflow
 *
 * Then rebuild the index: node project-guide/scripts/build-index.ts
 */
import { execFileSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

interface SourceProject {
  repo: string;
  branch: string;
  files: string[];
}

interface ManifestEntry {
  file: string;
  project: string;
  source: string;
  url: string;
}

interface Manifest {
  commits: Record<string, string>;
  entries: ManifestEntry[];
}

const here = dirname(fileURLToPath(import.meta.url));
const assistantDir = resolve(here, "..");
const corpusDir = join(assistantDir, "corpus");

function arg(name: string): string | undefined {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : undefined;
}

const root = resolve(arg("--root") || join(assistantDir, "..", "..", ".."));
const only = arg("--only");

const sources = JSON.parse(readFileSync(join(assistantDir, "sources.json"), "utf8")) as {
  projects: Record<string, SourceProject>;
};

const manifestPath = join(corpusDir, "manifest.json");
const previous: Manifest = existsSync(manifestPath)
  ? (JSON.parse(readFileSync(manifestPath, "utf8")) as Manifest)
  : { commits: {}, entries: [] };

// Hand-written documents kept in the corpus itself (not copied from a repo).
const entries: ManifestEntry[] = [
  { file: "profile/rahul-khanke.md", project: "profile", source: "curated", url: "https://portfolio.hulax.uk" },
  ...(["fleetflow", "graphguard", "sentinance"] as const).map((p) => ({
    file: `curated/${p}-at-a-glance.md`,
    project: p,
    source: "curated",
    url: `https://github.com/${sources.projects[p].repo}`,
  })),
];
const commits: Record<string, string> = { ...previous.commits };
let copied = 0;
let missing = 0;

for (const [project, spec] of Object.entries(sources.projects)) {
  const repoName = spec.repo.split("/")[1];
  const repoDir = join(root, repoName);
  if (only && only !== project) {
    entries.push(...previous.entries.filter((e) => e.project === project));
    continue;
  }
  if (!existsSync(repoDir)) {
    console.warn(`! ${project}: clone not found at ${repoDir}; keeping previous corpus files`);
    entries.push(...previous.entries.filter((e) => e.project === project));
    continue;
  }
  try {
    commits[project] = execFileSync("git", ["-C", repoDir, "rev-parse", "--short=12", "HEAD"], { encoding: "utf8" }).trim();
  } catch {
    commits[project] = "unknown";
  }
  for (const file of spec.files) {
    const from = join(repoDir, file);
    if (!existsSync(from)) {
      console.warn(`! ${project}: missing ${file}`);
      missing++;
      continue;
    }
    const target = `${project}/${file.replace(/\//g, "__")}`;
    mkdirSync(dirname(join(corpusDir, target)), { recursive: true });
    copyFileSync(from, join(corpusDir, target));
    entries.push({
      file: target,
      project,
      source: `${spec.repo}:${file}`,
      url: `https://github.com/${spec.repo}/blob/${spec.branch}/${file}`,
    });
    copied++;
  }
}

entries.sort((a, b) => a.file.localeCompare(b.file));
writeFileSync(manifestPath, JSON.stringify({ commits, entries }, null, 2) + "\n");
console.log(`synced ${copied} documents (${missing} missing) into ${corpusDir}`);
console.log("source commits:", commits);
