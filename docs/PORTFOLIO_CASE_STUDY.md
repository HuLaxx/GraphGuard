# GraphGuard — Evidence-led portfolio copy (draft, not yet published)

## Recruiter tagline

Built a reproducible synthetic fraud-investigation pipeline connecting registered Kafka events, Neo4j relationships, time-correct graph features, XGBoost scoring, native SHAP attribution and signed human review.

## LinkedIn Featured description

GraphGuard is my applied ML and graph-data engineering portfolio project. I wanted to show how a suspicious transaction should become a **reviewable investigation**, rather than automatically being called fraud. The local test path ingests real Avro records through Kafka and Schema Registry, projects connections into Neo4j, and computes immutable graph features using only information known when a transaction arrived. I compared logistic regression and XGBoost on a deterministic synthetic chronological holdout, then built hash-verified scoring, native TreeSHAP explanations and signed analyst/admin case actions with a traceable local audit trail. A connected Next.js case desk exposes the model evidence and human review history without fake fallback scores. The results are synthetic research evidence, not real banking accuracy or a production deployment.

## Case study (engineering narrative)

**Problem.** A model can rank a transaction as unusual while hiding the data lineage, time leakage and review steps behind that score. I designed GraphGuard around an investigator's question: what was known, which relationships contributed to the model output, and who reviewed it?

**Approach.** The reproducible synthetic source uses a registered Avro transaction event, Kafka and Schema Registry, a durable first-observed SQLite ledger, and Neo4j user, device and merchant relationships. Point-in-time feature snapshots exclude information received after the scored event. Models are trained on chronological splits with an explicit feature allowlist and SHA-256 provenance; a model/feature mismatch fails closed.

**Evaluation.** I compared a standardized logistic regression baseline with XGBoost on simulated labels, recording PR-AUC, ROC-AUC, precision@K, calibration diagnostics and realized false-positive rates. XGBoost achieved a synthetic held-out PR-AUC of **0.7650**, but its **9.375%** held-out FPR exceeded the validation-selected 5% budget. That limitation matters more than presenting a flattering single score.

**Investigation.** Native TreeSHAP contributions reconstruct the actual model output in log odds. A signed local reviewer opens and escalates cases, while an admin can close them. Each review event is linked to immutable model/source/feature hashes and a local keyed audit chain. The Next.js case desk retrieves actual signed API data and makes clear what is synthetic.

**Trade-offs.** The quick-start seeds SQLite directly for accessibility; a separate Docker-backed integration test verifies Kafka through signed review. SQLite, demo tokens, an uncalibrated synthetic model and an unpublished cloud architecture are deliberately **not** described as production banking infrastructure.

## Evidence links

- [GraphGuard source and architecture](https://github.com/HuLaxx/GraphGuard)
- [Signed investigation desk PR #10](https://github.com/HuLaxx/GraphGuard/pull/10)
- [Verified source-to-case PR #9](https://github.com/HuLaxx/GraphGuard/pull/9)
- [Real native SHAP PR #8](https://github.com/HuLaxx/GraphGuard/pull/8)
- [Synthetic training and metrics PR #6](https://github.com/HuLaxx/GraphGuard/pull/6)
- [Architecture and local setup](VERIFIED_ARCHITECTURE.md) · [Evidence register](EVIDENCE_REGISTER.md)

## A grounded technical interview story

**Question:** What did you do to prevent fraud-label and future-event leakage? **Answer:** I constrained model input to an explicit point-in-time feature contract, recorded first-known transaction payloads in an immutable ledger, and snapshotted graph context using both event-time and observation-time cutoffs. Tests insert late-arriving events and replay Kafka to verify old snapshots do not change. Labels exist in the synthetic training dataset, not ledger or source features. I compare chronological splits and disclose repeated entities across train/test as an unresolved cold-start limitation.

**Question:** How do you know the explanation is real? **Answer:** I call native XGBoost TreeSHAP on the same hash-pinned model and exact 12 input columns that produced the saved score. I test that baseline plus contributions reconstructs the raw model margin and final score. The signed case anchors the explanation's SHA-256. Model attribution does not establish causality or a person's wrongdoing.

**Question:** What would you do before production? **Answer:** Secure a licensed public/realistic dataset and human-labeled outcomes, evaluate cold-start and confidence intervals, calibrate and monitor false positives, add enterprise OIDC/MFA, external audit anchoring and retention, a browser-level e2e and load suite, and provision a measured least-privilege deployment only with approval.

**Publication restriction:** This is copy for a portfolio/LinkedIn update **after reviewing the final PR evidence**. Do not claim the draft code is merged, this system is a live deployed product, or the synthetic scores are real fraud performance.
