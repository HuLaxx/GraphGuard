# P0 dependency candidate promotion — 19 November 2026

The production audit on the existing lockfile was clean, but the full tree was not. The first isolated Vitest 5 trial failed because Vite was not present. The fixed trial, [GitHub Actions 44608220292](https://github.com/HuLaxx/GraphGuard/actions/runs/44608220292/job/135857507696), explicitly pins Vite 7.3.8 alongside Vitest and coverage 5.1.0 under Node 22. The candidate passed ESLint, TypeScript, 9 frontend cases in 4 test files and the Next production build. Both full-tree and production npm audit reported zero findings in the candidate at the time of that scan.

This commit promotes the runner-generated manifest and reconstructs the lock from the emitted 172 JSON patch records (17 additions, 58 removals; 772 -> 731 package records), checking baseline and target counts, unchanged direct production dependencies/scripts and matching root dev dependencies. CI now uses Node 22, replaces the temporary trial with a blocking full-tree high/critical audit, and preserves reports on failure. Fresh exact-head npm ci, service tests, security checks and audit must pass before release. npm advisory databases change, and a zero scan is not a guarantee against future vulnerability. No main merge, live deployment, cloud charges or production auth claim.

Local frontend prerequisite: Node.js 22.12+ (Vitest 5 engine requirement).
