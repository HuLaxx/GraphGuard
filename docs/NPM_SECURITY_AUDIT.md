# GraphGuard P0 — npm advisory triage (17 November 2026)

**Source:** [GitHub Actions 44146418606](https://github.com/HuLaxx/GraphGuard/actions/runs/44146418606) on commit `8ed01eefd91066c48103f49bf2a866161431ac45`. The job ran `npm --prefix frontend audit --json` and `npm --prefix frontend audit --omit=dev --json` against the locked frontend dependency tree. It uploaded machine-readable JSON and printed exact direct/transitive paths and fix suggestions. These are vulnerability **package counts**, not independent confirmed exploits.

## Measured baseline (before remediation)

| Scope | Critical | High | Moderate | Low | Total |
|---|---:|---:|---:|---:|---:|
| Full dependency tree, including developer/test tooling | 2 | 13 | 14 | 0 | 29 |
| Production-only (`--omit=dev`) | 0 | 1 | 0 | 0 | 1 |

**Production finding:** direct `zod` **3.25.76**, `GHSA-mrhx-c7xc-m3w5` (large/invalid constrained collection memory exhaustion). npm's automated fix requires a major v4 upgrade; simply running `npm audit fix --force` would make uncontrolled changes. The root application did not have a verified Zod consumption path at audit time.

**Critical development findings:** `vitest` **2.1.9** and its transitive worker pool `tinypool`, including prototype-pollution/remote-code and mock-redirect advisories. `vitest 5.1.0` and compatible `@vitest/coverage-v8 5.1.0` are being evaluated in a **noncommitting** CI trial, and require **Node.js 22.12+**, not the existing Node 20 workflow baseline. No migration result should be claimed before tests.

**Additional full-tree high findings** in `@next/eslint-plugin-next`/`eslint-config-next` through `fast-glob`/`micromatch`/`picomatch`, plus `brace-expansion`, `browserslist`, `flatted`, `js-yaml`, `minimatch`, `rollup`, `vite` and `zod`. Several require an upgraded transitive package or a controlled major version change; the npm suggestion to downgrade `eslint-config-next` to Next 14.x should **not** be accepted blindly against the Next 16 app.

## Changes on draft PR #11

1. `scripts/print-npm-audit.mjs` and `npm-audit-inventory` in `.github/workflows/ci.yml` print reproducible advisory details for both full and production scopes and retain the JSON reports as short-lived workflow artifacts.
2. Removed the **direct app/runtime Zod v3 dependency** from `frontend/package.json` and its lockfile root. Kept Zod v3 in the lockfile **marked dev-only** because `eslint-plugin-react-hooks` still depends on it in the development tooling tree. This is a narrowly scoped first fix, not a claim that all Zod copies or full-tree advisories are eliminated.
3. Added a strict `npm audit --omit=dev --audit-level=high` CI step to **block any high/critical production dependency advisories**. Its success against the changed lockfile is **pending** at this documentation checkpoint.
4. `scripts/prepare-npm-security-candidate.mjs` scans branch source files for explicit Zod imports and stages a Vitest + coverage major upgrade only in a temporary Actions checkout; `scripts/print-npm-security-patch.mjs` exports an inspectable changed-lockfile proposal for review. Trial CI has `contents:read`, never pushes or commits, and uses Node 22. No `npm audit fix --force`.

## Acceptance checklist

- [x] Full and production advisory inventory performed and artifacts uploaded on [CI 44146418606](https://github.com/HuLaxx/GraphGuard/actions/runs/44146418606).
- [x] Narrow source/lock direct Zod removal implemented on the **draft security branch**, preserving the remaining dev dependency.
- [x] Blocking production audit gate added to the workflow, but **not yet verified green on that change**.
- [ ] Run candidate dependency changes under supported Node 22 and inspect the exact modified transitive tree. If candidate fails, do not commit its patch.
- [ ] Apply only passing, reviewed package/lock changes and rerun `npm ci`, lint, TypeScript, Vitest coverage, Next production build, real Kafka/Neo4j tests and local Next+FastAPI HTTP smoke.
- [ ] Verify **zero production high/critical**, separately report all full-tree high/critical counts, and resolve or transparently risk-assess any remaining development advisories.
- [ ] Review SBOM/Trivy results and other Python, Docker and secrets exposures; no full dependency/security clearance is asserted.

## Reproduce

```bash
npm --prefix frontend ci
npm --prefix frontend audit --json
npm --prefix frontend audit --omit=dev --json
npm --prefix frontend audit --omit=dev --audit-level=high
npm --prefix frontend run lint
npm --prefix frontend run type-check
npm --prefix frontend run test
npm --prefix frontend run build
```

**Limitations:** npm audit metadata changes as advisories are added/updated and does not establish exploitability by itself; `--omit=dev` is **not** an excuse to ignore security of build/test tools that execute on trusted CI. A separate Trivy high/critical scan previously passed but does **not** eliminate these npm findings. This PR is a draft stacked on #10, with no merge, public deployment or AWS usage.
