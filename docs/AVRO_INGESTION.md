# GraphGuard P1 — Real Avro and Schema Registry acceptance

**Scope:** synthetic test events → real Avro serializer → local Schema Registry
→ Kafka → GraphBuilder Avro decoder → SQLite source ledger → Neo4j graph.
Not ML scoring, a live bank connection, or a deployed service.

## Local run

The disposable test environment uses localhost port 9092 for Kafka, 7687 for
Neo4j, and **8082** for Schema Registry (the registry's container port is 8081).

\`\`\`bash
python -m pip install -r requirements-ci.txt -r requirements-ingestion-ci.txt
docker compose -f docker-compose.ingestion.yml up -d --wait
GRAPHGUARD_INGESTION_INTEGRATION=1 pytest \
    tests/integration/test_ingest_kafka_neo4j.py \
    tests/integration/test_avro_registry.py -v
docker compose -f docker-compose.ingestion.yml down --remove-orphans
\`\`\`

CI executes the same commands using temporary services; it must pass against
the **current commit** before this milestone is accepted.

## Verified only if tests pass

1. The actual TransactionProducer serializes synthetic Pydantic events with
   the version-one Avro schema and obtains schema IDs from the live registry.
2. The registered subject is \`transactions.avro.acceptance-value\`. The
   produced record has Confluent's Avro magic byte and a non-zero schema ID,
   not a JSON fixture.
3. GraphBuilder resolves the schema ID through its real deserializer with
   JSON fallback disabled; writes a normalized source record first; then
   atomically applies its hash-checked graph projection.
4. A retry with the same transaction ID and normalized content does not add
   a duplicate transaction; different content under the same ID is quarantined
   through the existing acknowledged DLQ.
5. Replaying the same wire records with another consumer group leaves the
   first accepted source record and graph transaction unchanged.
6. A consumer configured with an **unreachable** registry URL refuses to
   advance the offset on an Avro decode fault. Reconnecting the **same**
   group to the correct URL enables it to replay and persist the event.
7. Naive datetime and nonfinite amounts are rejected by the producer model.
   The local ledger excludes source IP address and card fragments.

**Failure-mode boundary:** an unreachable URL simulates Schema Registry
unavailability with real Avro/Kafka/Neo4j clients, but is not a chaos drill
that stops the registry container. Version compatibility across evolving
schemas and broker rebalance under concurrent partitions remain untested.

## Contract boundaries

- The Avro schema defines \`schema_version=1\`. A new producer version needs
  compatibility testing and a documented migration.
- Confluent wire-framed messages are never interpreted as JSON on failure.
  An unavailable registry or unreadable schema ID fails closed with the
  original Kafka offset available for replay; operators must investigate
  permanent poison Avro records to prevent a stuck consumer.
- JSON is allowed only with \`GRAPHGUARD_JSON_FIXTURE_MODE=true\` for
  explicitly synthetic tests, not as a silent provider fallback.
- The ledger is local SQLite/WAL for a reproducible demo. It is not a
  horizontally scalable, access-controlled system of record. Kafka commits
  occur after ledger and graph writes; a crash can replay a valid record.
  Do **not** advertise exactly-once processing.
- No AWS account, paid service, cloud database or production data is used.

## Next gate

Add deliberate schema evolution compatibility and malformed schema-ID tests,
and then finish the true graph feature → trained model → explanation →
persisted analyst decision workflow. Only update the portfolio after its
evidence is reproducible.
