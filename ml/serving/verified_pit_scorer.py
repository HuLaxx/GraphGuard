"""Fail-closed, hash-pinned OFFLINE inference for synthetic GraphGuard events.

This module scores accepted `pit-v1` ledger snapshots without importing the
existing API's heuristic explanations or issuing automated accusations.
The manifest SHA must be pinned out-of-band (e.g. the trusted CI artifact).
"""
from datetime import datetime, timezone
import hashlib
import hmac
import json
import math
from pathlib import Path
import sqlite3

import numpy as np
from xgboost import XGBClassifier

from ml.training.pit_baselines import (
    FEATURE_COLUMNS, FEATURE_VERSION, MODEL_INPUT_VERSION,
)

SYNTHETIC_SCOPE = "SYNTHETIC ONLY - not real bank fraud detection"
MODEL_FILES = {
    "logistic_regression": "logistic_baseline.json",
    "xgboost": "xgboost_baseline.json",
}
RESEARCH_STATUS = "RESEARCH_SCORE_ONLY_NO_AUTOMATED_DECISION"


class ScoringContractError(ValueError):
    """Untrusted or mismatched source, model, snapshot or feature metadata."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _equals(left: str, right: str) -> bool:
    return (
        isinstance(left, str) and isinstance(right, str)
        and len(left) == 64 and len(right) == 64
        and hmac.compare_digest(left, right)
    )


def _ensure_hex(pin: str):
    if not isinstance(pin, str) or len(pin) != 64 or any(c not in "0123456789abcdef" for c in pin):
        raise ScoringContractError("Expected an explicit lower-case SHA-256 pin")


class VerifiedSyntheticScorer:
    """Read-only ledger scorer with deterministic hash-pinned model loading.

    The library doesn't mutate accepted transactions or feature snapshots.
    A saved score is for research/investigator evaluation ONLY, not a
    policy decision, and never a claim of actual fraud.
    """

    def __init__(self, artifact_dir: Path, *, expected_manifest_sha256: str):
        _ensure_hex(expected_manifest_sha256)
        root = Path(artifact_dir)
        manifest_path = root / "manifest.json"
        manifest_raw = manifest_path.read_bytes()
        if not _equals(_sha(manifest_raw), expected_manifest_sha256):
            raise ScoringContractError("Untrusted manifest SHA-256; refusing inference")
        manifest = json.loads(manifest_raw)
        if manifest.get("scope") != SYNTHETIC_SCOPE:
            raise ScoringContractError("Cannot use an unapproved/real-data model")
        if (
            manifest.get("feature_version") != FEATURE_VERSION
            or manifest.get("model_input_version") != MODEL_INPUT_VERSION
            or manifest.get("feature_columns") != list(FEATURE_COLUMNS)
        ):
            raise ScoringContractError("Manifest feature/version contract mismatch")
        selected = manifest.get("selected_by_validation_pr_auc")
        if selected not in MODEL_FILES:
            raise ScoringContractError("Unknown or unapproved model selection")
        filename = MODEL_FILES[selected]
        allowed_hashes = manifest.get("artifacts_sha256")
        if not isinstance(allowed_hashes, dict) or filename not in allowed_hashes:
            raise ScoringContractError("Missing trained model hash")
        model_path = root / filename
        if not _equals(_sha(model_path.read_bytes()), allowed_hashes[filename]):
            raise ScoringContractError("Model artifact SHA-256 does not match manifest")

        self.manifest_sha256 = expected_manifest_sha256
        self.model_sha256 = allowed_hashes[filename]
        self.model_name = selected
        self.input_version = MODEL_INPUT_VERSION
        self.feature_version = FEATURE_VERSION
        if selected == "xgboost":
            self.model = XGBClassifier()
            self.model.load_model(model_path)
            if self.model.n_features_in_ != len(FEATURE_COLUMNS):
                raise ScoringContractError("Native model feature dimensions mismatch")
        else:
            self.model = None
            params = json.loads(model_path.read_text())
            if (
                params.get("model_type") != "standard_scaler_plus_logistic"
                or params.get("input_version") != MODEL_INPUT_VERSION
                or params.get("feature_columns") != list(FEATURE_COLUMNS)
            ):
                raise ScoringContractError("Logistic model feature contract mismatch")
            self.logistic = params
            for item in ("scaler_mean", "scaler_scale", "coefficients"):
                values = params.get(item)
                if not isinstance(values, list) or len(values) != len(FEATURE_COLUMNS):
                    raise ScoringContractError(f"Invalid logistic parameters: {item}")
                if not all(type(v) in (float, int) and math.isfinite(v) for v in values):
                    raise ScoringContractError(f"Nonfinite logistic parameters: {item}")

    def _probability(self, values) -> float:
        vector = np.array([[values[name] for name in FEATURE_COLUMNS]], dtype=float)
        if self.model_name == "xgboost":
            probability = float(self.model.predict_proba(vector)[0, 1])
        else:
            p = self.logistic
            centered = (vector[0] - p["scaler_mean"]) / p["scaler_scale"]
            log_odds = float(np.dot(centered, p["coefficients"]) + p["intercept"][0])
            probability = 1.0 / (1.0 + math.exp(-log_odds)) if log_odds >= 0 else math.exp(log_odds) / (1.0 + math.exp(log_odds))
        if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
            raise ScoringContractError("Model returned invalid probability")
        return probability

    def score(self, connection: sqlite3.Connection, transaction_id: str) -> dict:
        if not isinstance(transaction_id, str) or not transaction_id.strip():
            raise ScoringContractError("Transaction ID required")
        row = connection.execute(
            """SELECT rowid, payload_json, payload_sha256, received_at_utc
               FROM transactions WHERE transaction_id=?""",
            (transaction_id,),
        ).fetchone()
        if row is None:
            raise ScoringContractError("Unaccepted transaction; no score allowed")
        seq, payload, payload_hash, arrived = row
        if not _equals(_sha(payload.encode("utf-8")), payload_hash):
            raise ScoringContractError("Source payload has been altered")
        event = json.loads(payload)
        if event.get("transaction_id") != transaction_id or event.get("schema_version") != 1:
            raise ScoringContractError("Source identity or Avro version mismatch")
        if event.get("currency") != "GBP":
            # The baseline generator used GBP only: no out-of-distribution
            # currency claims or unverified FX conversions allowed.
            raise ScoringContractError("Synthetic baseline supports GBP fixtures only")
        if type(event.get("amount")) not in (float, int) or not math.isfinite(event["amount"]) or event["amount"] <= 0:
            raise ScoringContractError("Invalid current amount")
        row = connection.execute(
            """SELECT feature_version, source_payload_sha256,
                      observation_cutoff_rowid, observation_cutoff_utc,
                      event_time_ms, features_json, features_sha256
               FROM transaction_feature_snapshots
               WHERE transaction_id=? AND feature_version=?""",
            (transaction_id, FEATURE_VERSION),
        ).fetchone()
        if row is None:
            raise ScoringContractError("Missing committed point-in-time feature snapshot")
        version, source_hash, cutoff_rowid, cutoff_utc, event_ms, snapshot_raw, snapshot_hash = row
        if not _equals(source_hash, payload_hash) or not _equals(_sha(snapshot_raw.encode("utf-8")), snapshot_hash):
            raise ScoringContractError("Source/snapshot SHA-256 mismatch")
        snapshot = json.loads(snapshot_raw)
        if (
            version != FEATURE_VERSION
            or event_ms != event.get("timestamp")
            or cutoff_rowid != seq or cutoff_utc != arrived
            or snapshot.get("feature_version") != FEATURE_VERSION
            or snapshot.get("event_time_ms") != event_ms
            or snapshot.get("as_of_ledger_rowid") != seq
            or snapshot.get("as_of_received_at_utc") != arrived
            or set(snapshot) != {"feature_version", "event_time_ms", "as_of_ledger_rowid", "as_of_received_at_utc", "features"}
        ):
            raise ScoringContractError("Feature point-in-time provenance mismatch")
        values = snapshot.get("features")
        if not isinstance(values, dict) or set(values) != set(FEATURE_COLUMNS) - {"current_amount"}:
            raise ScoringContractError("Feature allowlist/version does not match trained model")
        if not all(type(v) in (int, float) and math.isfinite(v) for v in values.values()):
            raise ScoringContractError("Nonfinite or nonnumeric feature")
        vector = {**values, "current_amount": event["amount"]}
        return {
            "transaction_id": transaction_id,
            "score": self._probability(vector),
            "score_type": "UNCALIBRATED_SYNTHETIC_MODEL_PROBABILITY",
            "status": RESEARCH_STATUS,
            "model_name": self.model_name,
            "model_input_version": self.input_version,
            "manifest_sha256": self.manifest_sha256,
            "model_sha256": self.model_sha256,
            "source_payload_sha256": payload_hash,
            "feature_snapshot_sha256": snapshot_hash,
            "feature_version": self.feature_version,
            "event_time_ms": event_ms,
        }


def save_research_score(connection: sqlite3.Connection, result: dict) -> dict:
    """Append a stable local research record; idempotent on exact rerun.

    Never updates source transactions, prior snapshots or human decisions.
    The saved row contains no IP, card fragment, customer text or fraud label.
    """
    if result.get("status") != RESEARCH_STATUS:
        raise ScoringContractError("Only non-decision research scores may be stored")
    connection.execute(
        """CREATE TABLE IF NOT EXISTS transaction_research_scores (
             transaction_id TEXT NOT NULL,
             manifest_sha256 TEXT NOT NULL,
             model_sha256 TEXT NOT NULL,
             feature_snapshot_sha256 TEXT NOT NULL,
             source_payload_sha256 TEXT NOT NULL,
             score REAL NOT NULL,
             saved_at_utc TEXT NOT NULL,
             PRIMARY KEY(transaction_id, manifest_sha256)
           )"""
    )
    identity = (result["transaction_id"], result["manifest_sha256"])
    prior = connection.execute(
        """SELECT model_sha256, feature_snapshot_sha256, source_payload_sha256, score
           FROM transaction_research_scores WHERE transaction_id=? AND manifest_sha256=?""",
        identity,
    ).fetchone()
    expected = (
        result["model_sha256"], result["feature_snapshot_sha256"],
        result["source_payload_sha256"], result["score"],
    )
    if prior is not None:
        if prior != expected:
            raise ScoringContractError("Refusing to overwrite prior research score")
        return result
    try:
        connection.execute(
            """INSERT INTO transaction_research_scores
               (transaction_id, manifest_sha256, model_sha256,
                feature_snapshot_sha256, source_payload_sha256, score, saved_at_utc)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (*identity, *expected, datetime.now(timezone.utc).isoformat()),
        )
        connection.commit()
    except sqlite3.IntegrityError as error:
        connection.rollback()
        raise ScoringContractError("Concurrent score conflict; retry read") from error
    return result
