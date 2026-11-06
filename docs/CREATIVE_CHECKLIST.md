# GraphGuard / Evidence Graph — Creative Casefile Checklist

**Design identity:** a forensic investigation file, **not** a cyberpunk trading dashboard or a copy of the Sentinance README.

**Editorial premise:** one transaction is an observation; connected entities are context; a model score is an estimate; the reviewer needs evidence, not just an alert.

This checklist distinguishes **published repo edits** from independent operational validation.

## Casefile design

- [x] Inspect actual GraphGuard repo tree, README, frontend, model serving, GraphQL and the historical audit.
- [x] Confirm the investigation desk contains **mock case/graph fixtures** and document that clearly.
- [x] Establish a unique **dark forensic casefile + warm paper exhibit** visual language.
- [x] Publish a bespoke **animated network casefile hero** at [evidence-graph-hero.svg](assets/evidence-graph-hero.svg), labeling it illustrative rather than real.
- [x] Publish a contrasting **five-stage evidence-trail diagram** at [investigation-trail.svg](assets/investigation-trail.svg).
- [x] Preserve the pre-existing [demo capture](assets/graphguard-demo.gif) and explain its demo limitations.
- [x] Rewrite README as a case investigation: opening → relationships → investigation desk → evidence register → local setup → unresolved questions.
- [x] Replace generic decorative badges with proof, repository links and dated testing evidence.
- [x] Document the difference between production plans, local backing services and hosted fallback/demo mode.

## Evidence quality

- [x] Connect specific statements to Kafka, Neo4j, XGBoost, SHAP, GraphQL and RAG modules.
- [x] Link historical [32-pass Python test record (24 Jan 2026)](../evidence/python-tests-20260124-210720.txt) and [API score sample](../evidence/api-score-20260124-214043.txt) without presenting them as live CI.
- [x] Disclose the documented GAT scoring stub and un-applied Terraform.
- [ ] Run current Python and frontend tests with recorded output; existing logs are historical.
- [ ] Verify current CI workflows pass (including install/build jobs).
- [ ] Verify local Docker Compose boot, graph ingestion, model score, explanation and case review end-to-end.
- [ ] Confirm public hosted demo status, screenshot accuracy and where fallback data is used.
- [ ] Reproduce evaluation metrics and false-positive/false-negative trade-offs on labeled data before publishing measured claims.
- [ ] Validate both SVGs in desktop/mobile GitHub rendering and reduced-motion contexts.
- [ ] Review old development credentials and security remediation tasks before any deployment.

## Release checks

- [x] Publish updated README and both custom SVG illustrations.
- [x] Confirm the new artifacts exist on the default branch.
- [ ] Recheck all README local links after this checklist file is added.
- [ ] Retest commands, live environment and production claims separately.

**Status:** Visual/editorial pass complete. Test/build/deployment verification is **not** complete.

**Return to the [master makeover tracker](https://github.com/HuLaxx/HuLaxx/blob/main/REPO_MAKEOVER_TRACKER.md).**
