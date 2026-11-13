"""Offset/DLQ recovery regression tests against the real GraphBuilder methods.

External clients are stubbed at import time; no Kafka, Neo4j or network services
are required. These are *failure-policy* tests, not broker-backed integration.
"""

import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def graph_builder_class(monkeypatch):
    kafka = types.ModuleType("confluent_kafka")
    kafka.Consumer = MagicMock()
    kafka.Producer = MagicMock()
    kafka.KafkaError = MagicMock()
    registry = types.ModuleType("confluent_kafka.schema_registry")
    registry.SchemaRegistryClient = MagicMock()
    avro = types.ModuleType("confluent_kafka.schema_registry.avro")
    avro.AvroDeserializer = MagicMock()
    serialization = types.ModuleType("confluent_kafka.serialization")
    serialization.SerializationContext = MagicMock()
    serialization.MessageField = types.SimpleNamespace(VALUE="value")
    neo4j = types.ModuleType("neo4j")
    neo4j.GraphDatabase = MagicMock()
    structlog = types.ModuleType("structlog")
    structlog.get_logger = MagicMock()

    for name, stub in (
        ("confluent_kafka", kafka),
        ("confluent_kafka.schema_registry", registry),
        ("confluent_kafka.schema_registry.avro", avro),
        ("confluent_kafka.serialization", serialization),
        ("neo4j", neo4j),
        ("structlog", structlog),
    ):
        monkeypatch.setitem(sys.modules, name, stub)

    source = Path(__file__).resolve().parents[2] / "data-eng/consumers/graph_builder.py"
    spec = importlib.util.spec_from_file_location("graphguard_delivery_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.GraphBuilder


def new_builder(cls):
    builder = cls.__new__(cls)
    builder.consumer = MagicMock()
    builder.dlq_producer = MagicMock()
    builder.avro_deserializer = None
    builder._create_transaction_edges_batch = MagicMock()
    builder.buffer = []
    builder.pending_messages = []
    return builder


def transaction():
    return {
        "transaction_id": "txn-synthetic-1",
        "user_id": "synthetic-user",
        "merchant_id": "synthetic-merchant",
        "device_id": "synthetic-device",
        "amount": 17.25,
        "currency": "GBP",
        "timestamp": 1790000000000,
        "idempotency_key": "a" * 64,
    }


def kafka_message(payload):
    msg = MagicMock()
    msg.value.return_value = json.dumps(payload).encode("utf-8")
    return msg


def test_neo4j_failure_does_not_commit_or_dlq_valid_transactions(graph_builder_class):
    builder = new_builder(graph_builder_class)
    builder.BATCH_SIZE = 1
    builder._create_transaction_edges_batch.side_effect = RuntimeError("Neo4j offline")
    builder._send_to_dlq = MagicMock()
    msg = kafka_message(transaction())

    with pytest.raises(RuntimeError, match="Neo4j offline"):
        builder.process_message(msg)

    builder.consumer.commit.assert_not_called()
    builder._send_to_dlq.assert_not_called()
    assert builder.pending_messages == [msg]
    assert builder.buffer[0]["transaction_id"] == "txn-synthetic-1"


def test_successful_graph_batch_commits_offsets_synchronously(graph_builder_class):
    builder = new_builder(graph_builder_class)
    msg = kafka_message(transaction())
    builder.buffer = [transaction()]
    builder.pending_messages = [msg]

    builder._flush_buffer()

    builder._create_transaction_edges_batch.assert_called_once()
    builder.consumer.commit.assert_called_once_with(message=msg, asynchronous=False)
    assert builder.buffer == []
    assert builder.pending_messages == []


def test_offset_commit_failure_preserves_batch_for_replay(graph_builder_class):
    builder = new_builder(graph_builder_class)
    msg = kafka_message(transaction())
    builder.buffer = [transaction()]
    builder.pending_messages = [msg]
    builder.consumer.commit.side_effect = RuntimeError("Kafka not available")

    with pytest.raises(RuntimeError, match="Kafka not available"):
        builder._flush_buffer()

    assert builder.buffer and builder.pending_messages == [msg]


def test_invalid_event_dlq_is_acknowledged_before_offset_commit(graph_builder_class):
    builder = new_builder(graph_builder_class)
    msg = kafka_message({"transaction_id": "missing-required-fields"})
    events = []

    def produce(**kwargs):
        events.append("dlq")
        kwargs["on_delivery"](None, MagicMock())

    def commit(**kwargs):
        events.append("commit")

    builder.dlq_producer.produce.side_effect = produce
    builder.dlq_producer.flush.return_value = 0
    builder.consumer.commit.side_effect = commit

    builder.process_message(msg)

    assert events == ["dlq", "commit"]
    builder.consumer.commit.assert_called_once_with(message=msg, asynchronous=False)
    assert builder.buffer == []


def test_dlq_outage_does_not_acknowledge_invalid_source_event(graph_builder_class):
    builder = new_builder(graph_builder_class)
    msg = kafka_message({"transaction_id": "missing-required-fields"})
    builder.dlq_producer.flush.return_value = 1

    with pytest.raises(RuntimeError, match="DLQ delivery not acknowledged"):
        builder.process_message(msg)

    builder.consumer.commit.assert_not_called()


@pytest.mark.parametrize("invalid_amount", [-1.0, float("nan"), float("inf"), 0])
def test_malformed_amount_never_reaches_graph(graph_builder_class, invalid_amount):
    builder = new_builder(graph_builder_class)
    payload = transaction()
    payload["amount"] = invalid_amount
    msg = kafka_message(payload)
    builder._send_to_dlq = MagicMock()

    builder.process_message(msg)

    builder._send_to_dlq.assert_called_once()
    builder.consumer.commit.assert_called_once()
    builder._create_transaction_edges_batch.assert_not_called()


def test_neo4j_result_consumed_before_batch_is_acknowledged(graph_builder_class):
    builder = new_builder(graph_builder_class)
    builder.neo4j_driver = MagicMock()
    transaction_batch = [transaction()]

    # Call the actual database method (rather than its standard test stub).
    graph_builder_class._create_transaction_edges_batch(builder, transaction_batch)

    session = builder.neo4j_driver.session.return_value.__enter__.return_value
    session.run.assert_called_once()
    session.run.return_value.consume.assert_called_once()
