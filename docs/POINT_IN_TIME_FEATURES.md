# GraphGuard P1 — Point-in-time graph-context features

**Scope:** local/synthetic events accepted by the real Kafka → Avro → SQLite
ledger → Neo4j path. This milestone produces **feature snapshots**, not a
trained fraud score, an analyst judgment, or a production feature store.

## Why the source ledger, not the current Neo4j graph?

A live graph reflects transactions received **after** a past decision. A
historical query against that graph can accidentally disclose future edges.
`data-eng/consumers/point_in_time_features.py` therefore reconstructs
user/device/merchant relationship counts from the first accepted normalized
source records. These edges match the graph's source identities; the feature
calculator does not pretend it executes GDS or a live Neo4j query.

The accepted local ledger stores receipt order (SQLite `rowid`), UTC receipt
time, immutable transaction identity, event timestamp and normalized entities.

For a target transaction `t`, a historical record `h` is eligible only if:

```text
h.ledger_rowid < t.first_ledger_rowid
h.received_at_utc <= t.first_received_at_utc
t.event_time_ms - window_ms <= h.event_time_ms < t.event_time_ms
```

The first two clauses prevent **knowledge-time leakage** (a late arrival or
backfill cannot change a decision already made). The last clause prevents
**event-time leakage** (a future event ingested early, or a simultaneous
event, cannot become history). Time windows have an inclusive lower bound
and exclusive upper bound. Neither fraud labels nor subsequent human review
decisions are used.

## Feature contract: `pit-v1`

- User transaction count in the previous 24 hours.
- Same-currency user transaction count, amount sum and amount mean over 24h
  (no FX mixing, no made-up exchange rates).
- Merchant transaction count over 24h.
- Device transaction count, unique linked users and *other* linked users over
  7 days.
- Merchant distinct users over 7 days.
- User→merchant transactions and user distinct devices over 30 days.

Zero-history results are explicit zero-valued features, not missing values
filled by future knowledge.

The immutable table `transaction_feature_snapshots` contains a
`(transaction_id, feature_version)` primary key, source payload SHA-256,
event/receipt cutoffs, a canonical feature JSON and SHA-256, and computation
time. It is written **after** graph projection and **before** Kafka offset
acknowledgment. Restart/replay returns the first persisted snapshot; it
does not silently recompute it after a late backfill. Failed snapshot
materialization retains the Kafka offset for retry.

## Reproduce

Focused synthetic SQLite leakage tests:

```bash
python -m pip install -r requirements-ci.txt
pytest tests/unit/test_point_in_time_features.py tests/unit/test_graph_builder_delivery.py -v
```

Full Docker-backed source → features test:

```bash
python -m pip install -r requirements-ci.txt -r requirements-ingestion-ci.txt
docker compose -f docker-compose.ingestion.yml up -d --wait
GRAPHGUARD_INGESTION_INTEGRATION=1 pytest \
  tests/integration/test_avro_registry.py -v
docker compose -f docker-compose.ingestion.yml down --remove-orphans
```

One added Avro test ingests a historical transaction, an event whose
event-time is **in the future**, and a target transaction; it checks the
persisted target features. It then publishes an older-event-time transaction
**after** the target decision and confirms that the snapshot hash stays
unchanged. Existing real Kafka/Schema Registry/Neo4j integration tests also
continue to run in CI.

## Limitations and following work

- This implementation scans synthetic records in a local SQLite DB. It is
  deliberately not a scalable distributed batch/stream feature platform,
  not Feast online materialization and not a performance claim.
- First-seen knowledge comes from **this one ledger**. Reconstructing
  historical production knowledge requires authoritative ingestion logs,
  versioned entity resolution, a governed online/offline feature store and
  consistent retention policies.
- Retrospective offline training on late-arriving data needs an **explicit**
  correction policy; it must not be confused with what the system knew
  at original decision time. Existing snapshots remain immutable.
- The ledger contains synthetic IDs. No actual customer, IP or payment-card
  details should be inserted into this unauthenticated local fixture DB.
- Currency comparison uses the same three-letter code only; exchange
  conversions, chargebacks, feature freshness SLAs and missing-data signals
  are not yet modeled.
- Race/failure testing under concurrent multi-process consumers, Kafka
  rebalances, DB compaction and legacy migrations remains necessary.
- Features **are not used by a verified trained scoring model yet**.
  Next gate: chronological, entity-leakage-free logistic-regression/XGBoost
  baselines with dataset provenance and a versioned scoring artifact;
  afterwards evidence-linked SHAP and persistent human-review decisions.
